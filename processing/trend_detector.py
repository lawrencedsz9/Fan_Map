"""
Trend GrowthDetector

Detects topics that are experiencing sudden spikes in attention.
Uses a rolling baseline to identify anomalies — topics getting way more
attention than usual are flagged as "exploding."

This is the core intelligence layer of the system.
"""

from __future__ import annotations
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from collections import defaultdict

from config import DATA_DIR, EXPLOSION_THRESHOLD

log = logging.getLogger(__name__)

HISTORY_FILE = DATA_DIR / "attention_history.json"


def _load_history() -> dict[str, list[dict[str, Any]]]:
    """Load historical attention snapshots."""
    if HISTORY_FILE.exists():
        return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    return {}


def _save_history(history: dict[str, list[dict[str, Any]]]) -> None:
    """Persist attention history to disk."""
    DATA_DIR.mkdir(exist_ok=True)
    HISTORY_FILE.write_text(json.dumps(history, indent=2), encoding="utf-8")


def record_snapshot(signals: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    """Record current attention levels and return current counts per topic."""
    now = datetime.now(timezone.utc).isoformat()
    topic_counts: dict[str, dict[str, int]] = defaultdict(lambda: {
        "reddit": 0, "youtube": 0, "google_trends": 0, "total": 0,
    })

    for signal in signals:
        source = signal.get("source", "unknown")
        for topic in signal.get("matched_topics", []):
            if source in topic_counts[topic]:
                topic_counts[topic][source] += 1
            topic_counts[topic]["total"] += 1

    # Save to history
    history = _load_history()
    for topic, counts in topic_counts.items():
        if topic not in history:
            history[topic] = []
        history[topic].append({
            "timestamp": now,
            **counts,
        })
        # Keep last 100 snapshots per topic
        history[topic] = history[topic][-100:]

    _save_history(history)
    log.info("Recorded attention snapshot for %d topics", len(topic_counts))
    return dict(topic_counts)


def detect_explosions(current_counts: dict[str, dict[str, int]]) -> list[dict[str, Any]]:
    """
    Compare current attention to historical baseline.
    Flag topics where current >> baseline as "exploding."
    """
    history = _load_history()
    explosions: list[dict[str, Any]] = []

    for topic, current in current_counts.items():
        past_snapshots = history.get(topic, [])

        # Need at least 2 historical snapshots for a baseline
        if len(past_snapshots) < 2:
            continue

        # Compute baseline (average of all past snapshots except latest)
        past_totals = [s.get("total", 0) for s in past_snapshots[:-1]]
        baseline = sum(past_totals) / len(past_totals) if past_totals else 1
        baseline = max(baseline, 1)  # avoid division by zero

        current_total = current.get("total", 0)
        ratio = current_total / baseline

        if ratio >= EXPLOSION_THRESHOLD:
            explosion = {
                "topic": topic,
                "current_mentions": current_total,
                "baseline_average": round(baseline, 1),
                "explosion_ratio": round(ratio, 2),
                "verdict": _classify_explosion(ratio),
                "details": {
                    "reddit": current.get("reddit", 0),
                    "youtube": current.get("youtube", 0),
                    "google_trends": current.get("google_trends", 0),
                },
                "detected_at": datetime.now(timezone.utc).isoformat(),
            }
            explosions.append(explosion)
            log.warning(
                "EXPLOSION DETECTED: %s (%.1fx baseline)", topic, ratio
            )

    # Sort by explosion ratio
    explosions.sort(key=lambda x: x["explosion_ratio"], reverse=True)
    return explosions


def _classify_explosion(ratio: float) -> str:
    """Classify the severity of a trend explosion."""
    if ratio >= 10:
        return "MEGA EXPLOSION"
    elif ratio >= 5:
        return "VIRAL"
    elif ratio >= 3:
        return "EXPLODING"
    else:
        return "RISING FAST"


def get_trend_report(signals: list[dict[str, Any]]) -> dict[str, Any]:
    """Full trend analysis: record snapshot + detect explosions."""
    current = record_snapshot(signals)
    explosions = detect_explosions(current)

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "topics_tracked": len(current),
        "explosions_detected": len(explosions),
        "explosions": explosions,
        "current_attention": {
            topic: counts for topic, counts in
            sorted(current.items(), key=lambda x: x[1]["total"], reverse=True)
        },
    }

    # Save report
    report_path = DATA_DIR / "latest_trend_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    log.info("Trend report: %d explosions detected", len(explosions))

    return report
