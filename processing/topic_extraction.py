"""
Topic & entity extraction pipeline.

Extracts anime names, characters, studios, and platforms from raw signal text.
Works in two modes:
  1. Keyword matching 
  2. spaCy NER + keyword hybrid (if spaCy is installed)
"""

from __future__ import annotations
import re
import logging
from typing import Any

log = logging.getLogger(__name__)

# ── Known entity dictionaries ────────────────────────────────────────────────

ANIME_ALIASES: dict[str, list[str]] = {
    "One Piece": ["one piece", "onepiece", "op", "luffy", "zoro", "sanji", "nami",
                   "shanks", "kaido", "kizaru", "gear 5", "gear fifth", "straw hat"],
    "Jujutsu Kaisen": ["jujutsu kaisen", "jjk", "gojo", "sukuna", "yuji", "megumi",
                        "todo", "cursed energy"],
    "Solo Leveling": ["solo leveling", "sung jin-woo", "jinwoo", "igris", "shadow army"],
    "Demon Slayer": ["demon slayer", "kimetsu no yaiba", "tanjiro", "nezuko",
                      "muzan", "rengoku", "akaza", "hashira"],
    "Attack on Titan": ["attack on titan", "aot", "shingeki", "eren", "mikasa",
                         "levi", "armin", "titan", "rumbling"],
    "Dragon Ball": ["dragon ball", "dragonball", "dbz", "dbs", "goku", "vegeta",
                     "gohan", "frieza", "beerus", "ultra instinct"],
    "Naruto": ["naruto", "sasuke", "kakashi", "itachi", "madara", "hokage",
               "boruto", "rasengan", "sharingan"],
    "My Hero Academia": ["my hero academia", "mha", "boku no hero", "deku",
                          "bakugo", "all might", "todoroki", "one for all"],
    "Chainsaw Man": ["chainsaw man", "csm", "denji", "makima", "power", "aki",
                      "devil hunter"],
    "Spy x Family": ["spy x family", "spy family", "anya", "loid", "yor", "bond",
                      "forger"],
}

CHARACTER_TO_ANIME: dict[str, str] = {}
for anime, aliases in ANIME_ALIASES.items():
    for alias in aliases:
        CHARACTER_TO_ANIME[alias.lower()] = anime

PLATFORMS = ["crunchyroll", "netflix", "funimation", "hulu", "amazon prime",
             "disney+", "hidive", "youtube", "reddit", "twitter", "myanimelist",
             "anilist"]

STUDIOS = ["toei animation", "mappa", "ufotable", "wit studio", "bones",
           "a-1 pictures", "cloverworks", "madhouse", "pierrot", "trigger"]


# ── Extraction functions ─────────────────────────────────────────────────────

def extract_entities(text: str) -> dict[str, list[str]]:
    """Extract anime, character, platform, and studio entities from text."""
    text_lower = text.lower()
    entities: dict[str, set[str]] = {
        "anime": set(),
        "characters": set(),
        "platforms": set(),
        "studios": set(),
    }

    # Match anime titles and character aliases
    for anime, aliases in ANIME_ALIASES.items():
        for alias in aliases:
            if alias in text_lower:
                entities["anime"].add(anime)
                # If the alias is a character name (not the anime title itself)
                if alias.lower() != anime.lower() and len(alias) > 2:
                    entities["characters"].add(alias.title())

    # Match platforms
    for platform in PLATFORMS:
        if platform in text_lower:
            entities["platforms"].add(platform.title())

    # Match studios
    for studio in STUDIOS:
        if studio in text_lower:
            entities["studios"].add(studio.title())

    return {k: sorted(v) for k, v in entities.items()}


def enrich_signal(signal: dict[str, Any]) -> dict[str, Any]:
    """Add extracted entities to a signal dict."""
    text = signal.get("title", "") + " " + signal.get("topic", "")
    entities = extract_entities(text)
    signal["entities"] = entities

    # Make sure matched_topics is populated
    if not signal.get("matched_topics") and entities["anime"]:
        signal["matched_topics"] = entities["anime"]

    return signal


def enrich_all(signals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Run entity extraction on every signal."""
    enriched = [enrich_signal(s) for s in signals]
    total_entities = sum(
        len(e) for s in enriched for e in s.get("entities", {}).values()
    )
    log.info("Extracted %d entities from %d signals", total_entities, len(enriched))
    return enriched
