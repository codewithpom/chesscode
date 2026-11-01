"""`chesscode batch --video <id> [--upload]`: one video end to end on a runner (spec section 9, job steps 4 to 8)."""
import argparse
import json
import logging
import shutil
import subprocess
import time
from datetime import datetime, timezone

from . import auth, qa, upload
from .context import REPO_ROOT
from .runner import run_video

log = logging.getLogger(__name__)
SPECS = REPO_ROOT / "build" / "specs"
REMOTION = REPO_ROOT / "remotion"


def _sh(cmd: list[str], cwd=None) -> None:
    subprocess.run(cmd, cwd=cwd, check=True)


def run_one(video_id: str, do_upload: bool = False, batch_id: str = "") -> int:
    """0 whenever a result.json was written (failed_qa and failed_upload included); exceptions mean a crash."""
    run_video(video_id, until="emit")
    spec_dir = SPECS / video_id
    spec = json.loads((spec_dir / "video_spec.json").read_text(encoding="utf-8"))
    mp4, thumb = spec_dir / "out.mp4", spec_dir / "thumb.png"
    npx = shutil.which("npx") or "npx"
    flags = [f"--props={spec_dir / 'video_spec.json'}", f"--public-dir={spec_dir}"]
    started = time.monotonic()
    _sh([npx, "remotion", "render", "ShortsVideo" if spec["template"] == "shorts" else "StudioVideo", str(mp4), *flags,
         "--codec=h264", "--crf=18", "--x264-preset=veryfast", "--concurrency=100%"], cwd=REMOTION)
    _sh([npx, "remotion", "still", "Thumbnail", str(thumb), *flags], cwd=REMOTION)
    render_seconds = round(time.monotonic() - started)
    passed = bool(qa.run_checks(spec_dir, mp4, thumb)["passed"])
    result = {"video_id": video_id, "status": "rendered" if passed else "failed_qa", "youtube_id": "", "publish_at": spec["youtube"]["publish_at"],
              "title": spec["youtube"]["title"], "qa_passed": passed, "render_seconds": render_seconds, "batch_id": batch_id}
    if passed and do_upload:
        try:
            result.update(upload.upload_from_spec(auth.youtube_client(), spec_dir, REPO_ROOT / "data" / "upload_log.csv", datetime.now(timezone.utc)))
        except upload.UploadRefused as exc:
            result.update(status="failed_upload", error=str(exc))
        except upload.TRANSIENT as exc:  # retries are exhausted inside upload_video; the playlist check on the next run finds a landed upload
            status = getattr(getattr(exc, "resp", None), "status", "")
            result.update(status="failed_upload", error=f"{type(exc).__name__} {status}".strip())
    (spec_dir / "result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("video_id", "status", "qa_passed", "render_seconds")}))
    return 0


def main(args: argparse.Namespace) -> int:
    try:
        return run_one(args.video, args.upload, args.batch_id or "")
    except Exception as exc:
        log.error("%s: batch crashed: %s", args.video, exc)
        print(f"batch crashed for {args.video}: {exc}")
        return 1
