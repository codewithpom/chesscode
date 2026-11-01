"""Fetch the CC0 Kenney packs, pick one sound per beat sfx id, convert to 48 kHz mono MP3 (peak <= -12 dBFS).

    python scripts/fetch_sfx.py --raw-dir <empty dir outside the repo>

Raw downloads are untrusted data: they stay in --raw-dir, only members named in PICKS are read (as bytes,
never extracted by path), and nothing from the archives is executed. Only the converted MP3s are written to
remotion/src/assets/sfx/. The licence line of each pack is read from its License.txt and must say CC0, or the
script stops. CREDITS.md gets one row per sound (idempotent).
"""
import argparse
import json
import re
import subprocess
import sys
import urllib.request
import zipfile
from http.cookiejar import CookieJar
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "remotion" / "src" / "assets" / "sfx"
CREDITS = ROOT / "remotion" / "public" / "CREDITS.md"
LIMIT_DB = -15.0  # limiter ceiling; MP3 encoding overshoots a transient by up to 3 dB, the hard limit is -12 dBFS
MOMENTARY_TARGET_LUFS = -21.0  # 6.5 LU under the -14.5 LUFS voice (design review: 6-10 LU under)
MAX_SECONDS = 2.0
UA = "Mozilla/5.0"

PACKS = {  # slug on kenney.nl -> pack name
    "interface-sounds": "Interface Sounds",
    "impact-sounds": "Impact Sounds",
    "ui-audio": "UI Audio",
}
# sfx id (config/beats.yaml) -> (pack slug, member). Judged by ear-free role: thud, question, bell, record scratch...
PICKS = {
    "oof_01": ("impact-sounds", "Audio/impactSoft_heavy_000.ogg"),  # blunder: dull thud
    "hmm_01": ("interface-sounds", "Audio/question_001.ogg"),  # mistake: questioning blip
    "ding_01": ("interface-sounds", "Audio/confirmation_002.ogg"),  # brilliant
    "gasp_01": ("interface-sounds", "Audio/scratch_001.ogg"),  # missed win: record scratch
    "whip_01": ("interface-sounds", "Audio/maximize_009.ogg"),  # comeback: rising sweep
    "tick_01": ("interface-sounds", "Audio/tick_001.ogg"),  # long think
    "tick_02": ("interface-sounds", "Audio/tick_002.ogg"),  # time scramble
    "sparkle_01": ("interface-sounds", "Audio/glass_003.ogg"),  # promotion
    "sting_01": ("impact-sounds", "Audio/impactBell_heavy_000.ogg"),  # checkmate: bell
    "sting_02": ("interface-sounds", "Audio/drop_004.ogg"),  # resign: falling drop
}


def ffmpeg() -> str:
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        return "ffmpeg"


def download(slug: str, dest: Path) -> None:
    """kenney.nl hands out a signed link after a cookie + referer round trip (its own download button does the same)."""
    jar = CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    page = f"https://kenney.nl/assets/{slug}"
    op.open(urllib.request.Request(page, headers={"User-Agent": UA}), timeout=30).read()
    ident = f"assets/{slug}".encode().hex()
    req = urllib.request.Request(
        f"https://kenney.nl/download-link/{ident}",
        headers={"User-Agent": UA, "Referer": page, "X-Requested-With": "XMLHttpRequest"},
    )
    url = json.load(op.open(req, timeout=30))["url"]
    dest.write_bytes(op.open(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=180).read())


def licence_ok(z: zipfile.ZipFile) -> str:
    text = z.read("License.txt").decode("utf8", "replace")
    if not re.search(r"Creative Commons Zero,\s*CC0", text):
        sys.exit("pack licence is not CC0: stop")
    return "CC0 1.0 (Creative Commons Zero)"


def peak_db(exe: str, path: Path) -> float:
    out = subprocess.run([exe, "-hide_banner", "-i", str(path), "-af", "volumedetect", "-f", "null", "-"], capture_output=True, text=True)
    return float(re.search(r"max_volume: (-?[\d.]+) dB", out.stderr).group(1))


def momentary_max(exe: str, path: Path) -> float:
    """Loudest 400 ms momentary loudness (LUFS) of the file padded to 1 s, so a short sound is not read as -70."""
    out = subprocess.run([exe, "-hide_banner", "-nostats", "-i", str(path), "-af", "apad=whole_dur=1,ebur128", "-f", "null", "-"], capture_output=True, text=True)
    vals = [float(v) for v in re.findall(r"M:\s*(-?[\d.]+)", out.stderr)]
    return max(vals)


def encode(src: bytes, dst: Path, tmp: Path) -> tuple[float, float]:
    """Trim, then raise the sound to MOMENTARY_TARGET_LUFS with a limiter at LIMIT_DB so it cannot clip: a short
    transient cannot always get there, in which case it is as loud as the limit allows. Returns (peak dBFS, momentary max)."""
    exe = ffmpeg()
    tmp.write_bytes(src)
    base = f"silenceremove=start_periods=1:start_threshold=-50dB,atrim=0:{MAX_SECONDS},afade=t=out:st={MAX_SECONDS - 0.2}:d=0.2"

    def run(gain: float) -> Path:
        af = f"{base},volume={gain:.2f}dB,alimiter=limit={10 ** (LIMIT_DB / 20):.4f}:level=disabled"
        subprocess.run([exe, "-hide_banner", "-y", "-i", str(tmp), "-af", af, "-ar", "48000", "-ac", "1", "-b:a", "128k", str(dst)], check=True, capture_output=True)
        return dst

    lo, hi = -10.0, 30.0
    for _ in range(12):  # bisection on the pre-limiter gain
        mid = (lo + hi) / 2
        if momentary_max(exe, run(mid)) < MOMENTARY_TARGET_LUFS:
            lo = mid
        else:
            hi = mid
    run(hi)
    return peak_db(exe, dst), momentary_max(exe, dst)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw-dir", required=True, type=Path, help="where the zips go (untrusted data; outside the repo)")
    raw = ap.parse_args().raw_dir
    raw.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    zips: dict[str, zipfile.ZipFile] = {}
    licences: dict[str, str] = {}
    for slug in PACKS:
        path = raw / f"{slug}.zip"
        if not path.exists():
            download(slug, path)
        zips[slug] = zipfile.ZipFile(path)
        licences[slug] = licence_ok(zips[slug])
    rows = []
    for sfx_id, (slug, member) in PICKS.items():
        peak, momentary = encode(zips[slug].read(member), OUT / f"{sfx_id}.mp3", raw / "tmp.ogg")
        assert peak <= -12.0, f"{sfx_id} peaks at {peak} dBFS"
        rows.append(f"| {sfx_id}.mp3 | {PACKS[slug]} by Kenney, `{member}` | https://kenney.nl/assets/{slug} | {licences[slug]} |")
        print(f"{sfx_id}: {member} peak {peak} dBFS, momentary max {momentary} LUFS")
    section = (
        "\n## Sound effects (`src/assets/sfx/`)\n\n"
        "Kenney (https://kenney.nl) packs, each with a License.txt reading \"Creative Commons Zero, CC0\" "
        "(http://creativecommons.org/publicdomain/zero/1.0/), checked at download. Converted by `scripts/fetch_sfx.py` "
        "(48 kHz mono MP3, trimmed to 2 s, raised to a -21 LUFS momentary maximum behind a -15 dBFS limiter, every file verified <= -12 dBFS).\n\n"
        "| File | Source file | Pack page | License |\n| --- | --- | --- | --- |\n" + "\n".join(rows) + "\n"
    )
    text = CREDITS.read_text(encoding="utf8")
    text = re.sub(r"\n## Sound effects.*?(?=\n## |\Z)", "", text, flags=re.S).rstrip("\n") + "\n" + section
    CREDITS.write_text(text, encoding="utf8")


if __name__ == "__main__":
    main()
