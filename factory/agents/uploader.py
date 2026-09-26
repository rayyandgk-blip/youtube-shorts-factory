"""Uploader subagent: publishes the rendered Short through the YouTube Data API v3."""

from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from ..config import CLIENT_SECRETS, DATA_DIR, YOUTUBE_TOKEN
from .script_writer import Script

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
CATEGORY_EDUCATION = "27"


def authorize() -> None:
    """One-time interactive OAuth consent; stores a refreshable token for unattended runs."""
    if not CLIENT_SECRETS.exists():
        raise SystemExit(f"missing {CLIENT_SECRETS}: download a Desktop-app OAuth client from Google Cloud Console")
    flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRETS), SCOPES)
    creds = flow.run_local_server(port=0)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    YOUTUBE_TOKEN.write_text(creds.to_json())


def _credentials() -> Credentials:
    if not YOUTUBE_TOKEN.exists():
        raise RuntimeError(f"no YouTube token at {YOUTUBE_TOKEN}; run `python main.py auth` first")
    creds = Credentials.from_authorized_user_file(str(YOUTUBE_TOKEN), SCOPES)
    if not creds.valid:
        creds.refresh(Request())
        YOUTUBE_TOKEN.write_text(creds.to_json())
    return creds


def upload(video_path: Path, script: Script, privacy: str) -> str:
    """Upload the video and return its YouTube video ID."""
    youtube = build("youtube", "v3", credentials=_credentials())
    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": script.title,
                "description": script.description,
                "tags": script.tags,
                "categoryId": CATEGORY_EDUCATION,
            },
            "status": {"privacyStatus": privacy, "selfDeclaredMadeForKids": False},
        },
        media_body=MediaFileUpload(str(video_path), mimetype="video/mp4", chunksize=-1, resumable=True),
    )
    response = None
    while response is None:
        _, response = request.next_chunk()
    return response["id"]
