"""channel_stats.py — Channel subscriber/view stats via YouTube Data API v3.

Requires env vars:
  YOUTUBE_API_KEY     — plain API key (Google Cloud Console → Credentials),
                         NOT the OAuth client used by youtube_uploader.py for
                         uploads. Public channel statistics only need a key.
  YOUTUBE_CHANNEL_ID  — the channel's UC... id.

Both optional: if either is missing, get_channel_stats() returns None and the
stats-intro simply omits the channel ribbon. Every failure degrades to None
(or a stale cached value) — never raises into the render pipeline.
"""

import json
import logging
import os
import time
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

_API_URL = "https://www.googleapis.com/youtube/v3/channels"
_VIDEO_API_URL = "https://www.googleapis.com/youtube/v3/videos"


@dataclass
class ChannelStats:
    subscriber_count: int
    view_count: int
    fetched_at: float
    video_count: int = 0


@dataclass
class VideoStats:
    view_count: int
    like_count: int
    comment_count: int
    fetched_at: float


def get_channel_stats(api_key: str, channel_id: str,
                      cache_dir: str = "output/.cache/channel_stats",
                      ttl_seconds: int = 3600, timeout: float = 6.0
                      ) -> Optional[ChannelStats]:
    if not api_key or not channel_id:
        logger.info("channel_stats: YOUTUBE_API_KEY/YOUTUBE_CHANNEL_ID not set — skipping channel ribbon")
        return None

    cache_path = os.path.join(cache_dir, f"{channel_id}.json")
    fresh = _read_cache(cache_path, ttl_seconds)
    if fresh:
        return fresh

    try:
        import requests
        resp = requests.get(_API_URL, params={
            "part": "statistics", "id": channel_id, "key": api_key,
        }, timeout=timeout)
        resp.raise_for_status()
        items = resp.json().get("items", [])
        if not items:
            logger.warning(f"channel_stats: no channel found for id {channel_id}")
            return _read_cache(cache_path, ttl_seconds=float("inf"))
        stats = items[0]["statistics"]
        result = ChannelStats(
            subscriber_count=int(stats.get("subscriberCount", 0)),
            view_count=int(stats.get("viewCount", 0)),
            fetched_at=time.time(),
            video_count=int(stats.get("videoCount", 0)),
        )
        _write_cache(cache_path, result)
        return result
    except Exception as e:
        logger.warning(f"channel_stats: fetch failed, falling back to cache if any: {e}")
        return _read_cache(cache_path, ttl_seconds=float("inf"))


def get_video_stats(api_key: str, video_id: str,
                    timeout: float = 6.0) -> Optional[VideoStats]:
    """Fetch view/like/comment counts for a single YouTube video via Data API v3.

    Returns None if the api_key/video_id is missing, the id is unknown, or the
    request fails — never raises. Not cached (video stats change frequently and
    callers want a live read).
    """
    if not api_key or not video_id:
        logger.info("video_stats: YOUTUBE_API_KEY/video_id not set — skipping")
        return None

    try:
        import requests
        resp = requests.get(_VIDEO_API_URL, params={
            "part": "statistics", "id": video_id, "key": api_key,
        }, timeout=timeout)
        resp.raise_for_status()
        items = resp.json().get("items", [])
        if not items:
            logger.warning(f"video_stats: no video found for id {video_id}")
            return None
        stats = items[0]["statistics"]
        return VideoStats(
            view_count=int(stats.get("viewCount", 0)),
            like_count=int(stats.get("likeCount", 0)),
            comment_count=int(stats.get("commentCount", 0)),
            fetched_at=time.time(),
        )
    except Exception as e:
        logger.warning(f"video_stats: fetch failed for {video_id}: {e}")
        return None


def _read_cache(cache_path: str, ttl_seconds: float) -> Optional[ChannelStats]:
    if not os.path.exists(cache_path):
        return None
    if time.time() - os.path.getmtime(cache_path) > ttl_seconds:
        return None
    try:
        with open(cache_path, encoding="utf-8") as f:
            d = json.load(f)
        return ChannelStats(**d)
    except Exception:
        return None


def _write_cache(cache_path: str, stats: ChannelStats) -> None:
    try:
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(stats.__dict__, f)
    except OSError as e:
        logger.warning(f"channel_stats: failed to write cache: {e}")
