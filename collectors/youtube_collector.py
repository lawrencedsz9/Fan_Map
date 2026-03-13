"""YouTube collector — searches for recent videos mentioning tracked topics."""

from __future__ import annotations
import logging
from datetime import datetime, timezone
from typing import Any

log = logging.getLogger(__name__)


def collect(topics: list[str], api_key: str) -> list[dict[str, Any]]:
    """Search YouTube for videos related to tracked topics."""
    from googleapiclient.discovery import build

    youtube = build("youtube", "v3", developerKey=api_key)
    signals: list[dict[str, Any]] = []

    for topic in topics:
        try:
            request = youtube.search().list(
                q=topic,
                part="snippet",
                type="video",
                order="date",
                maxResults=10,
            )
            response = request.execute()

            for item in response.get("items", []):
                snippet = item["snippet"]
                signals.append({
                    "source": "youtube",
                    "title": snippet["title"],
                    "channel": snippet["channelTitle"],
                    "video_id": item["id"]["videoId"],
                    "url": f"https://youtube.com/watch?v={item['id']['videoId']}",
                    "matched_topics": [topic],
                    "published_at": snippet["publishedAt"],
                    "collected_at": datetime.now(timezone.utc).isoformat(),
                })
        except Exception:
            log.warning("YouTube search failed for '%s'", topic, exc_info=True)

    log.info("YouTube: collected %d signals", len(signals))
    return signals
