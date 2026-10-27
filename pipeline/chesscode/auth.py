import argparse
import os
from pathlib import Path

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube"]
TOKEN_PATH = Path("data/secrets/youtube_token.json")


class AuthError(RuntimeError):
    pass


def _credentials_from_env():
    return Credentials(
        token=None,
        refresh_token=os.environ["YOUTUBE_REFRESH_TOKEN"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ["YOUTUBE_CLIENT_ID"],
        client_secret=os.environ["YOUTUBE_CLIENT_SECRET"],
        scopes=SCOPES,
    )


def load_credentials() -> Credentials:
    try:
        if all(os.getenv(key) for key in ("YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN")):
            credentials = _credentials_from_env()
        else:
            credentials = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
        if not credentials.valid:
            credentials.refresh(Request())
        return credentials
    except RefreshError as exc:
        message = str(exc)
        if "invalid_grant" in message:
            raise AuthError('OAuth refresh failed; verify the consent screen is "In production" and run auth login again.') from None
        raise AuthError("OAuth token refresh failed.") from None


def youtube_client():
    return build("youtube", "v3", credentials=load_credentials())


def check() -> dict:
    response = youtube_client().channels().list(part="snippet", mine=True).execute()
    channel = response["items"][0]
    return {"channel_id": channel["id"], "title": channel["snippet"]["title"]}


def main(args: argparse.Namespace) -> int:
    if args.action == "login":
        credentials = InstalledAppFlow.from_client_secrets_file("data/secrets/client_secret.json", SCOPES).run_local_server()
        TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
        TOKEN_PATH.write_text(credentials.to_json(), encoding="utf-8")
        print("YouTube authorization saved.")
        return 0
    try:
        channel = check()
    except AuthError as exc:
        print(exc)
        return 1
    print(f"Authenticated channel: {channel['title']} ({channel['channel_id']})")
    return 0
