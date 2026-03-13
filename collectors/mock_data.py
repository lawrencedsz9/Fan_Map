"""Mock data generator — realistic fake signals so the project works without API keys."""

from __future__ import annotations
import random
from datetime import datetime, timezone, timedelta
from typing import Any


# ── Realistic templates ──────────────────────────────────────────────────────

_REDDIT_TEMPLATES = [
    "{topic} Episode {ep} was absolutely insane!",
    "Just caught up on {topic} and wow",
    "{char} vs {villain} might be the best fight in {topic}",
    "Why {topic} is peak fiction right now",
    "Unpopular opinion: {topic} latest arc is mid",
    "{topic} animation quality has gone through the roof",
    "Theory: {char} will unlock a new power in {topic}",
    "{topic} just broke streaming records on Crunchyroll",
    "Rewatching {topic} and it hits different now",
    "The {topic} fandom is eating good this week",
]

_YT_TEMPLATES = [
    "{topic} Episode {ep} Reaction & Review",
    "Why {topic} Is Breaking The Internet Right Now",
    "{char}'s New Power EXPLAINED | {topic}",
    "{topic} Season Finale - Everything You Missed",
    "Ranking Every Arc in {topic}",
    "{topic} vs {topic2} - Which Is Better?",
    "The Rise of {topic} - A Deep Dive",
]

_CHARACTERS: dict[str, list[str]] = {
    "One Piece": ["Luffy", "Zoro", "Sanji", "Nami", "Shanks", "Kaido", "Kizaru"],
    "Jujutsu Kaisen": ["Gojo", "Yuji", "Sukuna", "Megumi", "Todo"],
    "Solo Leveling": ["Sung Jin-Woo", "Igris", "Thomas Andre"],
    "Demon Slayer": ["Tanjiro", "Nezuko", "Muzan", "Rengoku", "Akaza"],
    "Attack on Titan": ["Eren", "Mikasa", "Levi", "Armin", "Reiner"],
    "Dragon Ball": ["Goku", "Vegeta", "Gohan", "Frieza", "Beerus"],
    "Naruto": ["Naruto", "Sasuke", "Kakashi", "Itachi", "Madara"],
    "My Hero Academia": ["Deku", "Bakugo", "All Might", "Todoroki"],
    "Chainsaw Man": ["Denji", "Makima", "Power", "Aki"],
    "Spy x Family": ["Anya", "Loid", "Yor", "Bond"],
}

_VILLAINS = ["the final boss", "the new villain", "that one character"]

_SUBREDDITS_MAP: dict[str, str] = {
    "One Piece": "OnePiece",
    "Jujutsu Kaisen": "JuJutsuKaisen",
    "Solo Leveling": "sololeveling",
    "Demon Slayer": "KimetsuNoYaiba",
    "Attack on Titan": "ShingekiNoKyojin",
    "Dragon Ball": "Dragonballsuper",
    "Naruto": "Naruto",
    "My Hero Academia": "BokuNoHeroAcademia",
    "Chainsaw Man": "ChainsawMan",
    "Spy x Family": "SpyxFamily",
}


def _char(topic: str) -> str:
    return random.choice(_CHARACTERS.get(topic, ["the protagonist"]))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _recent_time() -> str:
    offset = random.randint(0, 7200)
    return (datetime.now(timezone.utc) - timedelta(seconds=offset)).isoformat()


# ── Public API ───────────────────────────────────────────────────────────────

def generate_mock_signals(topics: list[str]) -> list[dict[str, Any]]:
    """Generate a batch of realistic mock signals across all sources."""
    signals: list[dict[str, Any]] = []

    for topic in topics:
        # Weighted randomness — some anime "trend harder"
        heat = random.uniform(0.3, 1.0)

        # Reddit signals
        n_reddit = int(random.randint(5, 25) * heat)
        for _ in range(n_reddit):
            tpl = random.choice(_REDDIT_TEMPLATES)
            title = tpl.format(
                topic=topic,
                char=_char(topic),
                villain=random.choice(_VILLAINS),
                ep=random.randint(1, 1200),
            )
            signals.append({
                "source": "reddit",
                "subreddit": _SUBREDDITS_MAP.get(topic, "anime"),
                "title": title,
                "score": int(random.gauss(800, 400)),
                "num_comments": int(random.gauss(120, 60)),
                "url": f"https://reddit.com/r/{_SUBREDDITS_MAP.get(topic, 'anime')}/mock",
                "matched_topics": [topic],
                "created_utc": _recent_time(),
                "collected_at": _now(),
            })

        # YouTube signals
        n_yt = int(random.randint(3, 15) * heat)
        other_topics = [t for t in topics if t != topic]
        for _ in range(n_yt):
            tpl = random.choice(_YT_TEMPLATES)
            title = tpl.format(
                topic=topic,
                char=_char(topic),
                ep=random.randint(1, 1200),
                topic2=random.choice(other_topics) if other_topics else topic,
            )
            signals.append({
                "source": "youtube",
                "title": title,
                "channel": f"{random.choice(['AnimeExplained', 'Foxen', 'Tekking101', 'Chibi Reviews', 'RogersBase'])}",
                "video_id": f"mock_{random.randint(10000, 99999)}",
                "url": f"https://youtube.com/watch?v=mock_{random.randint(10000, 99999)}",
                "matched_topics": [topic],
                "published_at": _recent_time(),
                "collected_at": _now(),
            })

        # Google Trends signal
        latest = int(random.gauss(60, 25) * heat)
        avg = round(random.gauss(45, 15) * heat, 2)
        signals.append({
            "source": "google_trends",
            "topic": topic,
            "latest_score": max(0, min(100, latest)),
            "average_7d": max(0, avg),
            "matched_topics": [topic],
            "collected_at": _now(),
        })

    random.shuffle(signals)
    return signals
