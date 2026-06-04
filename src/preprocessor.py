"""
Text preprocessing: HTML stripping, cleaning, normalisation.
"""
import re
import logging
import pandas as pd
from bs4 import BeautifulSoup
from src.config import DATA_PROCESSED

log = logging.getLogger(__name__)


def strip_html(html: str) -> str:
    """Remove HTML tags and decode entities; return plain text."""
    if not html or not isinstance(html, str):
        return ""
    soup = BeautifulSoup(html, "lxml")
    return soup.get_text(separator=" ", strip=True)


def clean_text(text: str) -> str:
    """Normalise whitespace, remove non-printable characters."""
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text)          # collapse whitespace
    text = re.sub(r"[^\x20-\x7E -￿]", "", text)  # drop control chars
    return text.strip()


def make_search_text(row: pd.Series) -> str:
    """Concatenate title + standfirst + body for downstream NLP; title weighted 3×."""
    title = row.get("title_clean", "")
    standfirst = row.get("standfirst_clean", "")
    body = row.get("body_clean", "")
    return f"{title} {title} {title} {standfirst} {body}".strip()


def preprocess_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply all preprocessing steps to a raw Guardian DataFrame.
    Adds columns: body_clean, title_clean, standfirst_clean, search_text.
    Saves the result to data/processed/articles_clean.csv.
    """
    log.info(f"Preprocessing {len(df)} articles ...")
    df = df.copy()

    df["body_clean"] = df["body_html"].apply(strip_html).apply(clean_text)
    df["title_clean"] = df["title"].apply(clean_text)
    df["standfirst_clean"] = df["standfirst"].apply(strip_html).apply(clean_text)

    # Combined search text (title repeated for emphasis)
    df["search_text"] = df.apply(make_search_text, axis=1)

    # Drop articles with no usable text (rare; usually gallery-only content)
    before = len(df)
    df = df[df["body_clean"].str.len() > 50].reset_index(drop=True)
    log.info(f"Dropped {before - len(df)} articles with insufficient body text.")

    out = DATA_PROCESSED / "articles_clean.csv"
    df.to_csv(out, index=False)
    log.info(f"Saved preprocessed data to {out}")
    return df
