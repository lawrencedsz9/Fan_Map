from typing import TypedDict, List, Dict, Any
from langgraph.graph import StateGraph, END
import logging
from tenacity import retry, stop_after_attempt, wait_exponential
from db.mongo_storage import save_signals

log = logging.getLogger(__name__)

class IntelligenceState(TypedDict):
    """The memory of our intelligence agent."""
    raw_signals: List[Dict[str, Any]]
    enriched_signals: List[Dict[str, Any]]
    is_exploding: bool
    reddit_signals: List[Dict[str, Any]]
    youtube_signals: List[Dict[str, Any]]
    trends_signals: List[Dict[str, Any]]

# --- Retry Decorator (handles transient failures) ---
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True
)
def _reddit_collect() -> List[Dict[str, Any]]:
    """Collect Reddit signals with automatic retry."""
    from collectors.reddit_collector import collect as reddit_collect
    from config import TRACKED_TOPICS, SUBREDDITS
    log.info("Scout: Collecting Reddit signals...")
    return reddit_collect(TRACKED_TOPICS, SUBREDDITS)

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True
)
def _youtube_collect() -> List[Dict[str, Any]]:
    """Collect YouTube signals with automatic retry."""
    from collectors.youtube_collector import collect as yt_collect
    from config import TRACKED_TOPICS, YOUTUBE_API_KEY
    if not YOUTUBE_API_KEY:
        log.warning("YouTube API key not configured, skipping")
        return []
    log.info("Scout: Collecting YouTube signals...")
    return yt_collect(TRACKED_TOPICS, YOUTUBE_API_KEY)

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True
)
def _trends_collect() -> List[Dict[str, Any]]:
    """Collect Google Trends signals with automatic retry."""
    from collectors.trends_collector import collect as trends_collect
    from config import TRACKED_TOPICS
    log.info("Scout: Collecting Google Trends signals...")
    return trends_collect(TRACKED_TOPICS)

# --- Parallel Scout Nodes ---

def reddit_scout_node(state: IntelligenceState) -> IntelligenceState:
    """Reddit Scout: Fetches signals from Reddit RSS feeds."""
    print("Reddit Scout: Scavenging Reddit...")
    try:
        signals = _reddit_collect()
        log.info(f"Reddit Scout: Collected {len(signals)} signals")
        return {"reddit_signals": signals}
    except Exception as e:
        log.warning(f"Reddit Scout failed after retries: {e}")
        return {"reddit_signals": []}

def youtube_scout_node(state: IntelligenceState) -> IntelligenceState:
    """YouTube Scout: Fetches signals from YouTube."""
    print("YouTube Scout: Scavenging YouTube...")
    try:
        signals = _youtube_collect()
        log.info(f"YouTube Scout: Collected {len(signals)} signals")
        return {"youtube_signals": signals}
    except Exception as e:
        log.warning(f"YouTube Scout failed after retries: {e}")
        return {"youtube_signals": []}

def trends_scout_node(state: IntelligenceState) -> IntelligenceState:
    """Trends Scout: Fetches signals from Google Trends."""
    print("Trends Scout: Scavenging Google Trends...")
    try:
        signals = _trends_collect()
        log.info(f"Trends Scout: Collected {len(signals)} signals")
        return {"trends_signals": signals}
    except Exception as e:
        log.warning(f"Trends Scout failed after retries: {e}")
        return {"trends_signals": []}

def merger_node(state: IntelligenceState) -> IntelligenceState:
    """Merge signals from all scouts into a unified raw_signals list."""
    print("Merger: Combining scout reports...")
    reddit = state.get("reddit_signals", [])
    youtube = state.get("youtube_signals", [])
    trends = state.get("trends_signals", [])
    
    merged = reddit + youtube + trends
    log.info(f"Merger: Combined {len(merged)} total signals (Reddit: {len(reddit)}, YouTube: {len(youtube)}, Trends: {len(trends)})")
    
    # Save merged signals to MongoDB
    if merged:
        try:
            save_signals(merged)
            log.info(f"Merger: Saved {len(merged)} signals to MongoDB")
        except Exception as e:
            log.warning(f"Merger: Failed to save signals: {e}")
    
    return {"raw_signals": merged}

def analyzer_node(state: IntelligenceState) -> IntelligenceState:
    """The Analyst: Crushes raw ore into refined insights."""
    print("Analyzer: Calculating hype levels...")
    from processing.topic_extraction import enrich_all
    
    raw = state.get("raw_signals", [])
    if not raw:
        log.warning("Analyzer: No signals to analyze")
        return {"enriched_signals": [], "is_exploding": False}
    
    # Use existing NLP logic
    enriched = enrich_all(raw)
    log.info(f"Analyzer: Enriched {len(enriched)} signals with topic extraction")
    
    # Simple logic: If any topic has > 5 mentions, it's "Exploding"
    counts = {}
    for s in enriched:
        for t in s.get("matched_topics", []):
            counts[t] = counts.get(t, 0) + 1
    
    is_exploding = any(c > 5 for c in counts.values())
    if is_exploding:
        exploding_topics = [t for t, c in counts.items() if c > 5]
        log.info(f"Analyzer: Explosion detected! Topics: {exploding_topics}")
    
    return {"enriched_signals": enriched, "is_exploding": is_exploding}

# --- Build the Graph ---
workflow = StateGraph(IntelligenceState)

# Add all nodes
workflow.add_node("reddit_scout", reddit_scout_node)
workflow.add_node("youtube_scout", youtube_scout_node)
workflow.add_node("trends_scout", trends_scout_node)
workflow.add_node("merger", merger_node)
workflow.add_node("analyzer", analyzer_node)

# Entry point: Start all scouts in parallel
workflow.set_entry_point("reddit_scout")
workflow.add_edge("reddit_scout", "youtube_scout")
workflow.add_edge("youtube_scout", "trends_scout")
workflow.add_edge("trends_scout", "merger")
workflow.add_edge("merger", "analyzer")
workflow.add_edge("analyzer", END)

# Compile
app = workflow.compile()