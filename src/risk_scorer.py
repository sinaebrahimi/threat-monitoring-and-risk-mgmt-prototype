"""
Composite risk scoring for each article.

Score = (w_kw × S_keyword + w_sent × S_sentiment + w_rec × S_recency + w_ent × S_entity)
        × severity_base[category]

All component scores are normalised to [0, 1] before weighting.
Final score is scaled to [0, 10].
"""
import math
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from src.config import (
    SEVERITY_BASE, SEVERITY_LABELS,
    WEIGHT_KEYWORD, WEIGHT_SENTIMENT, WEIGHT_RECENCY, WEIGHT_ENTITIES,
    RECENCY_HALF_LIFE_DAYS,
)

log = logging.getLogger(__name__)

_vader = None


def _get_vader():
    global _vader
    if _vader is None:
        _vader = SentimentIntensityAnalyzer()
    return _vader


# ── Component scorers ─────────────────────────────────────────────────────────

def sentiment_score(text: str) -> float:
    """
    VADER compound score → threat sentiment score in [0, 1].
    Negative compound → higher risk (negative news = potential threat signal).
    Maps: compound ∈ [-1, 1] → score ∈ [0, 1]  via  (1 - compound) / 2.
    """
    if not text:
        return 0.5
    sia = _get_vader()
    compound = sia.polarity_scores(text[:2000])["compound"]
    return round((1.0 - compound) / 2.0, 4)


def recency_score(published_dt, reference_dt=None) -> float:
    """
    Exponential decay: articles published today score 1.0,
    halving every RECENCY_HALF_LIFE_DAYS days.
    Returns score ∈ [0, 1].
    """
    if reference_dt is None:
        reference_dt = datetime.now(timezone.utc)
    if pd.isna(published_dt):
        return 0.0
    # Ensure timezone-aware
    if published_dt.tzinfo is None:
        published_dt = published_dt.replace(tzinfo=timezone.utc)
    days_old = (reference_dt - published_dt).total_seconds() / 86400.0
    return round(math.exp(-math.log(2) * days_old / RECENCY_HALF_LIFE_DAYS), 4)


def entity_score(entity_count: int, max_count: int = 30) -> float:
    """
    More named entities → more specific threat intelligence → higher score.
    Clipped and normalised to [0, 1].
    """
    return round(min(entity_count / max_count, 1.0), 4)


# ── Composite scorer ──────────────────────────────────────────────────────────

def compute_risk_score(
    keyword_score: float,
    sent_score: float,
    rec_score: float,
    ent_score: float,
    category: str,
) -> float:
    """Compute composite risk score in [0, 10]."""
    base = (
        WEIGHT_KEYWORD * keyword_score
        + WEIGHT_SENTIMENT * sent_score
        + WEIGHT_RECENCY * rec_score
        + WEIGHT_ENTITIES * ent_score
    )
    multiplier = SEVERITY_BASE.get(category, SEVERITY_BASE["Unknown"])
    raw = base * multiplier * 10.0
    return round(min(max(raw, 0.0), 10.0), 3)


def severity_label(score: float) -> str:
    for (lo, hi), label in SEVERITY_LABELS.items():
        if lo <= score < hi:
            return label
    return "Critical" if score >= 8.0 else "Low"


# ── DataFrame enrichment ──────────────────────────────────────────────────────

def score_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute all component scores and the composite risk score for every article.
    Adds columns: sentiment_neg, recency_score, entity_score_norm,
                  risk_score, severity_label.
    """
    log.info("Computing risk scores ...")
    df = df.copy()

    now = datetime.now(timezone.utc)

    # Sentiment (use title + standfirst for speed; body for articles without standfirst)
    text_for_sentiment = (
        df["title_clean"].fillna("") + " " + df["standfirst_clean"].fillna("")
    )
    df["sentiment_neg"] = text_for_sentiment.apply(sentiment_score)

    # Recency
    df["recency_score_val"] = df["published"].apply(lambda d: recency_score(d, now))

    # Entity normalisation
    max_ent = df["entity_count"].max() if df["entity_count"].max() > 0 else 1
    df["entity_score_norm"] = df["entity_count"].apply(
        lambda c: entity_score(c, max_count=max_ent)
    )

    # Composite
    df["risk_score"] = df.apply(
        lambda row: compute_risk_score(
            keyword_score=row.get("keyword_score", 0.0),
            sent_score=row.get("sentiment_neg", 0.5),
            rec_score=row.get("recency_score_val", 0.5),
            ent_score=row.get("entity_score_norm", 0.0),
            category=row.get("threat_category", "Unknown"),
        ),
        axis=1,
    )

    df["severity_label"] = df["risk_score"].apply(severity_label)

    log.info(
        f"Risk scoring complete. "
        f"Mean={df['risk_score'].mean():.2f}, "
        f"Max={df['risk_score'].max():.2f}, "
        f"Severity counts:\n{df['severity_label'].value_counts().to_string()}"
    )
    return df
