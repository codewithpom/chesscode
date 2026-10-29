"""data/upload_log.csv: one row per state change, last row per video wins; `chesscode ledger check` compares it with YouTube."""
import argparse
import csv
import re
from datetime import datetime
from pathlib import Path

from .context import REPO_ROOT

COLUMNS = ["video_id", "status", "youtube_id", "publish_at", "title", "qa_passed", "render_seconds", "batch_id", "updated_at"]
STATUSES = {"scheduled", "failed_qa", "failed_upload", "deferred", "rendered"}
LEDGER = REPO_ROOT / "data" / "upload_log.csv"


def read_ledger(path: Path) -> dict[str, dict]:
    path = Path(path)
    if not path.is_file(): return {}
    with path.open(encoding="utf-8", newline="") as f:
        return {r["video_id"]: r for r in csv.DictReader(f)}


def append(path: Path, row: dict) -> None:
    missing = [c for c in COLUMNS if c not in row]
    if missing: raise ValueError(f"ledger row for {row.get('video_id')} lacks column(s): {', '.join(missing)}")
    if row["status"] not in STATUSES: raise ValueError(f"ledger status {row['status']!r} is not one of {sorted(STATUSES)}")
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    new = not path.is_file() or path.stat().st_size == 0
    with path.open("a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, COLUMNS, extrasaction="ignore", lineterminator="\n")
        if new: w.writeheader()
        w.writerow(row)


def youtube_uploads(client) -> dict[str, dict]:
    """ccid -> {youtube_id, publish_at, privacy} for every video in the channel's uploads playlist."""
    playlist = client.channels().list(part="contentDetails", mine=True).execute()["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
    found, token = {}, None
    while True:
        page = client.playlistItems().list(part="snippet", playlistId=playlist, maxResults=50, pageToken=token).execute()
        for item in page.get("items", []):
            m = re.search(r"^ccid: (\S+)\s*$", item["snippet"].get("description", ""), re.M)
            if m: found[m[1]] = {"youtube_id": item["snippet"]["resourceId"]["videoId"]}
        token = page.get("nextPageToken")
        if not token: break
    by_yt = {v["youtube_id"]: v for v in found.values()}
    ids = list(by_yt)
    for i in range(0, len(ids), 50):
        for v in client.videos().list(part="status", id=",".join(ids[i:i + 50])).execute().get("items", []):
            by_yt[v["id"]].update(publish_at=v["status"].get("publishAt", ""), privacy=v["status"].get("privacyStatus", ""))
    return found


def _utc(text: str) -> datetime | None:
    return datetime.fromisoformat(text.replace("Z", "+00:00")) if text else None


def check(client, path: Path) -> list[str]:
    rows = read_ledger(path); live = youtube_uploads(client); problems = []
    for vid, r in rows.items():
        if r["status"] != "scheduled": continue
        if vid not in live: problems.append(f"{vid}: missing in Studio (ledger says scheduled as {r['youtube_id']})")
        elif _utc(live[vid].get("publish_at", "")) != _utc(r["publish_at"]):
            problems.append(f"{vid}: different publishAt (ledger {r['publish_at']}, Studio {live[vid].get('publish_at') or 'none'})")
    for vid in live:
        if vid not in rows: problems.append(f"{vid}: missing in ledger (Studio has {live[vid]['youtube_id']})")
    return problems


def main(args: argparse.Namespace) -> int:
    from . import auth
    problems = check(auth.youtube_client(), LEDGER)
    for p in problems: print(p)
    print(f"ledger check: {len(problems)} mismatch(es)")
    return 1 if problems else 0
