import argparse
import http.client
import json
import logging
import re
import socket
import time
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
import httplib2

from chesscode import auth
from chesscode.config import load
from chesscode.context import REPO_ROOT
from chesscode.ledger import read_ledger
from chesscode.stages.metadata import _SERIES

log = logging.getLogger(__name__)
PACIFIC = ZoneInfo("America/Los_Angeles")
TRANSIENT = (HttpError, socket.error, http.client.HTTPException, httplib2.HttpLib2Error)


class UploadRefused(Exception):
    pass


def build_body(video_id: str, title: str, description: str, tags: list[str],
               publish_at: datetime, language: str) -> dict:
    if len(title) > 100:
        raise UploadRefused("title must be 100 characters or fewer")
    description = with_ccid_footer(description, video_id)
    if len(description) > 5000:
        raise UploadRefused("description must be 5000 characters or fewer")
    cfg = load("youtube")
    publish_utc = publish_at.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    return {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": str(cfg["category_id"]),
            "defaultLanguage": language,
            "defaultAudioLanguage": language,
        },
        "status": {
            "privacyStatus": "private",
            "publishAt": publish_utc,
            "selfDeclaredMadeForKids": False,
            "containsSyntheticMedia": cfg["contains_synthetic_media"],
        },
    }


def check_publish_at(publish_at: datetime, now: datetime) -> None:
    if publish_at.tzinfo is None or now.tzinfo is None:
        raise UploadRefused("publish_at and now must be timezone-aware")
    if publish_at < now or (publish_at - now).total_seconds() < 7200:
        raise UploadRefused("publish_at must be at least 2 hours in the future")


def with_ccid_footer(description: str, video_id: str) -> str:
    footer = f"ccid: {video_id}"
    if footer in description.splitlines():
        return description
    return f"{description.rstrip()}\n\n{footer}"


def find_existing(client, video_id: str) -> str | None:
    channels = client.channels().list(part="contentDetails", mine=True).execute()
    playlist_id = channels["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
    page_token = None
    footer = f"ccid: {video_id}"
    while True:
        response = client.playlistItems().list(
            part="snippet", playlistId=playlist_id, maxResults=50, pageToken=page_token
        ).execute()
        for item in response.get("items", []):
            if footer in item["snippet"].get("description", "").splitlines():
                return item["snippet"]["resourceId"]["videoId"]
        page_token = response.get("nextPageToken")
        if not page_token:
            return None


def upload_video(client, path: Path, video_id: str, title: str, description: str,
                 tags: list[str], publish_at: datetime, language: str,
                 now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    check_publish_at(publish_at, now)
    body = build_body(video_id, title, description, tags, publish_at, language)
    existing = find_existing(client, video_id)
    if existing:
        return existing
    return _insert(client, path, video_id, body)


def _insert(client, path: Path, video_id: str, body: dict) -> str:
    request = client.videos().insert(
        part="snippet,status", body=body, media_body=MediaFileUpload(str(path), resumable=True)
    )
    for attempt in range(5):
        try:
            return request.execute()["id"]
        except TRANSIENT as exc:
            retryable = not isinstance(exc, HttpError) or exc.resp.status >= 500
            if not retryable or attempt == 4:
                raise
            existing = find_existing(client, video_id)
            if existing:
                return existing
            time.sleep(2 ** attempt)


def _uploads_today(rows: dict[str, dict], now: datetime) -> int:
    day = now.astimezone(PACIFIC).date()
    return sum(1 for r in rows.values() if r["status"] == "scheduled" and r["updated_at"]
               and datetime.fromisoformat(r["updated_at"].replace("Z", "+00:00")).astimezone(PACIFIC).date() == day)


def _follow_ups(client, youtube_id: str, spec_dir: Path, playlist_id: str, check_playlist: bool) -> bool:
    """thumbnails.set then playlistItems.insert, independently; True when either failed (the video stays scheduled)."""
    failed = False
    try:
        client.thumbnails().set(videoId=youtube_id, media_body=MediaFileUpload(str(spec_dir / "thumb.png"))).execute()
    except TRANSIENT as exc:
        log.warning("%s: thumbnails.set failed (%s)", youtube_id, type(exc).__name__); failed = True
    try:
        listed = client.playlistItems().list(part="id", playlistId=playlist_id, videoId=youtube_id, maxResults=1).execute() if check_playlist else {}
        if not listed.get("items"):
            client.playlistItems().insert(part="snippet", body={"snippet": {"playlistId": playlist_id, "resourceId": {"kind": "youtube#video", "videoId": youtube_id}}}).execute()
    except TRANSIENT as exc:
        log.warning("%s: playlistItems.insert failed (%s)", youtube_id, type(exc).__name__); failed = True
    return failed


def upload_from_spec(client, spec_dir: Path, ledger_path: Path, now: datetime, repair: bool = False) -> dict:
    """One video from build/specs/<id>/ to a scheduled private upload; the result.json dict (spec 9 step 7)."""
    spec_dir = Path(spec_dir)
    spec = json.loads((spec_dir / "video_spec.json").read_text(encoding="utf-8"))
    vid, meta = spec["video_id"], spec["youtube"]
    qa_path = spec_dir / "qa.json"
    if not qa_path.is_file(): raise UploadRefused(f"{vid}: qa.json is missing; run chesscode qa before uploading")
    result = {"video_id": vid, "status": "scheduled", "youtube_id": "", "publish_at": meta["publish_at"]}
    if not json.loads(qa_path.read_text(encoding="utf-8"))["passed"]:
        return {**result, "status": "failed_qa"}
    prior = read_ledger(ledger_path).get(vid)
    scheduled = prior if prior and prior["status"] == "scheduled" and prior["youtube_id"] else None
    if repair:
        if not scheduled: raise UploadRefused(f"{vid}: --repair needs a scheduled row with a YouTube id in the ledger")
    elif scheduled:
        return {**result, "youtube_id": scheduled["youtube_id"], "skipped": True}
    else:
        existing = find_existing(client, vid)
        if existing: return {**result, "youtube_id": existing, "skipped": True}
    cfg = load("youtube")
    playlist_id = (cfg.get("playlists") or {}).get(spec["series"])
    if not playlist_id: raise UploadRefused(f"{vid}: no playlist id for series {spec['series']!r} in config/youtube.yaml; run chesscode upload --create-playlists")
    if repair:
        youtube_id = scheduled["youtube_id"]
    else:
        publish_at = datetime.fromisoformat(meta["publish_at"].replace("Z", "+00:00"))
        check_publish_at(publish_at, now)
        if _uploads_today(read_ledger(ledger_path), now) >= cfg["daily_cap"]: return {**result, "status": "deferred"}
        description = meta["description"]
        if spec["template"] == "shorts" and "#Shorts" not in description:  # YouTube has no Shorts flag; keep the ccid footer last
            description = description.replace(f"ccid: {vid}", "").rstrip() + "\n\n#Shorts"
        body = build_body(vid, meta["title"], description, meta["tags"], publish_at, meta["default_language"])
        youtube_id = _insert(client, spec_dir / "out.mp4", vid, body)
    needs_repair = _follow_ups(client, youtube_id, spec_dir, playlist_id, check_playlist=repair)
    return {**result, "youtube_id": youtube_id, **({"needs_repair": True} if needs_repair else {})}


def create_playlists(client, config_path: Path = REPO_ROOT / "config" / "youtube.yaml") -> dict[str, str]:
    """Reuse or create series playlists and save each resolved id before continuing."""
    import yaml
    text = config_path.read_text(encoding="utf-8")
    existing = {}
    page_token = None
    while True:
        page = client.playlists().list(part="snippet", mine=True, maxResults=50, pageToken=page_token).execute()
        for item in page.get("items", []):
            title = item["snippet"]["title"]
            existing.setdefault(title, []).append(item["id"])
        page_token = page.get("nextPageToken")
        if not page_token:
            break
    made = {}
    for key, current in (yaml.safe_load(text).get("playlists") or {}).items():
        if current: continue
        if key not in _SERIES: raise UploadRefused(f"unknown series {key!r} in {config_path}")
        matches = existing.get(_SERIES[key], [])
        if len(matches) > 1:
            raise UploadRefused(f"multiple playlists named {_SERIES[key]!r}; set its id in {config_path}")
        made[key] = matches[0] if matches else client.playlists().insert(part="snippet,status", body={
            "snippet": {"title": _SERIES[key]}, "status": {"privacyStatus": "public"}}).execute()["id"]
        text = re.sub(rf"^(\s*{key}:)\s*null\b.*$", lambda m: f"{m[1]} {made[key]}", text, flags=re.M)
        config_path.write_text(text, encoding="utf-8")  # per playlist, so a later failure keeps the ids already made
    return made


def main(args: argparse.Namespace) -> int:
    client = auth.youtube_client()
    if args.create_playlists:
        for key, pid in create_playlists(client).items(): print(f"{key}: {pid}")
        return 0
    spec_dir = REPO_ROOT / "build" / "specs" / args.video
    try:
        result = upload_from_spec(client, spec_dir, REPO_ROOT / "data" / "upload_log.csv", datetime.now(timezone.utc), repair=args.repair)
    except UploadRefused as exc:
        print(f"refused: {exc}")
        return 1
    (spec_dir / "result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result))
    return 1 if result["status"] in ("failed_upload", "failed_qa") or result.get("needs_repair") else 0
