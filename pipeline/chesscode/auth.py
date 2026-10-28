import argparse
import os
from pathlib import Path

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube"]
REPO_ROOT = Path(__file__).resolve().parents[2]
SECRETS_DIR = REPO_ROOT / "data" / "secrets"
TOKEN_PATH = SECRETS_DIR / "youtube_token.json"


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
    try:
        response = youtube_client().channels().list(part="snippet", mine=True).execute()
        channel = response["items"][0]
        return {"channel_id": channel["id"], "title": channel["snippet"]["title"]}
    except AuthError:
        raise
    except (FileNotFoundError, KeyError, IndexError, HttpError) as exc:
        raise AuthError("YouTube authentication check failed; run auth login and try again.") from exc


def main(args: argparse.Namespace) -> int:
    if args.action == "login":
        client_secret = SECRETS_DIR / "client_secret.json"
        try:
            credentials = InstalledAppFlow.from_client_secrets_file(str(client_secret), SCOPES).run_local_server()
        except FileNotFoundError:
            print(f"OAuth client file not found: {client_secret}")
            return 1
        TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
        TOKEN_PATH.write_text(credentials.to_json(), encoding="utf-8")
        TOKEN_PATH.chmod(0o600)
        print("YouTube authorization saved.")
        return 0
    try:
        channel = check()
    except AuthError as exc:
        print(exc)
        return 1
    print(f"Authenticated channel: {channel['title']} ({channel['channel_id']})")
    return 0
