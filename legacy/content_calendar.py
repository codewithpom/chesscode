"""content_calendar.py — Content queue and YouTube scheduling for ChessCode."""

import sqlite3
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)


def _get_db(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _init_db(db_path: str) -> None:
    """Create tables if they don't exist."""
    with _get_db(db_path) as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS content_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content_type TEXT NOT NULL,
                content_id TEXT NOT NULL,
                title TEXT NOT NULL,
                priority INTEGER DEFAULT 5,
                status TEXT DEFAULT 'pending',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS scheduled_videos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                queue_id INTEGER REFERENCES content_queue(id),
                video_path TEXT,
                language TEXT DEFAULT 'en',
                scheduled_at DATETIME,
                youtube_id TEXT,
                status TEXT DEFAULT 'pending'
            );
        """)


class ContentCalendar:
    """Manages the content queue and upload schedule for ChessCode."""

    def __init__(self, db_path: str = "chesscode.db"):
        self._db_path = db_path
        _init_db(db_path)

    # ── Queue management ──────────────────────────────────────────────────────

    def add(
        self,
        content_type: str,
        content_id: str,
        title: str,
        priority: int = 5,
    ) -> int:
        """Add an item to the queue. Returns new row id."""
        with _get_db(self._db_path) as conn:
            cur = conn.execute(
                "INSERT INTO content_queue (content_type, content_id, title, priority) "
                "VALUES (?, ?, ?, ?)",
                (content_type, content_id, title, priority),
            )
            conn.commit()
            logger.info(f"Queued [{content_type}] {title!r} (priority={priority})")
            return cur.lastrowid

    def get_next_batch(self, n: int = 4) -> List[sqlite3.Row]:
        """Return next n pending items ordered by priority desc, then created_at asc."""
        with _get_db(self._db_path) as conn:
            rows = conn.execute(
                "SELECT * FROM content_queue WHERE status = 'pending' "
                "ORDER BY priority DESC, created_at ASC LIMIT ?",
                (n,),
            ).fetchall()
        return rows

    def mark_status(self, queue_id: int, status: str) -> None:
        with _get_db(self._db_path) as conn:
            conn.execute(
                "UPDATE content_queue SET status = ? WHERE id = ?",
                (status, queue_id),
            )
            conn.commit()

    def schedule_upload(
        self,
        video_path: str,
        language: str,
        scheduled_at: datetime,
        queue_id: Optional[int] = None,
    ) -> int:
        """Queue a rendered video for YouTube upload at scheduled_at time."""
        with _get_db(self._db_path) as conn:
            cur = conn.execute(
                "INSERT INTO scheduled_videos (queue_id, video_path, language, scheduled_at) "
                "VALUES (?, ?, ?, ?)",
                (queue_id, video_path, language, scheduled_at.isoformat()),
            )
            conn.commit()
            return cur.lastrowid

    def set_youtube_id(self, scheduled_id: int, youtube_id: str) -> None:
        with _get_db(self._db_path) as conn:
            conn.execute(
                "UPDATE scheduled_videos SET youtube_id = ?, status = 'uploaded' WHERE id = ?",
                (youtube_id, scheduled_id),
            )
            conn.commit()

    def get_pending_uploads(self) -> List[sqlite3.Row]:
        """Return scheduled videos that are past their scheduled_at and not yet uploaded."""
        now = datetime.utcnow().isoformat()
        with _get_db(self._db_path) as conn:
            return conn.execute(
                "SELECT * FROM scheduled_videos WHERE status = 'pending' AND scheduled_at <= ?",
                (now,),
            ).fetchall()

    # ── Schedule helpers ──────────────────────────────────────────────────────

    def next_upload_slots(self, count: int = 4) -> List[datetime]:
        """Return next `count` Mon/Thu 09:00 IST slots from now (as UTC datetimes)."""
        import pytz
        ist = pytz.timezone("Asia/Kolkata")
        now_ist = datetime.now(ist)
        slots = []
        candidate = now_ist.replace(hour=9, minute=0, second=0, microsecond=0)
        if candidate <= now_ist:
            candidate += timedelta(days=1)
        while len(slots) < count:
            # Monday=0, Thursday=3
            if candidate.weekday() in (0, 3):
                slots.append(candidate.astimezone(pytz.utc).replace(tzinfo=None))
            candidate += timedelta(days=1)
        return slots

    # ── Status for dashboard ──────────────────────────────────────────────────

    def get_status(self) -> dict:
        """Return summary dict for dashboard display."""
        with _get_db(self._db_path) as conn:
            queue_rows = conn.execute("SELECT * FROM content_queue ORDER BY priority DESC, created_at ASC").fetchall()
            scheduled_rows = conn.execute(
                "SELECT sv.*, cq.title FROM scheduled_videos sv "
                "LEFT JOIN content_queue cq ON sv.queue_id = cq.id "
                "ORDER BY sv.scheduled_at ASC"
            ).fetchall()
        return {
            "queue": [dict(r) for r in queue_rows],
            "scheduled": [dict(r) for r in scheduled_rows],
        }
