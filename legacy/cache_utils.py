"""cache_utils.py — Simple content-addressed file cache (stdlib only).

Used to avoid regenerating identical TTS segments / board-frame images across
runs. No eviction/TTL — cache grows unbounded; clear the directory manually
if it becomes a problem.
"""

import hashlib
import os
import shutil
from typing import Optional


def cache_key(*parts: str) -> str:
    h = hashlib.sha256()
    for p in parts:
        h.update(p.encode("utf-8"))
        h.update(b"\x00")
    return h.hexdigest()


def get_cached(cache_dir: str, key: str, ext: str) -> Optional[str]:
    """Return the cached file path if present, else None."""
    path = os.path.join(cache_dir, f"{key}{ext}")
    return path if os.path.exists(path) else None


def put_cached(cache_dir: str, key: str, ext: str, src_path: str) -> str:
    """Copy src_path into the cache and return the cached path."""
    os.makedirs(cache_dir, exist_ok=True)
    dst = os.path.join(cache_dir, f"{key}{ext}")
    shutil.copyfile(src_path, dst)
    return dst
