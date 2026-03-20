"""YouTube collector — uses RSS feeds to bypass API quota limits."""

from __future__ import annotations
import logging
from datetime import datetime, timezone
from typing import Any
import feedparser

log = logging.getLogger(__name__)

# Popular anime YouTube channels (RSS-based, no API quota needed)
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
    """Collect YouTube videos using RSS feeds
    
    Strategy:
    - Collect ALL recent videos from anime channels 
    - Let the LLM analyzer determine semantic relevance
    - This enables cross-platform validation 
    
    Args:
        topics: List of topics to track 
       
    
    Returns:
        List of video signals from anime channels (unfiltered, for LLM analysis)
    """
    signals: list[dict[str, Any]] = []
    
    for channel_name, channel_id in ANIME_CHANNELS.items():
        try:
            rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
            feed = feedparser.parse(rss_url)
            
            log.info("YouTube RSS: Fetching from %s channel...", channel_name)
            
            for entry in feed.entries[:30]:  # Get last 30 videos per channel (no topic filter)
                title = entry.get("title", "")
                video_id = entry.get("yt_videoid", "")
                published = entry.get("published", datetime.now(timezone.utc).isoformat())
                
                # Collect ALL videos - let the LLM analyzer determine relevance
                # This enables cross-platform validation instead of pre-filtering
                signals.append({
                    "source": "youtube_rss",
                    "title": title,
                    "channel": channel_name,
                    "video_id": video_id,
                    "url": f"https://youtube.com/watch?v={video_id}",
                    "matched_topics": topics,  # Pass all topics for LLM analysis
                    "published_at": published,
                    "collected_at": datetime.now(timezone.utc).isoformat(),
                })
            
            channel_signals = len([s for s in signals if s['channel'] == channel_name])
            log.info("YouTube RSS: Collected %d videos from %s (raw, for LLM analysis)", channel_signals, channel_name)
        
        except Exception as e:
            log.warning("YouTube RSS: Failed to fetch %s channel: %s", channel_name, e)
    
    log.info("YouTube RSS: Total collected %d signals (unfiltered for semantic analysis)", len(signals))
    return signals
