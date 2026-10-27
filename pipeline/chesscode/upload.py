import argparse
import socket
import time
from datetime import datetime, timezone
from pathlib import Path

from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

from chesscode import auth


class UploadRefused(Exception):
    pass


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
    existing = find_existing(client, video_id)
    if existing:
        return existing
    publish_utc = publish_at.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    body = {
        "snippet": {
            "title": title,
            "description": with_ccid_footer(description, video_id),
            "tags": tags,
            "categoryId": "20",
            "defaultLanguage": language,
            "defaultAudioLanguage": language,
        },
        "status": {
            "privacyStatus": "private",
            "publishAt": publish_utc,
            "selfDeclaredMadeForKids": False,
        },
    }
    request = client.videos().insert(
        part="snippet,status", body=body, media_body=MediaFileUpload(str(path), resumable=True)
    )
    for attempt in range(5):
        try:
            return request.execute()["id"]
        except (HttpError, socket.error) as exc:
            retryable = isinstance(exc, socket.error) or (exc.resp.status >= 500)
            if not retryable or attempt == 4:
                raise
            time.sleep(2 ** attempt)


def main(args: argparse.Namespace) -> int:
    print("full uploader lands in M7")
    return 2
