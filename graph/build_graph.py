"""
Knowledge Graph Builder — constructs an attention graph from enriched signals.

Nodes: Anime, Characters, Platforms, Communities
Edges: MENTIONED_ON, DISCUSSED_IN, CHARACTER_OF, TRENDING_WITH
"""

from __future__ import annotations
import logging
from typing import Any
from collections import defaultdict

import networkx as nx

log = logging.getLogger(__name__)


def build_graph(signals: list[dict[str, Any]]) -> nx.Graph:
    """Build a NetworkX graph from enriched signals."""
    G = nx.Graph()

    # Aggregate attention counts
    mention_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    topic_scores: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "reddit_mentions": 0,
            "youtube_mentions": 0,
            "google_trends_score": 0,
            "total_engagement": 0,
        }
    )

    for signal in signals:
        source = signal.get("source", "unknown")
        topics = signal.get("matched_topics", [])
        entities = signal.get("entities", {})

        for topic in topics:
            mention_counts[topic][source] += 1

            if source == "reddit":
                topic_scores[topic]["reddit_mentions"] += 1
                topic_scores[topic]["total_engagement"] += signal.get("score", 0)
            elif source == "youtube":
                topic_scores[topic]["youtube_mentions"] += 1
            elif source == "google_trends":
                topic_scores[topic]["google_trends_score"] = signal.get(
                    "latest_score", 0
                )

            # Add character nodes
            for char in entities.get("characters", []):
                if not G.has_node(char):
                    G.add_node(char, type="Character", anime=topic, size=15)
                if not G.has_edge(topic, char):
                    G.add_edge(topic, char, relation="CHARACTER_OF", weight=2)

            # Add platform nodes
            for platform in entities.get("platforms", []):
                if not G.has_node(platform):
                    G.add_node(platform, type="Platform", size=20)
                mention_counts[topic][platform] = (
                    mention_counts[topic].get(platform, 0) + 1
                )

            # Add studio nodes
            for studio in entities.get("studios", []):
                if not G.has_node(studio):
                    G.add_node(studio, type="Studio", size=18)
                if not G.has_edge(topic, studio):
                    G.add_edge(topic, studio, relation="PRODUCED_BY", weight=3)

    # Add anime nodes with aggregated data
    for topic, scores in topic_scores.items():
        attention_score = _compute_attention_score(scores)
        node_size = max(20, int(attention_score * 50))
        G.add_node(
            topic,
            type="Anime",
            size=node_size,
            attention_score=round(attention_score, 3),
            **scores,
        )

    # Add source community nodes and edges
    for topic, sources in mention_counts.items():
        for source, count in sources.items():
            source_label = source.title()
            if not G.has_node(source_label):
                G.add_node(source_label, type="Source", size=12)
            G.add_edge(
                topic,
                source_label,
                relation="MENTIONED_ON",
                weight=count,
                label=f"{count} mentions",
            )

    # Connect anime that share characters or co-occur
    anime_nodes = [n for n, d in G.nodes(data=True) if d.get("type") == "Anime"]
    for i, a1 in enumerate(anime_nodes):
        for a2 in anime_nodes[i + 1 :]:
            shared = set(G.neighbors(a1)) & set(G.neighbors(a2))
            shared_chars = [
                n for n in shared if G.nodes[n].get("type") == "Character"
            ]
            if shared_chars:
                G.add_edge(a1, a2, relation="SHARES_FANDOM", weight=len(shared_chars))

    log.info(
        "Graph built: %d nodes, %d edges",
        G.number_of_nodes(),
        G.number_of_edges(),
    )
    return G


def _compute_attention_score(scores: dict[str, Any]) -> float:
    """Compute a 0-1 attention score from raw signal counts."""
    from config import WEIGHTS

    reddit = min(scores.get("reddit_mentions", 0) / 30, 1.0)
    youtube = min(scores.get("youtube_mentions", 0) / 20, 1.0)
    trends = min(scores.get("google_trends_score", 0) / 100, 1.0)
    engagement = min(scores.get("total_engagement", 0) / 10000, 1.0)

    score = (
        WEIGHTS["reddit"] * reddit
        + WEIGHTS["youtube"] * youtube
        + WEIGHTS["google_trends"] * trends
        + WEIGHTS["news"] * engagement
    )
    return min(score, 1.0)


def get_graph_stats(G: nx.Graph) -> dict[str, Any]:
    """Return a summary of the graph for the API."""
    anime_nodes = {n: d for n, d in G.nodes(data=True) if d.get("type") == "Anime"}
    rankings = sorted(
        anime_nodes.items(),
        key=lambda x: x[1].get("attention_score", 0),
        reverse=True,
    )

    return {
        "total_nodes": G.number_of_nodes(),
        "total_edges": G.number_of_edges(),
        "anime_count": len(anime_nodes),
        "rankings": [
            {
                "rank": i + 1,
                "anime": name,
                "attention_score": data.get("attention_score", 0),
                "reddit_mentions": data.get("reddit_mentions", 0),
                "youtube_mentions": data.get("youtube_mentions", 0),
                "google_trends_score": data.get("google_trends_score", 0),
            }
            for i, (name, data) in enumerate(rankings)
        ],
        "node_types": _count_types(G),
    }


def _count_types(G: nx.Graph) -> dict[str, int]:
    types: dict[str, int] = defaultdict(int)
    for _, data in G.nodes(data=True):
        types[data.get("type", "Unknown")] += 1
    return dict(types)
