"""Automated per-video QA (spec section 12). Writes qa.json; a failed check blocks upload, there is no override."""
import argparse
import json
import re
import subprocess
import tempfile
from pathlib import Path

import chess
import imageio_ffmpeg

from .audio import measure
from .san_guard import unknown_moves
from .stages.emit import validate

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
EDGE_S = 0.2  # black frames inside the first/last 0.2 s are fade in/out, not defects


def _ffmpeg(*args: str) -> str:
    return subprocess.run([FFMPEG, "-hide_banner", "-nostats", *args], capture_output=True, text=True, check=False).stderr


def _spec(spec_dir: Path) -> dict:
    return json.loads((spec_dir / "video_spec.json").read_text(encoding="utf-8"))


def _subtract(interval: tuple[float, float], holes: list[tuple[float, float]]) -> list[tuple[float, float]]:
    pieces = [interval]
    for h0, h1 in holes:
        pieces = [p for a, b in pieces for p in ((a, min(b, h0)), (max(a, h1), b)) if p[1] > p[0]]
    return pieces


def _engine_sans(spec_dir: Path) -> set[str]:
    path = spec_dir / "classified.json"
    if not path.is_file(): return set()
    sans = set()
    for row in json.loads(path.read_text(encoding="utf-8")):
        for key, fen in (("before", "fen_before"), ("after", "fen_after")):
            board = chess.Board(row[fen])
            for line in row.get(key) or []:
                for uci in line.get("pv", []):
                    try:
                        move = chess.Move.from_uci(uci)
                        if move not in board.legal_moves: break
                        sans.add(board.san(move)); board.push(move)
                    except ValueError: break
    return sans


def check_spec_valid(spec_dir: Path, **_):
    validate(_spec(spec_dir))
    return "schema, pacing and calendar rules hold"


def check_moves_real(spec_dir: Path, **_):
    spec = _spec(spec_dir)
    game_sans = {p["san"] for p in spec["plies"]}; engine = _engine_sans(spec_dir)
    texts = [n["text"] for n in spec["narration"]] + [b["mascot"]["line"] for b in spec["beats"]]
    texts += [spec["youtube"]["title"], spec["thumbnail"]["text"], spec["cold_open"]["hook"]]
    bad = [m for t in texts for m in unknown_moves(t, game_sans, engine)]
    if bad: raise ValueError("moves not in the game or an engine line: " + ", ".join(dict.fromkeys(bad)))
    return f"{len(texts)} texts checked"


def check_mascot_lines(spec_dir: Path, **_):
    spec = _spec(spec_dir)
    cap = 10 if spec["language"] == "hi" else 8
    lines = [b["mascot"]["line"] for b in spec["beats"]]
    long_ = [l for l in lines if len(l.split()) > cap]
    dupes = sorted({l for l in lines if lines.count(l) > 1})
    if long_ or dupes: raise ValueError(f"over {cap} words: {long_}; repeated: {dupes}")
    return f"{len(lines)} lines"


def check_audio_levels(spec_dir: Path, **_):
    bad = []
    for seg in _spec(spec_dir)["narration"]:
        m = measure(spec_dir / seg["audio"])
        if abs(m["input_i"] + 14) > 1 or m["input_tp"] > -1: bad.append(f"{seg['segment_id']}: {m['input_i']:.1f} LUFS, {m['input_tp']:.1f} dBTP")
    if bad: raise ValueError("; ".join(bad))
    return "all segments -14 +-1 LUFS, TP <= -1 dBTP"


def check_final_mix(spec_dir: Path, mp4: Path, **_):
    """The rendered MP4's mixed audio, not the segment files: Remotion's stereo upmix and music change the level."""
    m = measure(mp4)
    if abs(m["input_i"] + 14) > 1 or m["input_tp"] > -1: raise ValueError(f"{m['input_i']:.1f} LUFS, {m['input_tp']:.1f} dBTP")
    return f"{m['input_i']:.1f} LUFS, {m['input_tp']:.1f} dBTP"


def planned_gaps(spec: dict) -> list[tuple[float, float]]:
    """Silence the timeline plans on purpose: before the first segment, between segments (incl. 900 ms reaction gaps), and the outro."""
    segs = sorted(spec["narration"], key=lambda s: s["start_ms"])
    edges = [0] + [x for s in segs for x in (s["start_ms"], s["start_ms"] + s["duration_ms"])] + [spec["duration_ms"]]
    return [(edges[i] / 1000, edges[i + 1] / 1000) for i in range(0, len(edges), 2)]


def check_dead_air(spec_dir: Path, mp4: Path, **_):
    spec = _spec(spec_dir)
    out = _ffmpeg("-i", str(mp4), "-af", "silencedetect=n=-45dB:d=2.5", "-f", "null", "-")
    starts = [float(x) for x in re.findall(r"silence_start: (-?[\d.]+)", out)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", out)]
    ends += [spec["duration_ms"] / 1000] * (len(starts) - len(ends))  # silence running to EOF has no end line
    gaps = planned_gaps(spec)
    bad = [p for s, e in zip(starts, ends) for p in _subtract((max(s, 0), e), gaps) if p[1] - p[0] > 2.5]
    if bad: raise ValueError("dead air at " + ", ".join(f"{a:.1f}-{b:.1f}s" for a, b in bad))
    return f"{len(starts)} silences, all planned"


def check_black_frames(spec_dir: Path, mp4: Path, **_):
    end = _spec(spec_dir)["duration_ms"] / 1000 - EDGE_S
    out = _ffmpeg("-i", str(mp4), "-vf", "blackdetect=d=0.1", "-an", "-f", "null", "-")
    spans = [(float(a), float(b)) for a, b in re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", out)]
    bad = [(max(a, EDGE_S), min(b, end)) for a, b in spans if min(b, end) - max(a, EDGE_S) >= 0.1]
    if bad: raise ValueError("black frames at " + ", ".join(f"{a:.1f}-{b:.1f}s" for a, b in bad))
    return "none"


def probe(mp4: Path) -> dict:
    """ffprobe is not bundled with imageio-ffmpeg, so read `ffmpeg -i` (CI has both and they agree)."""
    out = _ffmpeg("-i", str(mp4))
    v = re.search(r"Video: (\w+).*?, (\w+)[(,].*?, (\d+)x(\d+).*?, ([\d.]+) fps", out)
    d = re.search(r"Duration: (\d+):(\d+):([\d.]+)", out)
    a = re.search(r"Audio: (\w+)", out)
    if not (v and d and a): raise ValueError("cannot read video stream, audio stream and duration from the file")
    return {"vcodec": v[1], "pix_fmt": v[2], "width": int(v[3]), "height": int(v[4]), "fps": float(v[5]), "acodec": a[1],
            "duration_s": int(d[1]) * 3600 + int(d[2]) * 60 + float(d[3])}


def check_file_format(spec_dir: Path, mp4: Path, **_):
    spec = _spec(spec_dir); f = spec["format"]; p = probe(mp4)
    want = {"vcodec": "h264", "pix_fmt": "yuv420p", "acodec": "aac", "width": f["width"], "height": f["height"]}
    bad = [f"{k} {p[k]} != {v}" for k, v in want.items() if p[k] != v]
    if abs(p["fps"] - f["fps"]) > 0.01: bad.append(f"fps {p['fps']} != {f['fps']}")
    if abs(p["duration_s"] - spec["duration_ms"] / 1000) > 1 / f["fps"]: bad.append(f"duration {p['duration_s']:.2f}s != {spec['duration_ms'] / 1000:.2f}s")
    if bad: raise ValueError("; ".join(bad))
    return f"{f['width']}x{f['height']} {f['fps']} fps h264/yuv420p/aac"


CHECKS = [("spec_valid", check_spec_valid), ("moves_real", check_moves_real), ("mascot_lines", check_mascot_lines),
          ("audio_levels", check_audio_levels), ("final_mix", check_final_mix), ("dead_air", check_dead_air), ("black_frames", check_black_frames),
          ("file_format", check_file_format)]


def contact_sheet(spec: dict, mp4: Path, dest: Path) -> None:
    """Frames at every beat (+400 ms) and every 30 s, 4 columns of 480 px."""
    last = spec["duration_ms"] - 1
    times = sorted({min(b["at_ms"] + 400, last) for b in spec["beats"]} | set(range(0, last, 30000)))
    with tempfile.TemporaryDirectory() as tmp:
        for i, t in enumerate(times):
            _ffmpeg("-y", "-ss", f"{t / 1000:.3f}", "-i", str(mp4), "-frames:v", "1", "-vf", "scale=480:-2", f"{tmp}/f{i:03d}.png")
        rows = -(-len(times) // 4)
        _ffmpeg("-y", "-i", f"{tmp}/f%03d.png", "-vf", f"tile=4x{rows}", "-frames:v", "1", "-update", "1", str(dest))
    if not dest.is_file(): raise ValueError("contact sheet was not written")


def run_checks(spec_dir: Path, mp4: Path, thumb: Path) -> dict:
    spec_dir = Path(spec_dir); checks = []
    for name, fn in CHECKS:
        try: detail, passed = fn(spec_dir=spec_dir, mp4=Path(mp4)), True
        except Exception as exc: detail, passed = str(exc) or type(exc).__name__, False
        checks.append({"name": name, "passed": passed, "detail": detail})
    spec = _spec(spec_dir) if (spec_dir / "video_spec.json").is_file() else {}
    sheet, small = spec_dir / "contact.jpg", spec_dir / "thumb_320.png"
    try:
        contact_sheet(spec, Path(mp4), sheet)
        _ffmpeg("-y", "-i", str(thumb), "-vf", "scale=320:180", str(small))
        if not small.is_file(): raise ValueError("thumbnail was not written")
    except Exception as exc:
        checks.append({"name": "artifacts", "passed": False, "detail": str(exc)})
    result = {"video_id": spec.get("video_id", spec_dir.name), "passed": all(c["passed"] for c in checks), "checks": checks,
              "contact_sheet": str(sheet), "thumb_small": str(small)}
    (spec_dir / "qa.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def main(args: argparse.Namespace) -> int:
    from .context import REPO_ROOT
    result = run_checks(REPO_ROOT / "build" / "specs" / args.video, Path(args.mp4), Path(args.thumb))
    for c in result["checks"]: print(f"{'PASS' if c['passed'] else 'FAIL'} {c['name']}: {c['detail']}")
    return 0 if result["passed"] else 1
