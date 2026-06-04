"""
Two-stage threat classifier:
  Stage 1 — Keyword matching (fast, all articles, fully explainable)
  Stage 2 — Zero-shot NLI classification (sampled top articles, ML-based)
"""
import logging
import numpy as np
import pandas as pd
from tqdm import tqdm
from src.config import THREAT_TAXONOMY

log = logging.getLogger(__name__)

# Zero-shot model — small NLI cross-encoder (~85 MB, CPU-friendly)
ZS_MODEL = "cross-encoder/nli-MiniLM2-L6-H768"
ZS_SAMPLE_SIZE = 50  # apply zero-shot to top-N articles by keyword score

_zs_pipeline = None


def _get_zs_pipeline():
    global _zs_pipeline
    if _zs_pipeline is None:
        from transformers import pipeline
        log.info(f"Loading zero-shot model: {ZS_MODEL} ...")
        _zs_pipeline = pipeline(
            "zero-shot-classification",
            model=ZS_MODEL,
            device=-1,  # CPU
        )
    return _zs_pipeline


# ── Stage 1: Keyword classifier ───────────────────────────────────────────────

def keyword_classify(text: str, taxonomy: dict = None) -> tuple[str, float]:
    """
    Count keyword hits per category in lowercased text.
    Returns (best_category, normalised_score ∈ [0, 1]).
    Score = keyword_hits / (text_word_count + 1), normalised across categories.
    """
    if taxonomy is None:
        taxonomy = THREAT_TAXONOMY

    if not text:
        return "Unknown", 0.0

    lower = text.lower()
    word_count = max(len(lower.split()), 1)

    scores = {}
    for category, keywords in taxonomy.items():
        hits = sum(lower.count(kw) for kw in keywords)
        scores[category] = hits / word_count

    best = max(scores, key=scores.get)
    best_score = scores[best]

    # Normalise: scale so max possible ≈ 1
    # (rough normalisation: clip at 0.05 raw density → score of 1.0)
    normalised = min(best_score / 0.05, 1.0)

    if best_score == 0:
        return "Unknown", 0.0
    return best, round(normalised, 4)


def keyword_scores_all(text: str, taxonomy: dict = None) -> dict[str, float]:
    """Return raw keyword density score for every category (useful for radar charts)."""
    if taxonomy is None:
        taxonomy = THREAT_TAXONOMY
    if not text:
        return {cat: 0.0 for cat in taxonomy}
    lower = text.lower()
    word_count = max(len(lower.split()), 1)
    return {cat: sum(lower.count(kw) for kw in kws) / word_count
            for cat, kws in taxonomy.items()}


# ── Stage 2: Zero-shot NLI classifier ────────────────────────────────────────

def zero_shot_classify(text: str, candidate_labels: list[str]) -> tuple[str, float]:
    """
    Classify text into one of candidate_labels using a zero-shot NLI model.
    Returns (top_label, confidence ∈ [0, 1]).
    Uses first 512 chars to respect token limits.
    """
    pipe = _get_zs_pipeline()
    result = pipe(text[:512], candidate_labels=candidate_labels, multi_label=False)
    return result["labels"][0], round(result["scores"][0], 4)


# ── Combined enrichment ───────────────────────────────────────────────────────

def classify_dataframe(df: pd.DataFrame, run_zero_shot: bool = True) -> pd.DataFrame:
    """
    Apply keyword classification to all articles.
    Apply zero-shot classification to the top ZS_SAMPLE_SIZE by keyword_score.

    Adds columns:
        threat_category, keyword_score,
        zs_category (where available, else NaN), zs_confidence
    """
    df = df.copy()
    categories = list(THREAT_TAXONOMY.keys())

    log.info("Stage 1: Keyword classification ...")
    results = [keyword_classify(t) for t in tqdm(df["search_text"], desc="Keyword classify")]
    df["threat_category"] = [r[0] for r in results]
    df["keyword_score"] = [r[1] for r in results]

    # All-category scores (for visualisation)
    all_scores = [keyword_scores_all(t) for t in df["search_text"]]
    for cat in categories:
        df[f"score_{cat.lower().replace(' ', '_')}"] = [s[cat] for s in all_scores]

    df["zs_category"] = np.nan
    df["zs_confidence"] = np.nan

    if run_zero_shot:
        log.info(f"Stage 2: Zero-shot classification on top-{ZS_SAMPLE_SIZE} articles ...")
        # Sort by keyword_score descending, take top sample
        top_idx = df.nlargest(ZS_SAMPLE_SIZE, "keyword_score").index
        for idx in tqdm(top_idx, desc="Zero-shot classify"):
            text = df.at[idx, "search_text"]
            try:
                zs_cat, zs_conf = zero_shot_classify(text, categories)
                df.at[idx, "zs_category"] = zs_cat
                df.at[idx, "zs_confidence"] = zs_conf
            except Exception as e:
                log.warning(f"Zero-shot failed for idx {idx}: {e}")
    else:
        log.info("Skipping zero-shot classification (run_zero_shot=False).")

    return df
