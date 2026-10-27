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
