import subprocess
from pathlib import Path

import imageio_ffmpeg

from chesscode import audio


def test_loudnorm_hits_target(tmp_path):
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    source = tmp_path / "source.wav"
    target = tmp_path / "normalized.mp3"
    subprocess.run([ffmpeg, "-y", "-f", "lavfi", "-i", "sine=frequency=440:duration=2", str(source)],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    audio.loudnorm(source, target)
    result = audio.measure(target)
    assert -15 <= result["input_i"] <= -13
    assert result["input_tp"] <= -1.0


def test_loudnorm_lifts_peaky_signal_into_window(tmp_path):
    """Sparse clicks over a quiet tone: single-pass loudnorm left this below -15 LUFS."""
    import subprocess, imageio_ffmpeg
    from chesscode import audio
    src = tmp_path / "peaky.wav"
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-f", "lavfi", "-i",
                    "sine=frequency=220:duration=6,volume=0.02[a];aevalsrc=0.9*gt(mod(t\,0.5)\,0.49):d=6[b];[a][b]amix=inputs=2",
                    str(src)], check=True, capture_output=True)
    out = tmp_path / "out.mp3"
    audio.loudnorm(src, out)
    m = audio.measure(out)
    assert -15 <= m["input_i"] <= -13
    assert m["input_tp"] <= -1.0
