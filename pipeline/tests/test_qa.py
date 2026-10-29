import json
import shutil
import subprocess
from pathlib import Path

import imageio_ffmpeg
import pytest

from chesscode import audio, qa

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "spec" / "fixtures" / "cc-2026-0001-en" / "video_spec.json"
FF = imageio_ffmpeg.get_ffmpeg_exe()


def ffmpeg(*args):
    subprocess.run([FF, "-y", "-loglevel", "error", *args], check=True)


def make_mp4(path, dur=6, silent=None, black=None, fps=30, size="320x180"):
    """Tiny h264/aac clip: a tone with an optional silent span and an optional black span (seconds)."""
    tone = "0.3*sin(2*PI*440*t)"
    if silent: tone = f"if(between(t,{silent[0]},{silent[1]}),0,{tone})"
    video = f"testsrc2=s={size}:r={fps}:d={dur}"
    if black: video += f",drawbox=x=0:y=0:w=iw:h=ih:color=black:t=fill:enable='between(t,{black[0]},{black[1]})'"
    ffmpeg("-f", "lavfi", "-i", video, "-f", "lavfi", "-i", f"aevalsrc='{tone}':d={dur}:s=44100",
           "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(path))


def make_spec(tmp_path, narration, duration_ms=6000, fps=30, size=(320, 180)):
    spec = json.loads(FIXTURE.read_text(encoding="utf-8"))
    spec.update(narration=narration, duration_ms=duration_ms, format={"width": size[0], "height": size[1], "fps": fps})
    (tmp_path / "video_spec.json").write_text(json.dumps(spec), encoding="utf-8")
    return spec


def seg(i, start, dur, audio_path="a.wav"):
    return {"segment_id": f"seg-{i}", "kind": "ply", "ply": 1, "text": "x", "audio": audio_path, "start_ms": start, "duration_ms": dur}


# silence from 1 s to 4 s
def test_dead_air_outside_planned_gap_fails(tmp_path):
    make_spec(tmp_path, [seg(0, 0, 1000), seg(1, 1000, 3000), seg(2, 4000, 2000)])  # the 3 s is "narrated" yet silent
    make_mp4(tmp_path / "o.mp4", silent=(1, 4))
    with pytest.raises(ValueError, match="dead air"):
        qa.check_dead_air(spec_dir=tmp_path, mp4=tmp_path / "o.mp4")


def test_dead_air_inside_planned_gap_passes(tmp_path):
    make_spec(tmp_path, [seg(0, 0, 1000), seg(1, 4000, 2000)])  # 1 s to 4 s is a planned pause
    make_mp4(tmp_path / "o.mp4", silent=(1, 4))
    qa.check_dead_air(spec_dir=tmp_path, mp4=tmp_path / "o.mp4")


def test_dead_air_in_outro_passes(tmp_path):
    make_spec(tmp_path, [seg(0, 0, 3000)])  # silent tail after the last segment is the outro
    make_mp4(tmp_path / "o.mp4", silent=(3, 6))
    qa.check_dead_air(spec_dir=tmp_path, mp4=tmp_path / "o.mp4")


def test_black_segment_fails_but_black_edges_pass(tmp_path):
    make_spec(tmp_path, [seg(0, 0, 6000)])
    make_mp4(tmp_path / "bad.mp4", black=(2, 3))
    with pytest.raises(ValueError, match="black"):
        qa.check_black_frames(spec_dir=tmp_path, mp4=tmp_path / "bad.mp4")
    make_mp4(tmp_path / "ok.mp4", black=(0, 0.15))
    qa.check_black_frames(spec_dir=tmp_path, mp4=tmp_path / "ok.mp4")


def test_file_format(tmp_path):
    make_spec(tmp_path, [seg(0, 0, 6000)])
    make_mp4(tmp_path / "ok.mp4")
    qa.check_file_format(spec_dir=tmp_path, mp4=tmp_path / "ok.mp4")
    make_mp4(tmp_path / "fps.mp4", fps=25)
    with pytest.raises(ValueError, match="fps"):
        qa.check_file_format(spec_dir=tmp_path, mp4=tmp_path / "fps.mp4")
    make_mp4(tmp_path / "short.mp4", dur=5)
    with pytest.raises(ValueError, match="duration"):
        qa.check_file_format(spec_dir=tmp_path, mp4=tmp_path / "short.mp4")


def test_audio_levels(tmp_path):
    raw, good, quiet = tmp_path / "raw.wav", tmp_path / "good.wav", tmp_path / "quiet.wav"
    ffmpeg("-f", "lavfi", "-i", "sine=f=220:d=4", "-ar", "44100", str(raw))
    audio.loudnorm(raw, good)
    ffmpeg("-i", str(good), "-af", "volume=-4dB", str(quiet))  # -18 LUFS
    make_spec(tmp_path, [seg(0, 0, 4000, "good.wav")])
    qa.check_audio_levels(spec_dir=tmp_path)
    make_spec(tmp_path, [seg(0, 0, 4000, "quiet.wav")])
    with pytest.raises(ValueError, match="seg-0"):
        qa.check_audio_levels(spec_dir=tmp_path)


def test_mascot_lines_cap_and_repeats(tmp_path):
    spec = make_spec(tmp_path, [seg(0, 0, 6000)])
    qa.check_mascot_lines(spec_dir=tmp_path)
    spec["beats"][1]["mascot"]["line"] = spec["beats"][0]["mascot"]["line"]
    (tmp_path / "video_spec.json").write_text(json.dumps(spec), encoding="utf-8")
    with pytest.raises(ValueError, match="repeated"):
        qa.check_mascot_lines(spec_dir=tmp_path)


def test_moves_real_flags_invented_move(tmp_path):
    spec = make_spec(tmp_path, [seg(0, 0, 6000)])
    spec["narration"][0]["text"] = "Then Qh7 mates"
    (tmp_path / "video_spec.json").write_text(json.dumps(spec), encoding="utf-8")
    with pytest.raises(ValueError, match="Qh7"):
        qa.check_moves_real(spec_dir=tmp_path)


def test_run_checks_writes_qa_json_and_artifacts(tmp_path):
    make_spec(tmp_path, [seg(0, 0, 6000)])
    make_mp4(tmp_path / "o.mp4")
    ffmpeg("-f", "lavfi", "-i", "testsrc2=s=1280x720:d=1", "-frames:v", "1", str(tmp_path / "thumb.png"))
    result = qa.run_checks(tmp_path, tmp_path / "o.mp4", tmp_path / "thumb.png")
    assert result["passed"] is False  # fixture narration audio files do not exist
    assert json.loads((tmp_path / "qa.json").read_text(encoding="utf-8"))["video_id"] == "cc-2026-0001-en"
    assert (tmp_path / "contact.jpg").stat().st_size > 0 and (tmp_path / "thumb_320.png").stat().st_size > 0
    by_name = {c["name"]: c for c in result["checks"]}
    assert by_name["file_format"]["passed"] and by_name["black_frames"]["passed"] and not by_name["audio_levels"]["passed"]


def test_cli_exits_1_on_failed_qa(tmp_path, monkeypatch):
    from chesscode.__main__ import main
    monkeypatch.setattr(qa, "run_checks", lambda *a: {"passed": False, "checks": []})
    assert main(["qa", "--video", "cc-2026-0001-en", "--mp4", "x.mp4", "--thumb", "t.png"]) == 1
