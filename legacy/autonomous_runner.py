"""autonomous_runner.py — Scheduled content generation and upload runner.

Run this in the background to automatically generate and upload videos
on the configured schedule (Mon + Thu at 09:00 IST by default).

Usage:
    python autonomous_runner.py
"""

import logging
import subprocess
import sys
import time
from datetime import datetime

import pytz
import schedule

from config import cfg
from content_calendar import ContentCalendar

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("runner.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("runner")

IST = pytz.timezone("Asia/Kolkata")


def _run_pipeline_for(item: dict) -> bool:
    """Run main.py for a queue item. Returns True on success."""
    content_type = item["content_type"]
    content_id = item["content_id"]
    title = item["title"]
    logger.info(f"Processing [{content_type}] {title!r}")

    cmd = [sys.executable, "main.py"]
    if content_type == "game":
        cmd.extend([content_id])
    elif content_type == "opening":
        cmd.extend(["--opening", content_id])
    elif content_type == "trap":
        cmd.extend(["--trap", content_id])
    else:
        logger.warning(f"Unknown content_type {content_type!r}, skipping")
        return False

    cmd.extend(["--hindi", "--upload"])
    try:
        result = subprocess.run(cmd, timeout=3600, check=True)
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Pipeline failed for {title!r}: exit code {e.returncode}")
        return False
    except subprocess.TimeoutExpired:
        logger.error(f"Pipeline timed out for {title!r}")
        return False


def _run_scheduled_job() -> None:
    """Called by scheduler on each Mon/Thu slot."""
    cal = ContentCalendar(cfg.db_path)
    batch = cal.get_next_batch(n=1)

    if not batch:
        logger.info("Queue empty — nothing to process this slot")
        return

    item = dict(batch[0])
    queue_id = item["id"]
    cal.mark_status(queue_id, "processing")

    success = _run_pipeline_for(item)

    if success:
        cal.mark_status(queue_id, "done")
        logger.info(f"Completed: {item['title']!r}")
    else:
        cal.mark_status(queue_id, "failed")
        logger.error(f"Failed: {item['title']!r} — marked as failed")


def _ist_to_local_time(ist_time_str: str) -> str:
    """Convert "HH:MM" IST to system-local "HH:MM" for the schedule library.

    schedule always uses the system clock, so we must convert IST→system-local.
    On an IST machine this is a no-op; on a UTC server it subtracts 5h30m.
    """
    import time as _time
    h, m = map(int, ist_time_str.split(":"))
    ist_offset_min = 5 * 60 + 30
    # system UTC offset in minutes (positive = east)
    sys_offset_min = -_time.timezone // 60
    total = h * 60 + m - ist_offset_min + sys_offset_min
    total %= 24 * 60
    return f"{total // 60:02d}:{total % 60:02d}"


def start() -> None:
    """Start the scheduler loop. Blocks forever."""
    local_time = _ist_to_local_time(cfg.upload_time_ist)

    schedule.every().monday.at(local_time).do(_run_scheduled_job)
    schedule.every().thursday.at(local_time).do(_run_scheduled_job)

    logger.info(
        f"Runner started — jobs Mon+Thu at {cfg.upload_time_ist} IST ({local_time} system-local)"
    )
    logger.info("Press Ctrl+C to stop")

    try:
        while True:
            schedule.run_pending()
            time.sleep(30)
    except KeyboardInterrupt:
        logger.info("Runner stopped")


if __name__ == "__main__":
    start()
