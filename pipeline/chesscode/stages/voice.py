import json
import re
import shutil
import subprocess

import imageio_ffmpeg

from .. import tts
from ..config import load
from ..context import StageError

INPUTS = ["script.json", "config/models.yaml"]
OUTPUTS = ["voice.json"]


def _duration_ms(path):
    result = subprocess.run(
        [imageio_ffmpeg.get_ffmpeg_exe(), "-i", str(path)],
        capture_output=True, text=True, check=False,
    )
    match = re.search(r"Duration: (\d+):(\d+):(\d+(?:\.\d+)?)", result.stderr)
    if not match:
        raise ValueError(f"ffprobe could not read audio duration for {path}")
    hours, minutes, seconds = match.groups()
    return round((int(hours) * 3600 + int(minutes) * 60 + float(seconds)) * 1000)


def run(ctx):
    try:
        script = json.loads((ctx.spec_dir / "script.json").read_text(encoding="utf-8"))
        cfg = load("models", root=ctx.repo_root)["tts"]
        provider = cfg["provider"]
        voice = cfg["voice"][ctx.language]
        audio_dir = ctx.spec_dir / "audio"
        audio_dir.mkdir(parents=True, exist_ok=True)
        rows = []
        for index, segment in enumerate(script["segments"]):
            text = segment["text"]
            source, words = tts.synthesize(
                provider, text, voice, ctx.language, ctx.repo_root / "data" / "tts_cache"
            )
            if not words:
                raise ValueError(f"segment {index} returned no word timings")
            segment_id = f"seg-{index:03d}"
            filename = f"{ctx.language}_{segment_id}.mp3"
            target = audio_dir / filename
            shutil.copyfile(source, target)
            rows.append({
                "segment_id": segment_id,
                "audio": f"audio/{filename}",
                "duration_ms": _duration_ms(target),
                "words": words,
            })
        (ctx.spec_dir / "voice.json").write_text(
            json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    except Exception as exc:
        if isinstance(exc, StageError):
            raise
        raise StageError(ctx.video_id, "voice", str(exc)) from exc
