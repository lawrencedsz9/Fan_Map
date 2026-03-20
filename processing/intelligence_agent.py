from typing import TypedDict, List, Dict, Any, Literal
from langgraph.graph import StateGraph, END
import logging
import os
from datetime import datetime, timedelta
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
    approval_id: str  # For pending trends
    approval_status: str  # "approved", "pending", "rejected"

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
    """LLM Judgment: Use AI Modelto evaluate if explosions are real or noise.
    
    This node takes potential trend explosions detected by the Analyzer
    and asks the agent to reason about them:
    - Is this real hype, or bot spam?
    - Are the signals authentic?
    
    FALLBACK: If LLM error occurs, uses analyzer result as fallback.
    """
    print("Evaluating trends with AI reasoning...")
    
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

Respond in JSON format only (no other text):
{{"is_real": true/false, "confidence": 0.0-1.0, "reasoning": "brief explanation"}}"""
    
    try:
        from groq import Groq
        import json
        import re
        
        # Load API key from environment
        groq_api_key = os.getenv("Groq")
        if not groq_api_key:
            log.warning("LLM Judgment: Groq API key not found in environment")
            # Fallback to analyzer result
            return {"llm_judgment": {"is_real": True, "confidence": 0.70, "reasoning": "No API key. Using analyzer result."}}
        
        client = Groq(api_key=groq_api_key)
        
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0.7
        )
        response_text = response.choices[0].message.content
        
        # Extract JSON from response
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            verdict = json.loads(json_match.group())
        else:
            verdict = {"is_real": False, "confidence": 0.5, "reasoning": "Could not parse LLM response"}
        
        log.info(f"LLM Judgment: {verdict}")
        print(f"  Verdict: {'REAL HYPE' if verdict.get('is_real') else 'LIKELY NOISE'}")
        print(f"  Confidence: {verdict.get('confidence', 0):.2f}")
        print(f"  Reason: {verdict.get('reasoning', 'N/A')}")
        
        return {"llm_judgment": verdict}
    
    except Exception as e:
        error_msg = str(e)
        log.warning(f"LLM Judgment failed: {e}")
        
        # Fallback to pending approval on any error
        log.info(f"LLM Judgment: Error encountered, using fallback logic based on analyzer result")
        print(f"  LLM error. Using analyzer result as fallback.")
        
        fallback_verdict = {
            "is_real": True,  # Assume it's real (let human decide)
            "confidence": 0.70,  # Medium confidence triggers pending_approval
            "reasoning": f"LLM error ({error_msg[:50]}...). Using analyzer explosion detection. Pending human review.",
            "is_fallback": True
        }
        
        log.info(f"LLM Judgment Fallback: {fallback_verdict}")
        return {"llm_judgment": fallback_verdict}

def conditional_llm_router(state: IntelligenceState) -> Literal["llm_judgment", "end"]:
    """Conditional edge: Route to LLM judgment if explosions detected, else end."""
    is_exploding = state.get("is_exploding", False)
    if is_exploding:
        return "llm_judgment"
    else:
        return "end"

def decision_router(state: IntelligenceState) -> Literal["auto_save", "pending_approval", "discard"]:
    """STEP 5: Three-way router based on LLM confidence.
    
    Routes to:
    - auto_save: confidence > 0.85 (high confidence → save immediately)
    - pending_approval: 0.60-0.85 (medium confidence → wait for human)
    - discard: confidence < 0.60 (low confidence → trash it)
    """
    llm_judgment = state.get("llm_judgment", {})
    is_real = llm_judgment.get("is_real", False)
    confidence = llm_judgment.get("confidence", 0.5)
    
    if not is_real:
        log.info(f"Decision Router: is_real=False, confidence={confidence}. Discarding.")
        return "discard"
    
    if confidence > 0.85:
        log.info(f"Decision Router: High confidence ({confidence}). Auto-saving.")
        return "auto_save"
    else:
        log.info(f"Decision Router: Medium confidence ({confidence}). Pending approval.")
        return "pending_approval"

def auto_save_node(state: IntelligenceState) -> IntelligenceState:
    """Auto-save high-confidence trends directly to final collection."""
    print("Auto-Save: High confidence trend. Saving to database...")
    
    try:
        from db.mongo_storage import _get_db
        from bson import ObjectId
        
        db = _get_db()
        enriched = state.get("enriched_signals", [])
        llm_judgment = state.get("llm_judgment", {})
        
        # Extract topic from enriched signals
        topics_mentioned = {}
        for signal in enriched:
            for topic in signal.get("matched_topics", []):
                topics_mentioned[topic] = topics_mentioned.get(topic, 0) + 1
        
        top_topic = max(topics_mentioned, key=topics_mentioned.get) if topics_mentioned else "Unknown"
        
        trend_doc = {
            "topic": top_topic,
            "confidence": llm_judgment.get("confidence", 0),
            "reasoning": llm_judgment.get("reasoning", ""),
            "signals_count": len(enriched),
            "sources": list(set(s.get("source", "unknown") for s in enriched)),
            "approval_status": "auto_approved",
            "approved_at": datetime.now(),
            "created_at": datetime.now()
        }
        
        result = db.trends.insert_one(trend_doc)
        trend_id = str(result.inserted_id)
        
        log.info(f"Auto-Save: Trend '{top_topic}' saved with ID {trend_id}")
        print(f"Saved to trends collection: {trend_id}")
        
        return {
            "approval_id": trend_id,
            "approval_status": "auto_approved"
        }
    
    except Exception as e:
        log.error(f"Auto-Save failed: {e}")
        print(f"Error: {e}")
        return {
            "approval_id": "",
            "approval_status": "error"
        }

def pending_approval_node(state: IntelligenceState) -> IntelligenceState:
    """Save medium-confidence trends to pending collection for human review."""
    print("Pending Approval: Medium confidence. Waiting for human review...")
    
    try:
        from db.mongo_storage import _get_db
        from bson import ObjectId
        
        db = _get_db()
        enriched = state.get("enriched_signals", [])
        llm_judgment = state.get("llm_judgment", {})
        
        # Extract topic
        topics_mentioned = {}
        for signal in enriched:
            for topic in signal.get("matched_topics", []):
                topics_mentioned[topic] = topics_mentioned.get(topic, 0) + 1
        
        top_topic = max(topics_mentioned, key=topics_mentioned.get) if topics_mentioned else "Unknown"
        
        pending_doc = {
            "topic": top_topic,
            "confidence": llm_judgment.get("confidence", 0),
            "reasoning": llm_judgment.get("reasoning", ""),
            "signals_count": len(enriched),
            "sources": list(set(s.get("source", "unknown") for s in enriched)),
            "sample_signals": [s.get("content", "")[:100] for s in enriched[:3]],
            "status": "pending",
            "created_at": datetime.now(),
            "expires_at": datetime.now() + timedelta(days=7)  # 7-day TTL
        }
        
        result = db.pending_trends.insert_one(pending_doc)
        approval_id = str(result.inserted_id)
        
        log.info(f"Pending Approval: Trend '{top_topic}' saved for review. ID: {approval_id}")
        print(f"Pending approval (ID: {approval_id[:8]}...)")
        
        return {
            "approval_id": approval_id,
            "approval_status": "pending"
        }
    
    except Exception as e:
        log.error(f"Pending Approval failed: {e}")
        print(f"Error: {e}")
        return {
            "approval_id": "",
            "approval_status": "error"
        }

def discard_node(state: IntelligenceState) -> IntelligenceState:
    """Discard low-confidence trends."""
    print("Low confidence or not real. Discarding...")
    
    llm_judgment = state.get("llm_judgment", {})
    confidence = llm_judgment.get("confidence", 0)
    is_real = llm_judgment.get("is_real", False)
    reasoning = llm_judgment.get("reasoning", "")
    
    log.info(f"Discarded: is_real={is_real}, confidence={confidence}. Reason: {reasoning}")
    print(f"  Discarded: {reasoning[:50]}...")
    
    return {
        "approval_id": "discarded",
        "approval_status": "discarded"
    }


# --- Build the Graph ---

workflow = StateGraph(IntelligenceState)

workflow.add_node("reddit_scout", reddit_scout_node)
workflow.add_node("youtube_scout", youtube_scout_node)
workflow.add_node("trends_scout", trends_scout_node)
workflow.add_node("merger", merger_node)
workflow.add_node("router", router_node)
workflow.add_node("analyzer", analyzer_node)
workflow.add_node("llm_judgment", llm_judgment_node)
workflow.add_node("decision_router", decision_router)
workflow.add_node("auto_save", auto_save_node)
workflow.add_node("pending_approval", pending_approval_node)
workflow.add_node("discard", discard_node)

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
# After analysis, if explosions detected, send to LLM for verification
workflow.add_conditional_edges(
    "analyzer",
    conditional_llm_router,
    {"llm_judgment": "llm_judgment", "end": END}
)

# STEP 5: Three-Way Decision Router
# Based on LLM confidence, route to: auto_save, pending_approval, or discard
workflow.add_conditional_edges(
    "llm_judgment",
    decision_router,
    {
        "auto_save": "auto_save",
        "pending_approval": "pending_approval",
        "discard": "discard"
    }
)

# All three paths converge at END
workflow.add_edge("auto_save", END)
workflow.add_edge("pending_approval", END)
workflow.add_edge("discard", END)

# Compile
app = workflow.compile()