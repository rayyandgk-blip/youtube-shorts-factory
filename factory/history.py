"""Append-only log of published Shorts, used to keep topics fresh."""

import json
from datetime import datetime, timezone

from .config import DATA_DIR

HISTORY_FILE = DATA_DIR / "history.jsonl"


def recent_titles(limit: int = 50) -> list[str]:
    if not HISTORY_FILE.exists():
        return []
    lines = HISTORY_FILE.read_text().splitlines()[-limit:]
    return [json.loads(line)["title"] for line in lines]


def record(title: str, video_id: str) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    entry = {
        "published_at": datetime.now(timezone.utc).isoformat(),
        "title": title,
        "video_id": video_id,
    }
    with HISTORY_FILE.open("a") as f:
        f.write(json.dumps(entry) + "\n")
