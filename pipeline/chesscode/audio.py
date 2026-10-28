import json
import re
import subprocess
import tempfile
from pathlib import Path

import imageio_ffmpeg


def _measure(path: Path) -> dict:
    result = subprocess.run(
        [imageio_ffmpeg.get_ffmpeg_exe(), "-i", str(path), "-af",
         "loudnorm=I=-14:TP=-1:LRA=11:print_format=json", "-f", "null", "-"],
        capture_output=True, text=True, check=False,
    )
    matches = re.findall(r"\{[^{}]*\"input_i\"[^{}]*\}", result.stderr, re.S)
    if not matches:
        raise RuntimeError("ffmpeg did not return loudness measurements")
    return json.loads(matches[-1])


def measure(path: Path) -> dict:
    values = _measure(path)
    return {"input_i": float(values["input_i"]), "input_tp": float(values["input_tp"])}


def loudnorm(src: Path, dst: Path, passes: int = 6) -> None:
    """Normalize speech to -14 LUFS integrated with true peak <= -1 dBTP (spec section 4).

    ffmpeg's single-pass loudnorm cannot lift peaky speech to -14 under the peak cap
    (bake-off: -15.7 LUFS), so apply gain, brick-wall limit at -2.5 dBFS, re-measure, repeat.
    """
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    dst.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        current = Path(tmp) / "pass0.wav"
        _run([ffmpeg, "-y", "-i", str(src), "-ar", "48000", str(current)])
        for i in range(1, passes + 1):
            gain = -14.0 - float(_measure(current)["input_i"])
            if abs(gain) < 0.3:
                break
            nxt = Path(tmp) / f"pass{i}.wav"
            _run([ffmpeg, "-y", "-i", str(current), "-af", f"volume={gain:.2f}dB,alimiter=limit=0.75:level=disabled", str(nxt)])
            current = nxt
        _run([ffmpeg, "-y", "-i", str(current), "-ar", "48000", "-codec:a", "libmp3lame", "-b:a", "192k", str(dst)])


def _run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
