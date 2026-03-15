from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from pymongo import MongoClient, ASCENDING
from pymongo.collection import Collection

try:
    import certifi
except ImportError:
    certifi = None  # type: ignore[assignment]

_client: Optional[MongoClient] = None


def _get_client() -> MongoClient:
    global _client
    if _client is None:
        uri = os.getenv("MONGODB_URI")
        if not uri:
            raise RuntimeError("MONGODB_URI is not set")
        
        uri = uri.strip()
        
        kwargs: dict = {
            "serverSelectionTimeoutMS": 15_000,
            "connectTimeoutMS": 10_000,
        }
        
        # On Render, disable SSL certificate validation
        if "RENDER" in os.environ:
            kwargs["tlsInsecure"] = True
            kwargs["retryWrites"] = False
        elif certifi is not None:
            kwargs["tlsCAFile"] = certifi.where()
        
        _client = MongoClient(uri, **kwargs)
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
    try:
        col = _signals_col()
        # Insert copies to avoid mutating original dicts with ObjectId
        col.insert_many([s.copy() for s in signals])
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("MongoDB save_signals failed (non-critical): %s", str(e))


def load_signals(limit: int = 1000) -> List[Dict[str, Any]]:
    """Load recent signals."""
    try:
        col = _signals_col()
        cursor = col.find().sort("created_at", -1).limit(limit)
        return list(cursor)
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("MongoDB load_signals failed (non-critical): %s", str(e))
        return []


def append_history_snapshot(topic_counts: Dict[str, Dict[str, int]], timestamp: str) -> None:
    """Append a snapshot per topic."""
    if not topic_counts:
        return
    try:
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
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("MongoDB append_history_snapshot failed (non-critical): %s", str(e))


def load_history() -> Dict[str, List[Dict[str, Any]]]:
    """Return history grouped by topic to match existing structure."""
    try:
        col = _history_col()
        history: Dict[str, List[Dict[str, Any]]] = {}
        for doc in col.find().sort([("topic", ASCENDING), ("timestamp", ASCENDING)]):
            topic = doc.pop("topic")
            doc.pop("_id", None)
            history.setdefault(topic, []).append(doc)
        return history
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("MongoDB load_history failed (non-critical): %s", str(e))
        return {}


def save_trend_report(report: Dict[str, Any]) -> None:
    """Persist the latest trend report."""
    try:
        col = _reports_col()
        col.insert_one(report.copy())
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("MongoDB save_trend_report failed (non-critical): %s", str(e))


def load_latest_trend_report() -> Optional[Dict[str, Any]]:
    """Load the most recent trend report, if any."""
    try:
        col = _reports_col()
        doc = col.find_one(sort=[("timestamp", -1)])
        if not doc:
            return None
        doc.pop("_id", None)
        return doc
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("MongoDB load_latest_trend_report failed (non-critical): %s", str(e))
        return None

