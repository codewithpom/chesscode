"""lichess_api.py — Thin, domain-allowlisted GET proxy for the Lichess APIs.

Lets the MCP layer (and the connecting LLM) pull arbitrary read-only data from
Lichess — the Opening Explorer (top games + player names), player profiles,
game exports, tournament data, etc. — without hard-coding one endpoint per need.

Safety: only the three official Lichess hosts are permitted; any other host is
rejected. Read-only GET only. The optional LICHESS_TOKEN is attached as a Bearer
header when present (raises rate limits) but is never required.
"""

import logging
from typing import Optional, Union

import requests

logger = logging.getLogger(__name__)

# Only these hosts may be contacted.
ALLOWED_HOSTS = {
    "lichess.org":            "https://lichess.org",
    "explorer.lichess.ovh":   "https://explorer.lichess.ovh",
    "lichess.ovh":            "https://lichess.ovh",
}

DEFAULT_TIMEOUT = 8.0


class LichessError(RuntimeError):
    """Raised for a disallowed host or a failed/blocked request."""


def fetch(host: str, path: str, params: Optional[dict] = None,
          timeout: float = DEFAULT_TIMEOUT) -> Union[dict, list, str]:
    """GET https://{host}{path}?{params} and return parsed JSON (dict/list) or
    raw text for non-JSON (e.g. NDJSON streams, PGN).

    host must be one of ALLOWED_HOSTS. Raises LichessError on a disallowed host
    or a network/HTTP failure.
    """
    if host not in ALLOWED_HOSTS:
        raise LichessError(
            f"Host '{host}' not allowed. Use one of: {', '.join(sorted(ALLOWED_HOSTS))}")

    base = ALLOWED_HOSTS[host]
    if not path.startswith("/"):
        path = "/" + path
    url = base + path

    headers = {"Accept": "application/json", "User-Agent": "ChessCode/1.0"}
    try:
        from config import cfg
        token = getattr(cfg, "lichess_token", "") or ""
    except Exception:
        token = ""
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        resp = requests.get(url, params=params or {}, headers=headers, timeout=timeout)
    except requests.RequestException as e:
        raise LichessError(f"Request to {url} failed: {e}") from e

    if resp.status_code in (401, 429):
        raise LichessError(
            f"Lichess {resp.status_code} for {url} — the API is rate-limiting/temporarily "
            f"blocking this IP (no WWW-Authenticate challenge = a deliberate deny, not a "
            f"login prompt). Slow down and retry after a cooldown; results are cached so "
            f"repeat calls for the same opening don't re-hit the network.")
    if resp.status_code >= 400:
        raise LichessError(
            f"Lichess returned HTTP {resp.status_code} for {url}: {resp.text[:200]}")

    ctype = resp.headers.get("Content-Type", "")
    if "application/json" in ctype:
        try:
            return resp.json()
        except ValueError:
            return resp.text
    return resp.text
