#!/usr/bin/env python3
import argparse
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))

import imageio_ffmpeg

from chesscode.auth import youtube_client
from chesscode.upload import build_body, check_publish_at, upload_video


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--publish-in-hours", type=int, required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    title = "ChessCode API test (delete me)"
    video_id = "cc-test-0000-en"
    publish_at = datetime.now(timezone.utc) + timedelta(hours=args.publish_in_hours)
    description = "Throwaway scheduled API test."
    check_publish_at(publish_at, datetime.now(timezone.utc))
    body = build_body(video_id, title, description, [], publish_at, "en")
    clip_path = ROOT / "build" / "day1-test.mp4"
    clip_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([
        imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-f", "lavfi", "-i",
        "testsrc=size=1280x720:rate=30", "-f", "lavfi", "-i",
        "sine=frequency=1000:sample_rate=48000", "-t", "5", "-pix_fmt",
        "yuv420p", str(clip_path),
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"clip: {clip_path}")
    if args.dry_run:
        print(json.dumps(body, indent=2))
        return 0
    youtube_id = upload_video(youtube_client(), clip_path, video_id, title,
                              description, [], publish_at, "en")
    print(f"https://studio.youtube.com/video/{youtube_id}/edit")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
