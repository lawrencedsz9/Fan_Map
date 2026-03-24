"""
FastAPI server — exposes the Fandom Intelligence Graph as a live API + dashboard.
"""

from __future__ import annotations
import asyncio
import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

log = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)


app = FastAPI(
    title="Fandom Intelligence Graph",
    description="Real-Time Internet Attention Map",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for local dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


_state: dict = {
    "graph": None,
    "stats": None,
    "trend_report": None,
    "signals": [],
}


def _run_pipeline() -> None:
    """Execute the full collection → extraction → graph → trend pipeline."""
    import networkx as nx
    from processing.intelligence_agent import app as intelligence_agent_app
    from processing.trend_detector import get_trend_report
    from graph.build_graph import build_graph, get_graph_stats
    from graph.visualize import render_graph
    from config import GRAPH_OUTPUT

    log.info("Running pipeline with LangGraph Intelligence Agent...")
    
    # LangGraph Execution: Scout -> Analyzer
    result = intelligence_agent_app.invoke({"raw_signals": []})
    enriched = result.get("enriched_signals", [])

    # Legacy Graph Building (for 2D dashboard)
    G = build_graph(enriched)
    report = get_trend_report(enriched)
    render_graph(G, GRAPH_OUTPUT)

    _state["graph"] = nx.node_link_data(G)
    _state["stats"] = get_graph_stats(G)
    _state["trend_report"] = report
    _state["signals"] = enriched


@app.on_event("startup")
async def startup() -> None:
    """Start server immediately; run pipeline in background so Render sees an open port."""
    async def run_pipeline_background() -> None:
        try:
            log.info("Starting background pipeline...")
            await asyncio.to_thread(_run_pipeline)
            log.info("Startup pipeline finished successfully")
        except Exception as e:
            # Log the error but don't crash - app will still start with empty state
            log.warning("Background pipeline encountered issues: %s", str(e), exc_info=True)
            log.warning("App will continue running. MongoDB may be unavailable temporarily.")
            log.warning("Attempting to re-run pipeline in 30 seconds...")
            
            # Retry after 30 seconds
            await asyncio.sleep(30)
            try:
                await asyncio.to_thread(_run_pipeline)
                log.info("Pipeline retry successful")
            except Exception as retry_e:
                log.warning("Pipeline retry also failed: %s", str(retry_e))
                log.info("Running with limited data until MongoDB recovers")

    asyncio.create_task(run_pipeline_background())


@app.post("/api/refresh")
async def refresh():
    """Re-run the full pipeline with fresh data."""
    _run_pipeline()
    return {"status": "ok", "message": "Pipeline refreshed"}


@app.get("/api/stats")
async def stats():
    """Get graph statistics and anime rankings."""
    return JSONResponse(_state["stats"] or {})


@app.get("/api/trends")
async def trends():
    """Get the latest trend explosion report."""
    return JSONResponse(_state["trend_report"] or {})


@app.get("/api/graph")
async def graph_data():
    """Get the raw graph data (node-link format)."""
    return JSONResponse(_state["graph"] or {})


@app.get("/api/signals")
async def signals():
    """Get raw collected signals (last run)."""
    return JSONResponse(_state["signals"][:100])


@app.get("/api/pending-approvals")
async def get_pending_approvals():
    """STEP 5: Get all trends pending human approval."""
    try:
        from db.mongo_storage import _get_db
        from bson import ObjectId
        
        db = _get_db()
        pending = list(db.pending_trends.find(
            {"status": "pending"},
            {"_id": 1, "topic": 1, "confidence": 1, "reasoning": 1, "signals_count": 1, "sources": 1, "created_at": 1}
        ).sort("created_at", -1))
        
        result = {
            "count": len(pending),
            "trends": [
                {
                    "id": str(p["_id"]),
                    "topic": p.get("topic", "Unknown"),
                    "confidence": p.get("confidence", 0),
                    "reasoning": p.get("reasoning", ""),
                    "signals_count": p.get("signals_count", 0),
                    "sources": p.get("sources", []),
                    "created_at": p.get("created_at", "").isoformat() if hasattr(p.get("created_at"), "isoformat") else str(p.get("created_at", ""))
                }
                for p in pending
            ]
        }
        return JSONResponse(result)
    
    except Exception as e:
        log.error(f"Error fetching pending approvals: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/approve/{trend_id}")
async def approve_trend(trend_id: str, action: str = "approve"):
    """STEP 5: Approve or reject a pending trend.
    
    Args:
        trend_id: MongoDB _id of the pending trend
        action: "approve" or "reject"
    """
    try:
        from db.mongo_storage import _get_db
        from bson import ObjectId
        
        db = _get_db()
        
        # Find pending trend
        pending = db.pending_trends.find_one({"_id": ObjectId(trend_id)})
        if not pending:
            return JSONResponse({"error": "Trend not found"}, status_code=404)
        
        if action == "approve":
            # Move to final trends collection
            final_trend = {
                "topic": pending.get("topic", "Unknown"),
                "confidence": pending.get("confidence", 0),
                "reasoning": pending.get("reasoning", ""),
                "signals_count": pending.get("signals_count", 0),
                "sources": pending.get("sources", []),
                "approval_status": "human_approved",
                "approved_at": asyncio.get_event_loop().time(),
                "created_at": pending.get("created_at")
            }
            result = db.trends.insert_one(final_trend)
            
            # Remove from pending
            db.pending_trends.delete_one({"_id": ObjectId(trend_id)})
            
            log.info(f"Trend {trend_id} APPROVED and saved to trends collection")
            return JSONResponse({
                "status": "approved",
                "trend_id": str(result.inserted_id),
                "message": f"Trend '{pending.get('topic')}' approved and saved"
            })
        
        elif action == "reject":
            # Just remove from pending
            db.pending_trends.delete_one({"_id": ObjectId(trend_id)})
            
            log.info(f"Trend {trend_id} REJECTED")
            return JSONResponse({
                "status": "rejected",
                "message": f"Trend '{pending.get('topic')}' rejected"
            })
        
        else:
            return JSONResponse({"error": "Invalid action. Use 'approve' or 'reject'"}, status_code=400)
    
    except Exception as e:
        log.error(f"Error processing approval: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/anime/{name}")
async def anime_detail(name: str):
    """Get details for a specific anime topic."""
    if not _state["stats"]:
        return JSONResponse({"error": "No data yet"}, status_code=404)

    rankings = _state["stats"].get("rankings", [])
    match = next(
        (r for r in rankings if r["anime"].lower() == name.lower()),
        None,
    )
    if not match:
        return JSONResponse(
            {"error": f"Anime '{name}' not found"},
            status_code=404,
        )

    related_signals = [
        s
        for s in _state["signals"]
        if name.lower() in [t.lower() for t in s.get("matched_topics", [])]
    ][:20]

    return JSONResponse({**match, "recent_signals": related_signals})


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Serve the main dashboard from Vite build output."""
    from config import BASE_DIR
    
    dashboard_dist = BASE_DIR / "dashboard" / "dist" / "index.html"
    
    if dashboard_dist.exists():
        return dashboard_dist.read_text(encoding="utf-8")
    
    # Fallback if not built yet
    return """
    <h1>Dashboard not built yet</h1>
    <p>Run <code>npm run build</code> in the dashboard folder to build the Vite project.</p>
    <p>For development, run <code>npm run dev</code> and access the dashboard on port 5173.</p>
    """


@app.get("/graph", response_class=HTMLResponse)
async def graph_view():
    """Serve the interactive graph visualization."""
    from config import GRAPH_OUTPUT

    if GRAPH_OUTPUT.exists():
        return HTMLResponse(GRAPH_OUTPUT.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Graph not generated yet. Hit /api/refresh first.</h1>")


# Mount static files from Vite build
dashboard_dist_path = Path(__file__).resolve().parent.parent / "dashboard" / "dist"
if dashboard_dist_path.exists():
    app.mount("/assets", StaticFiles(directory=str(dashboard_dist_path / "assets")), name="assets")
