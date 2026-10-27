import json
import re
import subprocess
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


def loudnorm(src: Path, dst: Path) -> None:
    values = _measure(src)
    dst.parent.mkdir(parents=True, exist_ok=True)
    filter_value = (
        "loudnorm=I=-14:TP=-1:LRA=11:linear=true:"
        f"measured_I={values['input_i']}:measured_TP={values['input_tp']}:"
        f"measured_LRA={values['input_lra']}:measured_thresh={values['input_thresh']}:"
        f"offset={values['target_offset']}"
    )
    subprocess.run([
        imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-i", str(src), "-af", filter_value,
        "-ar", "48000", "-codec:a", "libmp3lame", "-q:a", "2", str(dst),
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
