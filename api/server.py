"""
FastAPI server — exposes the Fandom Intelligence Graph as a live API + dashboard.
"""

from __future__ import annotations
import asyncio
import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

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
            log.warning("⚠️  Background pipeline encountered issues: %s", str(e), exc_info=True)
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
    """Serve the main dashboard."""
    return _get_dashboard_html()


@app.get("/graph", response_class=HTMLResponse)
async def graph_view():
    """Serve the interactive graph visualization."""
    from config import GRAPH_OUTPUT

    if GRAPH_OUTPUT.exists():
        return HTMLResponse(GRAPH_OUTPUT.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Graph not generated yet. Hit /api/refresh first.</h1>")


def _get_dashboard_html() -> str:
    """Generate the dashboard HTML."""
    dashboard_path = (
        Path(__file__).resolve().parent.parent / "dashboard" / "index.html"
    )
    if dashboard_path.exists():
        return dashboard_path.read_text(encoding="utf-8")
    return "<h1>Dashboard not found</h1>"
