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

# Color scheme per node type - Ghibli Aesthetic
COLORS = {
    "Anime": "#D4AF37",        # Ghibli Gold
    "Character": "#E89B7A",    # Ghibli Peach
    "Platform": "#E89B7A",     # Ghibli Peach
    "Source": "#6B8E6F",       # Ghibli Forest
    "Studio": "#9B6B4F",       # Ghibli Brown
    "Unknown": "#999999",      # Gray
}

EDGE_COLORS = {
    "CHARACTER_OF": "#9B6B4F",
    "MENTIONED_ON": "#6B8E6F",
    "PRODUCED_BY": "#D4AF37",
    "SHARES_FANDOM": "#E89B7A",
    "TRENDING_WITH": "#9B6B4F",
}


def render_graph(G: nx.Graph, output_path: str | Path) -> Path:
    """Render the graph as an interactive HTML visualization."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    net = Network(
        height="100vh",
        width="100%",
        bgcolor="#f4f1ea",
        font_color="#2a2a1e",
        directed=False,
        select_menu=False,
        filter_menu=False,
    )

    # Physics configuration for soft, breathing movement (Ghibli aesthetic)
    net.set_options("""
    {
        "physics": {
            "barnesHut": {
                "gravitationalConstant": -2000,
                "centralGravity": 0.1,
                "springLength": 150,
                "damping": 0.09,
                "avoidOverlap": 0.1
            },
            "solver": "barnesHut",
            "stabilization": {
                "iterations": 200,
                "fit": true
            },
            "minVelocity": 0.75
        },
        "nodes": {
            "borderWidth": 3,
            "borderWidthSelected": 5,
            "color": {
                "border": "#6B8E6F",
                "highlight": {
                    "border": "#D4AF37",
                    "background": "#E89B7A"
                }
            },
            "font": {
                "size": 14,
                "face": "Fredoka One, monospace",
                "color": "#2a2a1e",
                "strokeWidth": 0,
                "bold": {
                    "size": 16
                }
            },
            "shadow": {
                "enabled": true,
                "color": "rgba(107, 142, 111, 0.2)",
                "size": 8,
                "x": 2,
                "y": 2
            }
        },
        "edges": {
            "smooth": {
                "type": "continuous"
            },
            "color": {
                "inherit": false,
                "opacity": 0.7
            },
            "width": 2,
            "shadow": {
                "enabled": true,
                "color": "rgba(107, 142, 111, 0.15)",
                "size": 4,
                "x": 1,
                "y": 1
            }
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
    """Inject Ghibli theme + title bar into the pyvis HTML output."""
    content = html_path.read_text(encoding="utf-8")

    custom_css = """
    <style>
        body {
            margin: 0;
            background: #f4f1ea;
            font-family: 'Fredoka One', 'Courier New', monospace;
            overflow: hidden;
            background-image: 
                url('data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAYAAABytg0kAAAA120lEQVQIHWP4z+DwH0ghyMDAwMDAwMDg4ODAf/J/Bv4DAAD//wMCACoBAkcb8sUiYGBg+M/wn4GBgf8/AwMDAwP//xkYGP7/ZwAyGABk/hnIM/xnYPjPwPI/FQOrOgYGBgaGf4wMDg8ZGP4z/GdgYGBg+P+fgYGBgQGZnIGBgQGZhoGBgQGZioGBgQGZhYGBgQGZmYGBgQGZlYGBgQGZn4GBgQGZj4GBgQGZgYGBgQGZiYGBgQGZhYGBgQGZjYGBgQGZjYGBgQGZk4GBgQGZk4GBgQGZj4GBgQGZi4GBgQGZk4GBgQGZjYGBgQGZi4GBgQGZh4GBgQGZi4GBgQGZi4GBgQGZi4GBgQGZi4GBgQGZi4GBgQGZhYGBgQGZhYGBgQGZi4GBgQGZi4GBgQGZi4GBgQGZi4GBgQGZi4GBgQGZi4GBgQGZh4GBgQGZh4GBgQGZh4GBgQGZh4GBgQGZh4GBgQGZh4HBgQGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYG');
            background-repeat: repeat;
            background-size: 2px 2px;
        }
        #title-bar {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            z-index: 1000;
            background: linear-gradient(135deg, #6B8E6F 0%, #5a8060 50%, #4a7050 100%);
            border: 3px solid #6B8E6F;
            border-bottom: 6px solid #D4AF37;
            padding: 16px 24px;
            display: flex;
            align-items: center;
            gap: 16px;
            box-shadow: 0 8px 0px rgba(0, 0, 0, 0.1), inset 0 2px 0px rgba(107, 142, 111, 0.3);
        }
        #title-bar h1 {
            color: #2a2a1e;
            font-size: 24px;
            margin: 0;
            font-weight: 900;
            text-shadow: 2px 2px 0px rgba(212, 175, 55, 0.3);
            letter-spacing: 1px;
        }
        #title-bar span {
            color: #E89B7A;
            font-size: 12px;
            font-weight: 700;
            letter-spacing: 1px;
            text-transform: uppercase;
        }
        .pulse {
            width: 10px;
            height: 10px;
            background: #D4AF37;
            border: 2px solid #6B8E6F;
            border-radius: 50%;
            animation: gentle-pulse 0.8s ease-in-out infinite;
            box-shadow: 0 0 6px rgba(212, 175, 55, 0.4);
        }
        @keyframes gentle-pulse {
            0%, 100% { opacity: 0.8; transform: scale(1); }
            50% { opacity: 1; transform: scale(1.1); }
        }
    </style>
    <div id="title-bar">
        <div class="pulse"></div>
        <h1>✦ FANDOM GRAPH ✦</h1>
        <span>Network Visualization</span>
    </div>
    """

    content = content.replace("<body>", f"<body>{custom_css}", 1)
    html_path.write_text(content, encoding="utf-8")
