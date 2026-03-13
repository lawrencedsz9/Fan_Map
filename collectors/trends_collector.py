"""Google Trends collector — fetches interest-over-time for tracked topics."""

from __future__ import annotations
import logging
from datetime import datetime, timezone
from typing import Any

log = logging.getLogger(__name__)


def collect(topics: list[str]) -> list[dict[str, Any]]:
    """Pull Google Trends interest scores for the tracked topics."""
    from pytrends.request import TrendReq

    pytrends = TrendReq(hl="en-US", tz=360)
    signals: list[dict[str, Any]] = []

    # Google Trends allows max 5 topics per request
    for i in range(0, len(topics), 5):
        batch = topics[i : i + 5]
        try:
            pytrends.build_payload(batch, timeframe="now 7-d")
            df = pytrends.interest_over_time()

            if df.empty:
                continue

            for topic in batch:
                if topic in df.columns:
                    latest = int(df[topic].iloc[-1])
                    avg = float(df[topic].mean())
                    signals.append({
                        "source": "google_trends",
                        "topic": topic,
                        "latest_score": latest,
                        "average_7d": round(avg, 2),
                        "matched_topics": [topic],
                        "collected_at": datetime.now(timezone.utc).isoformat(),
                    })
        except Exception:
            log.warning("Google Trends failed for batch %s", batch, exc_info=True)

    log.info("Google Trends: collected %d signals", len(signals))
    return signals
