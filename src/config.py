"""
Central configuration: API settings, threat taxonomy, scoring weights.
"""
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

# ── Guardian API ──────────────────────────────────────────────────────────────
GUARDIAN_API_KEY = os.getenv("GUARDIAN_API_KEY", "")
BASE_URL = "https://content.guardianapis.com"

# Fetch articles published in the last N days
LOOKBACK_DAYS = 180
DATE_FROM = (datetime.utcnow() - timedelta(days=LOOKBACK_DAYS)).strftime("%Y-%m-%d")
DATE_TO = datetime.utcnow().strftime("%Y-%m-%d")

# Fields to retrieve from the Guardian API
SHOW_FIELDS = "headline,standfirst,byline,body,wordcount,trailText"

# Number of results per API page (max 50 for developer tier)
PAGE_SIZE = 50

# Maximum pages to fetch per query (50 results × 3 pages = 150 articles max per term)
MAX_PAGES = 3

# Guardian sections most likely to contain threat-relevant content
TARGET_SECTIONS = [
    "technology",
    "world",
    "uk-news",
    "us-news",
    "politics",
    "business",
    "environment",
]

# Search queries to collect a diverse threat corpus
THREAT_QUERIES = [
    "cyberattack",
    "ransomware",
    "data breach",
    "malware",
    "espionage",
    "terrorism",
    "disinformation",
    "critical infrastructure attack",
    "phishing",
    "DDoS attack",
    "zero-day vulnerability",
    "nation state hacking",
    "cyber warfare",
    "information warfare",
    "supply chain attack",
]

# ── Threat Taxonomy ───────────────────────────────────────────────────────────
# Maps threat category → list of keywords to match (case-insensitive)
THREAT_TAXONOMY = {
    "Cyber": [
        "ransomware", "malware", "phishing", "ddos", "breach", "exploit",
        "zero-day", "botnet", "spyware", "trojan", "worm", "backdoor",
        "cybercrime", "hacker", "hack", "cyberattack", "cyber attack",
        "data leak", "credential", "vulnerability", "cve", "patch",
        "supply chain attack", "apt", "advanced persistent threat",
    ],
    "Geopolitical": [
        "espionage", "nation state", "sanctions", "intelligence agency",
        "military operation", "nato", "foreign interference", "covert",
        "spy", "intelligence service", "fsb", "gru", "mss", "gchq",
        "cyber warfare", "information warfare", "hybrid warfare",
    ],
    "Terrorism": [
        "terrorism", "terrorist", "extremism", "extremist", "attack",
        "bomb", "explosive", "isis", "isil", "al-qaeda", "jihad",
        "radicalisation", "right-wing extremism", "domestic terrorism",
    ],
    "Disinformation": [
        "disinformation", "misinformation", "propaganda", "fake news",
        "influence operation", "deepfake", "bot network", "troll farm",
        "election interference", "narrative manipulation", "social media manipulation",
    ],
    "Critical Infrastructure": [
        "power grid", "water supply", "hospital attack", "pipeline",
        "satellite", "energy grid", "nuclear", "transport system",
        "financial system", "stock exchange", "smart city", "ics", "scada",
        "operational technology", "ot security",
    ],
}

# Base severity multiplier per category (1.0 = neutral, higher = more severe by nature)
SEVERITY_BASE = {
    "Cyber": 1.3,
    "Geopolitical": 1.2,
    "Terrorism": 1.5,
    "Disinformation": 1.0,
    "Critical Infrastructure": 1.4,
    "Unknown": 0.8,
}

# ── Risk Score Thresholds ─────────────────────────────────────────────────────
SEVERITY_LABELS = {
    (0.0, 3.0): "Low",
    (3.0, 6.0): "Medium",
    (6.0, 8.0): "High",
    (8.0, 10.0): "Critical",
}

# ── Scoring Weights (must sum to 1.0) ────────────────────────────────────────
WEIGHT_KEYWORD = 0.35
WEIGHT_SENTIMENT = 0.25
WEIGHT_RECENCY = 0.20
WEIGHT_ENTITIES = 0.20

# Recency decay half-life in days (articles older than this lose half their recency score)
RECENCY_HALF_LIFE_DAYS = 30

# ── Paths ─────────────────────────────────────────────────────────────────────
import pathlib
ROOT = pathlib.Path(__file__).parent.parent
DATA_RAW = ROOT / "data" / "raw"
DATA_PROCESSED = ROOT / "data" / "processed"
OUTPUTS = ROOT / "outputs"

DATA_RAW.mkdir(parents=True, exist_ok=True)
DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
OUTPUTS.mkdir(parents=True, exist_ok=True)
