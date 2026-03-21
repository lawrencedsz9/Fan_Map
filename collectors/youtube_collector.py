"""YouTube collector — uses YouTube Data API to fetch latest anime channel videos."""

from __future__ import annotations
import logging
import os
from datetime import datetime, timezone
from typing import Any
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

log = logging.getLogger(__name__)

# Popular anime YouTube channels (by channel ID)
ANIME_CHANNELS = {
    "Crunchyroll": "UCJgkaHz66-MYpnSuWU_5t7A",
    "Anime News Network": "UCJ8YCEOT5oHo63mFuIxvj3A",
    "MyAnimeList": "UCqwxSpD5kgGyjAdL212AIFw",
    "Anitube": "UCprlvclHFx-8W-vLW-Eo7MA",
    "AnimeXin": "UCNNuQ8SYFjqAGqD3dMEqiAA",
    "Tokyo Anime Now": "UC4T0B07lSVcP9k8B9zq5Vew",
    "ANN Studio": "UC-rYnmQdQrXO4a_-QsJmjcg",
}


def collect(topics: list[str], api_key: str = None) -> list[dict[str, Any]]:
    """Collect YouTube videos using YouTube Data API v3
    
    Strategy:
    - Fetch latest videos from major anime channels using official API
    - Collect ALL recent videos (unfiltered) for LLM analysis
    - This enables proper cross-platform validation
    
    Args:
        topics: List of topics to track
        api_key: YouTube API key (defaults to YOUTUBE_API_KEY env var)
    
    Returns:
        List of video signals from anime channels (unfiltered, for LLM analysis)
    """
    signals: list[dict[str, Any]] = []
    
    # Get API key from parameter or environment
    key = api_key or os.getenv("YOUTUBE_API_KEY")
    if not key:
        log.error("YouTube API: YOUTUBE_API_KEY not configured in .env")
        return signals
    
    try:
        youtube = build("youtube", "v3", developerKey=key)
    except Exception as e:
        log.error("YouTube API: Failed to initialize client: %s", e)
        return signals
    
    for channel_name, channel_id in ANIME_CHANNELS.items():
        try:
            log.info("YouTube API: Fetching from %s channel...", channel_name)
            
            # Get latest uploads from this channel
            request = youtube.search().list(
                part="snippet",
                channelId=channel_id,
                order="date",
                maxResults=30,
                type="video",
                relevanceLanguage="en"
            )
            response = request.execute()
            
            for item in response.get("items", []):
                snippet = item.get("snippet", {})
                video_id = item.get("id", {}).get("videoId", "")
                title = snippet.get("title", "")
                published = snippet.get("publishedAt", datetime.now(timezone.utc).isoformat())
                description = snippet.get("description", "")
                
                # Collect ALL videos - let the LLM analyzer determine relevance
                signals.append({
                    "source": "youtube_api",
                    "title": title,
                    "channel": channel_name,
                    "video_id": video_id,
                    "url": f"https://youtube.com/watch?v={video_id}",
                    "description": description,
                    "matched_topics": topics,  # Pass all topics for LLM analysis
                    "published_at": published,
                    "collected_at": datetime.now(timezone.utc).isoformat(),
                })
            
            channel_signals = len([s for s in signals if s['channel'] == channel_name])
            log.info("YouTube API: Collected %d videos from %s", channel_signals, channel_name)
        
        except HttpError as e:
            log.warning("YouTube API: HTTP error fetching %s: %s", channel_name, e)
        except Exception as e:
            log.warning("YouTube API: Failed to fetch %s channel: %s", channel_name, e)
    
    log.info("YouTube API: Total collected %d signals", len(signals))
    return signals
