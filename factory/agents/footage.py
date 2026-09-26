"""Footage subagent: portrait stock clips from the Pexels video API."""

from pathlib import Path

import requests

from ..config import VIDEO_SIZE

SEARCH_URL = "https://api.pexels.com/videos/search"


def _best_file(video: dict) -> dict | None:
    """The portrait rendition whose width is closest to the output width."""
    portrait = [f for f in video["video_files"] if f["file_type"] == "video/mp4" and f["height"] > f["width"]]
    return min(portrait, key=lambda f: abs(f["width"] - VIDEO_SIZE[0]), default=None)


def fetch(queries: list[str], api_key: str, out_dir: Path) -> list[Path]:
    """Download one clip per query (skipping queries with no portrait result)."""
    session = requests.Session()
    session.headers["Authorization"] = api_key
    paths: list[Path] = []
    for i, query in enumerate(queries):
        response = session.get(
            SEARCH_URL,
            params={"query": query, "orientation": "portrait", "per_page": 5},
            timeout=30,
        )
        response.raise_for_status()
        file = next(filter(None, map(_best_file, response.json()["videos"])), None)
        if file is None:
            continue
        path = out_dir / f"clip_{i:02d}.mp4"
        with session.get(file["link"], stream=True, timeout=120) as download:
            download.raise_for_status()
            with path.open("wb") as f:
                for chunk in download.iter_content(chunk_size=1 << 20):
                    f.write(chunk)
        paths.append(path)
    return paths
