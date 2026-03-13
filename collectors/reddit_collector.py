"""Reddit collector — pulls recent posts via public RSS .

Uses reddit.com/r/<subreddit>/new/.rss — live, keyless, returns the 25 most
recent posts per subreddit without any OAuth or account approval.
"""

from __future__ import annotations
import logging
from datetime import datetime, timezone
from typing import Any

log = logging.getLogger(__name__)

_RSS_TEMPLATE = "https://www.reddit.com/r/{subreddit}/new/.rss"
_HEADERS = {"User-Agent": "fandom-intelligence-bot/1.0 (RSS reader)"}


def collect(topics: list[str], subreddits: list[str], **_kwargs: Any) -> list[dict[str, Any]]:
    """Collect the 25 most recent Reddit posts per subreddit via RSS.

    The **_kwargs absorbs legacy praw credential arguments so existing call
    sites do not need to change.
    """
    import feedparser

    signals: list[dict[str, Any]] = []

    for sub_name in subreddits:
        url = _RSS_TEMPLATE.format(subreddit=sub_name)
        try:
            feed = feedparser.parse(url, request_headers=_HEADERS)

            # bozo=True just means the feed had minor XML issues, entries may still be valid
            if not feed.entries:
                log.warning("No RSS entries for r/%s (bozo=%s)", sub_name, feed.get("bozo"))
                continue

            for entry in feed.entries:
                title: str = entry.get("title", "")
                matched = [t for t in topics if t.lower() in title.lower()]
                if matched:
                    signals.append({
                        "source": "reddit",
                        "subreddit": sub_name,
                        "title": title,
                        "url": entry.get("link", ""),
                        "matched_topics": matched,
                        "published_at": entry.get("published", ""),
                        "collected_at": datetime.now(timezone.utc).isoformat(),
                    })
        except Exception:
            log.warning("Failed to fetch RSS for r/%s", sub_name, exc_info=True)

    log.info("Reddit RSS: collected %d signals", len(signals))
    return signals
