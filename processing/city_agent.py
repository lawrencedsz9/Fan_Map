from typing import TypedDict, List, Dict, Any, Literal
from langgraph.graph import StateGraph, END
from collectors import collect_all
from processing.topic_extraction import enrich_all
from db.mongo_storage import save_signals

class CityState(TypedDict):
    """The memory of our city-building agent."""
    raw_signals: List[Dict[str, Any]]
    enriched_signals: List[Dict[str, Any]]
    city_plan: List[Dict[str, Any]]
    is_exploding: bool

# --- Nodes ---

def scout_node(state: CityState) -> CityState:
    print("🤖 Scout: Scavenging the internet for signals...")
    signals = collect_all()
    # Save raw signals immediately for persistence
    try:
        save_signals(signals)
    except Exception as e:
        print(f"⚠️ Persistence warning in Scout: {e}")
    return {"raw_signals": signals}

def analyzer_node(state: CityState) -> CityState:
    """The Analyst: Crushes raw ore into refined building materials."""
    print("🧠 Analyzer: Calculating hype levels...")
    raw = state.get("raw_signals", [])
    if not raw:
        return {"enriched_signals": [], "is_exploding": False}
    
    # Use existing NLP logic (or LLM later)
    enriched = enrich_all(raw)
    
    # Simple logic: If any topic has > 5 mentions, it's "Exploding"
    # This determines if we loop back (in future steps)
    counts = {}
    for s in enriched:
        for t in s.get("matched_topics", []):
            counts[t] = counts.get(t, 0) + 1
    
    is_exploding = any(c > 5 for c in counts.values())
    return {"enriched_signals": enriched, "is_exploding": is_exploding}

def architect_node(state: CityState) -> CityState:
    """The City Planner: Assigns X,Z coordinates for the 3D grid."""
    print("🏗️ Architect: Drafting city blueprints...")
    processed = state.get("enriched_signals", [])
    
    # 1. Aggregate scores by topic
    topic_stats = {}
    for signal in processed:
        for topic in signal.get("matched_topics", []):
            if topic not in topic_stats:
                topic_stats[topic] = {"score": 0, "sentiment": 0, "sources": set()}
            
            # Simple Hype Score Algorithm
            weight = 1
            if signal.get("source") == "youtube": weight = 2
            if signal.get("source") == "google_trends": weight = 3
            
            topic_stats[topic]["score"] += weight
            topic_stats[topic]["sources"].add(signal.get("source"))

    # 2. Map to Grid (Spiral Layout to keep hottest topics in center)
    city_buildings = []
    sorted_topics = sorted(topic_stats.items(), key=lambda x: x[1]['score'], reverse=True)
    
    # Simple grid logic for now
    import math
    for i, (topic, data) in enumerate(sorted_topics):
        # Height = Hype Score
        height = min(data["score"] * 10, 300) # Cap height
        
        # Color based on source mix (Sentiment placeholder)
        color = "#00ff88" # Default Green
        if "youtube" in data["sources"]: color = "#ff0000" # Red
        if "google_trends" in data["sources"]: color = "#4285f4" # Blue
        
        # Spiral Position: place hottest topics near 0,0
        angle = 0.5 * i
        radius = 4 * math.sqrt(i)
        x = radius * math.cos(angle) * 20 # Spread out by 20 units
        z = radius * math.sin(angle) * 20
        
        city_buildings.append({
            "id": topic,
            "x": round(x, 2),
            "z": round(z, 2),
            "height": height,
            "color": color,
            "score": data["score"]
        })
        
    return {"city_plan": city_buildings}

# --- 3. Build the Graph ---
workflow = StateGraph(CityState)

workflow.add_node("scout", scout_node)
workflow.add_node("analyzer", analyzer_node)
workflow.add_node("architect", architect_node)

# Define the flow
workflow.set_entry_point("scout")
workflow.add_edge("scout", "analyzer")
workflow.add_edge("analyzer", "architect")
workflow.add_edge("architect", END)

# Compile
app = workflow.compile()
