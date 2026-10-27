"""youtube_uploader.py — Upload videos to YouTube via Data API v3.

Requires:
    pip install google-api-python-client google-auth-oauthlib

OAuth setup:
    1. Go to Google Cloud Console → APIs & Services → Credentials
    2. Create OAuth 2.0 Client ID (Desktop app)
    3. Download as client_secret.json → place in project root
    4. First run opens browser for auth; token saved to youtube_token.pickle
"""

import os
import pickle
import logging
from dataclasses import dataclass, field
from typing import List, Optional

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/youtube.upload",
          "https://www.googleapis.com/auth/youtube"]
TOKEN_FILE = "youtube_token.pickle"


@dataclass
class VideoMetadata:
    title: str
    description: str = ""
    tags: List[str] = field(default_factory=list)
    privacy: str = "private"
    playlist_id: Optional[str] = None
    category_id: str = "17"  # Sports
    # ISO 8601 datetime (e.g. "2026-07-20T09:00:00+05:30") for a scheduled release.
    # YouTube requires privacyStatus="private" for any video with a future publishAt —
    # set here so callers can't accidentally combine publish_at with a public/unlisted
    # privacy value and have the API silently reject/ignore the schedule.
    publish_at: Optional[str] = None

    @classmethod
    def from_script(cls, script, ga) -> "VideoMetadata":
        tags = list(getattr(script, "tags", []))
        for tag in ["chess", "chess analysis", "chess tutorial"]:
            if tag not in tags:
                tags.append(tag)

        desc = getattr(script, "description", "")
        white = getattr(ga, "white", "")
        black = getattr(ga, "black", "")
        if white and black:
            desc = f"{white} vs {black}\n\n{desc}"

        return cls(title=script.title, description=desc, tags=tags)


class YouTubeUploader:
    def __init__(self):
        self._service = None

    def _get_service(self):
        if self._service:
            return self._service

        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build

        creds = None
        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE, "rb") as f:
                creds = pickle.load(f)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                from google_auth_oauthlib.flow import InstalledAppFlow
                flow = InstalledAppFlow.from_client_secrets_file("client_secret.json", SCOPES)
                creds = flow.run_local_server(port=0)
            with open(TOKEN_FILE, "wb") as f:
                pickle.dump(creds, f)

        self._service = build("youtube", "v3", credentials=creds)
        return self._service

    def upload(self, video_path: str, meta: VideoMetadata) -> str:
        from googleapiclient.http import MediaFileUpload

        service = self._get_service()
        # A scheduled release (status.publishAt) is only honored by the YouTube Data
        # API when privacyStatus is "private" — force it here rather than silently
        # dropping the schedule or letting a public/unlisted upload go live early.
        status = {"privacyStatus": "private" if meta.publish_at else meta.privacy}
        if meta.publish_at:
            status["publishAt"] = meta.publish_at
        body = {
            "snippet": {
                "title": meta.title,
                "description": meta.description,
                "tags": meta.tags,
                "categoryId": meta.category_id,
            },
            "status": status,
        }
        media = MediaFileUpload(video_path, mimetype="video/mp4", resumable=True)
        request = service.videos().insert(part="snippet,status", body=body, media_body=media)

        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                logger.info(f"  Upload {int(status.progress() * 100)}%")

        video_id = response["id"]
        logger.info(f"  Uploaded: https://youtu.be/{video_id}")

        if meta.playlist_id:
            try:
                service.playlistItems().insert(
                    part="snippet",
                    body={"snippet": {
                        "playlistId": meta.playlist_id,
                        "resourceId": {"kind": "youtube#video", "videoId": video_id},
                    }},
                ).execute()
            except Exception as e:
                logger.warning(f"  Playlist add failed: {e}")

        return video_id

    def set_thumbnail(self, video_id: str, thumbnail_path: str) -> None:
        """Upload and set a custom thumbnail for an already-uploaded video."""
        from googleapiclient.http import MediaFileUpload

        service = self._get_service()
        service.thumbnails().set(
            videoId=video_id,
            media_body=MediaFileUpload(thumbnail_path),
        ).execute()
        logger.info(f"  Thumbnail set for {video_id}: {thumbnail_path}")
