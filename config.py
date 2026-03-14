"""Central configuration for the Fandom Intelligence Graph."""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Paths
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
GRAPH_OUTPUT = DATA_DIR / "attention_graph.html"

# Reddit
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID", "")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET", "")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT", "fandom-intelligence-bot/1.0")

# YouTube
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")

# Mock mode (no API keys needed)
USE_MOCK_DATA = os.getenv("USE_MOCK_DATA", "true").lower() == "true"

# Storage / Database
MONGODB_URI = os.getenv("MONGODB_URI", "")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "fandom_intel")

# Tracking targets
TRACKED_TOPICS = [
    "One Piece",
    "Jujutsu Kaisen",
    "Solo Leveling",
    "Demon Slayer",
    "Attack on Titan",
    "Dragon Ball",
    "Naruto",
    "My Hero Academia",
    "Chainsaw Man",
    "Spy x Family",
]

# Subreddits to monitor
SUBREDDITS = [
    "anime",
    "OnePiece",
    "JuJutsuKaisen",
    "sololeveling",
    "KimetsuNoYaiba",
    "ShingekiNoKyojin",
    "Dragonballsuper",
    "Naruto",
    "BokuNoHeroAcademia",
    "ChainsawMan",
]

# Attention score weights
WEIGHTS = {
    "reddit": 0.35,
    "youtube": 0.30,
    "google_trends": 0.20,
    "news": 0.15,
}

# Trend explosion threshold (% increase over baseline to flag as "exploding")
EXPLOSION_THRESHOLD = 2.0  # 200% increase
