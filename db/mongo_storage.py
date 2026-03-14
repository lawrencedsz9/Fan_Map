from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from pymongo import MongoClient, ASCENDING
from pymongo.collection import Collection


_client: Optional[MongoClient] = None


def _get_client() -> MongoClient:
    global _client
    if _client is None:
        uri = os.getenv("MONGODB_URI")
        if not uri:
            raise RuntimeError("MONGODB_URI is not set")
        _client = MongoClient(uri)
    return _client


def _get_db():
    client = _get_client()
    name = os.getenv("MONGODB_DB_NAME", "fandom_intel")
    return client[name]


def _signals_col() -> Collection:
    db = _get_db()
    col = db["signals"]
    col.create_index([("created_at", ASCENDING)])
    return col


def _history_col() -> Collection:
    db = _get_db()
    col = db["attention_history"]
    col.create_index([("topic", ASCENDING), ("timestamp", ASCENDING)])
    return col


def _reports_col() -> Collection:
    db = _get_db()
    col = db["trend_reports"]
    col.create_index([("timestamp", ASCENDING)])
    return col


def save_signals(signals: List[Dict[str, Any]]) -> None:
    """Store the latest batch of enriched signals."""
    if not signals:
        return
    col = _signals_col()
    col.insert_many(signals)


def load_signals(limit: int = 1000) -> List[Dict[str, Any]]:
    """Load recent signals."""
    col = _signals_col()
    cursor = col.find().sort("created_at", -1).limit(limit)
    return list(cursor)


def append_history_snapshot(topic_counts: Dict[str, Dict[str, int]], timestamp: str) -> None:
    """Append a snapshot per topic."""
    if not topic_counts:
        return
    col = _history_col()
    docs = []
    for topic, counts in topic_counts.items():
        docs.append(
            {
                "topic": topic,
                "timestamp": timestamp,
                **counts,
            }
        )
    if docs:
        col.insert_many(docs)


def load_history() -> Dict[str, List[Dict[str, Any]]]:
    """Return history grouped by topic to match existing structure."""
    col = _history_col()
    history: Dict[str, List[Dict[str, Any]]] = {}
    for doc in col.find().sort([("topic", ASCENDING), ("timestamp", ASCENDING)]):
        topic = doc.pop("topic")
        doc.pop("_id", None)
        history.setdefault(topic, []).append(doc)
    return history


def save_trend_report(report: Dict[str, Any]) -> None:
    """Persist the latest trend report."""
    col = _reports_col()
    col.insert_one(report)


def load_latest_trend_report() -> Optional[Dict[str, Any]]:
    """Load the most recent trend report, if any."""
    col = _reports_col()
    doc = col.find_one(sort=[("timestamp", -1)])
    if not doc:
        return None
    doc.pop("_id", None)
    return doc

