"""
Graph Visualizer — renders the attention graph as an interactive HTML page.

Uses pyvis to create stunning interactive graph visualizations.
"""

from __future__ import annotations
import logging
from pathlib import Path

import networkx as nx
from pyvis.network import Network

log = logging.getLogger(__name__)

# Color scheme per node type
COLORS = {
    "Anime": "#ff6b6b",       # Coral red
    "Character": "#4ecdc4",   # Teal
    "Platform": "#45b7d1",    # Sky blue
    "Source": "#96ceb4",      # Sage green
    "Studio": "#ffeaa7",      # Warm yellow
    "Unknown": "#dfe6e9",     # Light gray
}

EDGE_COLORS = {
    "CHARACTER_OF": "#4ecdc4",
    "MENTIONED_ON": "#74b9ff",
    "PRODUCED_BY": "#ffeaa7",
    "SHARES_FANDOM": "#fd79a8",
    "TRENDING_WITH": "#e17055",
}


def render_graph(G: nx.Graph, output_path: str | Path) -> Path:
    """Render the graph as an interactive HTML visualization."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    net = Network(
        height="100vh",
        width="100%",
        bgcolor="#0a0a0a",
        font_color="#ffffff",
        directed=False,
        select_menu=False,
        filter_menu=False,
    )

    # Physics configuration for beautiful layout
    net.set_options("""
    {
        "physics": {
            "forceAtlas2Based": {
                "gravitationalConstant": -80,
                "centralGravity": 0.008,
                "springLength": 180,
                "springConstant": 0.04,
                "damping": 0.5
            },
            "solver": "forceAtlas2Based",
            "stabilization": {
                "iterations": 200
            }
        },
        "nodes": {
            "borderWidth": 2,
            "borderWidthSelected": 4,
            "font": {
                "size": 14,
                "face": "monospace"
            }
        },
        "edges": {
            "smooth": {
                "type": "continuous"
            },
            "color": {
                "inherit": false,
                "opacity": 0.6
            },
            "width": 1.5
        },
        "interaction": {
            "hover": true,
            "tooltipDelay": 100,
            "navigationButtons": true,
            "keyboard": true
        }
    }
    """)

    # Add nodes
    for node, data in G.nodes(data=True):
        node_type = data.get("type", "Unknown")
        size = data.get("size", 15)
        color = COLORS.get(node_type, COLORS["Unknown"])

        # Build tooltip
        tooltip_parts = [f"<b>{node}</b>", f"Type: {node_type}"]
        if data.get("attention_score"):
            tooltip_parts.append(f"Attention Score: {data['attention_score']}")
        if data.get("reddit_mentions"):
            tooltip_parts.append(f"Reddit: {data['reddit_mentions']} mentions")
        if data.get("youtube_mentions"):
            tooltip_parts.append(f"YouTube: {data['youtube_mentions']} mentions")
        if data.get("google_trends_score"):
            tooltip_parts.append(f"Google Trends: {data['google_trends_score']}")

        tooltip = "<br>".join(tooltip_parts)

        net.add_node(
            node,
            label=node,
            size=size,
            color=color,
            title=tooltip,
            shape="dot" if node_type != "Anime" else "diamond",
        )

    # Add edges
    for u, v, data in G.edges(data=True):
        relation = data.get("relation", "")
        weight = data.get("weight", 1)
        color = EDGE_COLORS.get(relation, "#636e72")
        label = data.get("label", relation)

        net.add_edge(
            u, v,
            color=color,
            width=min(weight * 0.5, 5),
            title=label,
        )

    net.save_graph(str(output_path))

    # Inject custom CSS into the generated HTML for a slicker look
    _inject_custom_styles(output_path)

    log.info("Graph visualization saved to %s", output_path)
    return output_path


def _inject_custom_styles(html_path: Path) -> None:
    """Inject dark theme + title bar into the pyvis HTML output."""
    content = html_path.read_text(encoding="utf-8")

    custom_css = """
    <style>
        body {
            margin: 0;
            background: #0a0a0a;
            font-family: 'Segoe UI', monospace;
            overflow: hidden;
        }
        #title-bar {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            z-index: 1000;
            background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 100%);
            border-bottom: 1px solid #333;
            padding: 12px 24px;
            display: flex;
            align-items: center;
            gap: 16px;
        }
        #title-bar h1 {
            color: #ff6b6b;
            font-size: 18px;
            margin: 0;
        }
        #title-bar span {
            color: #888;
            font-size: 13px;
        }
        .pulse {
            width: 8px;
            height: 8px;
            background: #00ff88;
            border-radius: 50%;
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.3; }
        }
    </style>
    <div id="title-bar">
        <div class="pulse"></div>
        <h1>Fandom Intelligence Graph</h1>
        <span>Real-Time Internet Attention Map</span>
    </div>
    """

    content = content.replace("<body>", f"<body>{custom_css}", 1)
    html_path.write_text(content, encoding="utf-8")
