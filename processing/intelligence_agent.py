from typing import TypedDict, List, Dict, Any, Literal
from langgraph.graph import StateGraph, END
import logging
import os
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
    should_analyze: bool  # Router decision flag
    llm_judgment: Dict[str, Any]  # LLM verdict on explosions

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
    else:
        log.warning("Merger: No signals collected from any source")
    
    return {"raw_signals": merged}

def router_node(state: IntelligenceState) -> IntelligenceState:
    """Router: Decides whether to proceed with deep analysis.
    
    Logic:
    - If raw_signals is empty → skip analysis (save costs)
    - If raw_signals exists → proceed to deep analysis
    """
    print("Router: Deciding workflow path...")
    raw = state.get("raw_signals", [])
    
    if not raw or len(raw) == 0:
        log.info("Router: No signals detected. Skipping analysis to save costs.")
        print("  No activity detected. Analysis skipped.")
        return {"should_analyze": False, "enriched_signals": [], "is_exploding": False}
    else:
        log.info(f"Router: Activity detected ({len(raw)} signals). Routing to analyzer...")
        print(f"  {len(raw)} signals found. Proceeding to analysis.")
        return {"should_analyze": True}

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
        print(f"  Explosion detected: {exploding_topics}")
    else:
        log.info("Analyzer: No trend explosions detected")
        print("  No explosions detected.")
    
    return {"enriched_signals": enriched, "is_exploding": is_exploding}

def conditional_analyzer_router(state: IntelligenceState) -> Literal["analyzer", "end"]:
    """Conditional edge: Route to analyzer or end based on signal availability."""
    should_analyze = state.get("should_analyze", False)
    if should_analyze:
        return "analyzer"
    else:
        return "end"

def llm_judgment_node(state: IntelligenceState) -> IntelligenceState:
    """LLM Judgment: Use Gemini to evaluate if explosions are real or noise.
    
    This node takes potential trend explosions detected by the Analyzer
    and asks Claude to reason about them:
    - Is this real hype, or bot spam?
    - Are the signals authentic?
    """
    print("🧠 LLM Judgment: Evaluating trends with AI reasoning...")
    
    is_exploding = state.get("is_exploding", False)
    enriched = state.get("enriched_signals", [])
    
    # If no explosions detected by simple logic, skip LLM
    if not is_exploding:
        log.info("LLM Judgment: No explosions to evaluate. Skipping.")
        return {"llm_judgment": {"verdict": "no_explosions", "confidence": 1.0, "reasoning": "No trends exceeded threshold"}}
    
    # Extract explosion data
    counts = {}
    for s in enriched:
        for t in s.get("matched_topics", []):
            counts[t] = counts.get(t, 0) + 1
    
    exploding_topics = {t: c for t, c in counts.items() if c > 5}
    
    # Sample some snippets for context
    sample_snippets = []
    for signal in enriched[:5]:  # Sample first 5 signals
        snippet = signal.get("content", "")[:100]
        source = signal.get("source", "unknown")
        sample_snippets.append(f"[{source}] {snippet}")
    
    # Build the prompt
    prompt = f"""You are an AI analyst evaluating internet trends. Analyze the following trend explosion and determine if it's real hype or noise.

**Detected Explosion:**
Topics: {list(exploding_topics.keys())}
Mention Counts: {exploding_topics}

**Sample Signals:**
{chr(10).join(sample_snippets)}

**Your Task:**
1. Is this trend explosion REAL (authentic hype from genuine interest)?
2. What's your confidence level (0.0-1.0)?
3. Why? (brief reasoning)

Respond in JSON format:
{{"is_real": true/false, "confidence": 0.0-1.0, "reasoning": "brief explanation"}}"""
    
    try:
        import google.generativeai as genai
        
        # Load API key from environment
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        if not gemini_api_key:
            log.warning("LLM Judgment: GEMINI_API_KEY not found in environment")
            return {"llm_judgment": {"verdict": "skipped", "reason": "No API key"}}
        
        genai.configure(api_key=gemini_api_key)
        model = genai.GenerativeModel("gemini-2.0-flash")
        
        response = model.generate_content(prompt)
        response_text = response.text
        
        # Parse JSON response
        import json
        import re
        
        # Extract JSON from response
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            verdict = json.loads(json_match.group())
        else:
            verdict = {"is_real": False, "confidence": 0.5, "reasoning": "Could not parse LLM response"}
        
        log.info(f"LLM Judgment: {verdict}")
        print(f"  Verdict: {'✅ REAL HYPE' if verdict.get('is_real') else '❌ LIKELY NOISE'}")
        print(f"  Confidence: {verdict.get('confidence', 0):.2f}")
        print(f"  Reason: {verdict.get('reasoning', 'N/A')}")
        
        return {"llm_judgment": verdict}
    
    except Exception as e:
        log.warning(f"LLM Judgment failed: {e}")
        return {"llm_judgment": {"verdict": "error", "reason": str(e)}}

def conditional_llm_router(state: IntelligenceState) -> Literal["llm_judgment", "end"]:
    """Conditional edge: Route to LLM judgment if explosions detected, else end."""
    is_exploding = state.get("is_exploding", False)
    if is_exploding:
        return "llm_judgment"
    else:
        return "end"

# --- Build the Graph ---
workflow = StateGraph(IntelligenceState)

# Add all nodes
workflow.add_node("reddit_scout", reddit_scout_node)
workflow.add_node("youtube_scout", youtube_scout_node)
workflow.add_node("trends_scout", trends_scout_node)
workflow.add_node("merger", merger_node)
workflow.add_node("router", router_node)
workflow.add_node("analyzer", analyzer_node)
workflow.add_node("llm_judgment", llm_judgment_node)

# Entry point: Start all scouts in parallel
workflow.set_entry_point("reddit_scout")
workflow.add_edge("reddit_scout", "youtube_scout")
workflow.add_edge("youtube_scout", "trends_scout")
workflow.add_edge("trends_scout", "merger")
workflow.add_edge("merger", "router")

# STEP 3: Conditional Routing
# Router decides: Analyze or End?
workflow.add_conditional_edges(
    "router",
    conditional_analyzer_router,
    {"analyzer": "analyzer", "end": END}
)

# STEP 4: LLM Judgment
# After analysis, if explosions detected → send to LLM for verification
workflow.add_conditional_edges(
    "analyzer",
    conditional_llm_router,
    {"llm_judgment": "llm_judgment", "end": END}
)
workflow.add_edge("llm_judgment", END)

# Compile
app = workflow.compile()