"""Runtime settings, read once from the environment."""

import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "output"

MODEL = "claude-opus-5"
# Server-side refusal fallback: the API routes a declined request to a suitable model.
FALLBACK_BETA = "server-side-fallback-2026-07-01"

WHISPER_MODEL = "base"
VIDEO_SIZE = (1080, 1920)
MAX_SHORT_SECONDS = 58


@dataclass(frozen=True)
class Settings:
    niche: str
    post_time: str
    privacy: str
    voice: str
    pexels_api_key: str
    client_secrets: Path
    token_path: Path

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            niche=os.environ.get("SHORTS_NICHE", "surprising science facts"),
            post_time=os.environ.get("SHORTS_POST_TIME", "15:00"),
            privacy=os.environ.get("YOUTUBE_PRIVACY", "private"),
            voice=os.environ.get("TTS_VOICE", "en-US-GuyNeural"),
            pexels_api_key=os.environ["PEXELS_API_KEY"],
            client_secrets=DATA_DIR / "client_secrets.json",
            token_path=DATA_DIR / "youtube_token.json",
        )
