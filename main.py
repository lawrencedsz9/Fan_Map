"""
Fandom Intelligence Graph — Main Entry Point

This is the orchestrator that ties everything together.
Run it to:
  1. Collect attention signals from the internet
  2. Extract entities and topics via NLP
  3. Build the knowledge graph
  4. Detect trend explosions
  5. Generate the interactive visualization
  6. Launch the dashboard

Usage:
    python main.py               Run pipeline + launch dashboard
    python main.py --collect     Run collection only
    python main.py --graph       Build graph only 
    python main.py --serve       Launch dashboard only
"""

from __future__ import annotations
import argparse
import logging
import sys
import webbrowser
from pathlib import Path

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).parent))

from config import DATA_DIR, GRAPH_OUTPUT
from db.mongo_storage import save_signals
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
log = logging.getLogger("main")

def run_collection() -> list[dict]:
    """Step 1: Collect signals."""
    console.print("\n[bold cyan]COLLECTING ATTENTION SIGNALS...[/bold cyan]")

    from collectors import collect_all
    signals = collect_all()

    # Cache signals in MongoDB
    save_signals(signals)

    console.print(f"  Collected [bold green]{len(signals)}[/bold green] signals")
    return signals


def run_extraction(signals: list[dict]) -> list[dict]:
    """Step 2: Extract entities."""
    console.print("\n[bold cyan]EXTRACTING ENTITIES...[/bold cyan]")

    from processing.topic_extraction import enrich_all
    enriched = enrich_all(signals)

    entity_count = sum(
        len(e) for s in enriched for e in s.get("entities", {}).values()
    )
    console.print(f"  Extracted [bold green]{entity_count}[/bold green] entities")
    return enriched


def run_graph(enriched: list[dict]):
    """Step 3-4: Build graph + detect trends."""
    import networkx as nx
    from graph.build_graph import build_graph, get_graph_stats
    from graph.visualize import render_graph
    from processing.trend_detector import get_trend_report

    # Build graph
    console.print("\n[bold cyan]BUILDING KNOWLEDGE GRAPH...[/bold cyan]")
    G = build_graph(enriched)
    stats = get_graph_stats(G)

    console.print(f"  Nodes: [bold green]{stats['total_nodes']}[/bold green]")
    console.print(f"  Edges: [bold green]{stats['total_edges']}[/bold green]")

    # Render visualization
    console.print("\n[bold cyan]RENDERING VISUALIZATION...[/bold cyan]")
    path = render_graph(G, GRAPH_OUTPUT)
    console.print(f"  Saved to [bold]{path}[/bold]")

    # Detect trends
    console.print("\n[bold cyan]SCANNING FOR TREND EXPLOSIONS...[/bold cyan]")
    report = get_trend_report(enriched)

    # Print the epic results
    _print_rankings(stats)
    _print_explosions(report)

    return G, stats, report


def _print_rankings(stats: dict):
    """Print a beautiful rankings table."""
    table = Table(title="Anime Attention Rankings", border_style="bright_cyan")
    table.add_column("#", style="bold", width=4)
    table.add_column("Anime", style="bold white", min_width=20)
    table.add_column("Score", justify="right", style="bold green")
    table.add_column("Reddit", justify="right", style="red")
    table.add_column("YouTube", justify="right", style="bright_red")
    table.add_column("Trends", justify="right", style="blue")

    for r in stats.get("rankings", []):
        score_pct = f"{r['attention_score'] * 100:.0f}%"
        table.add_row(
            str(r["rank"]),
            r["anime"],
            score_pct,
            str(r["reddit_mentions"]),
            str(r["youtube_mentions"]),
            str(r["google_trends_score"]),
        )

    console.print()
    console.print(table)


def _print_explosions(report: dict):
    """Print trend explosions."""
    explosions = report.get("explosions", [])
    if not explosions:
        console.print(
            Panel(
                "[dim]No explosions detected yet.\n"
                "Run the pipeline multiple times to build baseline data,[/dim]\n"
                "[dim]then trend spikes will be detected automatically.[/dim]",
                title="Trend Explosion Detector",
                border_style="yellow",
            )
        )
        return

    for e in explosions:
        verdict = e["verdict"]
        color = "red" if "MEGA" in verdict else "yellow" if "VIRAL" in verdict else "cyan"
        console.print(
            Panel(
                f"[bold]{e['topic']}[/bold]\n"
                f"  {e['explosion_ratio']}x baseline  |  "
                f"Current: {e['current_mentions']}  |  "
                f"Avg: {e['baseline_average']}",
                title=f"[bold {color}]{verdict}[/bold {color}]",
                border_style=color,
            )
        )


def _find_available_port(host: str, start: int, end: int) -> int:
    """Return first port in [start, end) that can be bound. Raises OSError if none."""
    import socket
    for port in range(start, end):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind((host, port))
                return port
        except OSError:
            continue
    raise OSError(f"No free port in range {start}-{end - 1}")


def launch_server():
    """Launch the FastAPI dashboard. Uses PORT env if set (e.g. Render), else picks 8000 or next free port."""
    import os
    import uvicorn

    host = "0.0.0.0"
    port_str = os.getenv("PORT")
    if port_str and port_str.isdigit():
        port = int(port_str)
    else:
        port = _find_available_port(host, 8000, 8010)
        if port != 8000:
            log.warning("Port 8000 in use, using port %s", port)

    url = f"http://localhost:{port}"
    console.print("\n[bold cyan]LAUNCHING DASHBOARD...[/bold cyan]")
    console.print(f"  Dashboard: [bold underline]{url}[/bold underline]")
    console.print(f"  Graph:     [bold underline]{url}/graph[/bold underline]")
    console.print(f"  API:       [bold underline]{url}/api/stats[/bold underline]")
    console.print("\n[dim]Press Ctrl+C to stop[/dim]\n")
    webbrowser.open(url)
    uvicorn.run("api.server:app", host=host, port=port, reload=False)


def main():
    parser = argparse.ArgumentParser(description="Fandom Intelligence Graph")
    parser.add_argument("--collect", action="store_true", help="Run collection only")
    parser.add_argument("--graph", action="store_true", help="Build graph from cached signals")
    parser.add_argument("--serve", action="store_true", help="Launch dashboard only")
    args = parser.parse_args()

    console.print(Panel.fit(
        "[bold red]FANDOM INTELLIGENCE GRAPH[/bold red]\n"
        "[dim]Real-Time Internet Attention Map[/dim]",
        border_style="red",
    ))

    if args.serve:
        launch_server()
        return

    if args.graph:
        console.print("[red]Graph-from-cache mode is not supported with MongoDB yet.[/red]")
        return

    if args.collect:
        run_collection()
        return

    # Full pipeline
    signals = run_collection()
    enriched = run_extraction(signals)
    run_graph(enriched)
    launch_server()


if __name__ == "__main__":
    main()
