"""Collector package — aggregates signals from all sources."""

from __future__ import annotations
import logging
from typing import Any

from config import TRACKED_TOPICS, SUBREDDITS, YOUTUBE_API_KEY

log = logging.getLogger(__name__)


def collect_all() -> list[dict[str, Any]]:
    """Run every collector and return a unified list of attention signals."""
    signals: list[dict[str, Any]] = []

    # Reddit — RSS Feed (no API key needed)
    try:
        from collectors.reddit_collector import collect as reddit_collect
        signals.extend(reddit_collect(TRACKED_TOPICS, SUBREDDITS))
    except Exception:
        log.warning("Reddit RSS collection failed", exc_info=True)

    # YouTube
    if YOUTUBE_API_KEY:
        from collectors.youtube_collector import collect as yt_collect
        signals.extend(yt_collect(TRACKED_TOPICS, YOUTUBE_API_KEY))

    # Google Trends (no API key needed)
    try:
        from collectors.trends_collector import collect as trends_collect
        signals.extend(trends_collect(TRACKED_TOPICS))
    except Exception:
        log.warning("Google Trends collection failed", exc_info=True)

    log.info("Total signals collected: %d", len(signals))
    return signals
