"""
Named Entity Recognition using spaCy.
Extracts organisations, geopolitical entities, persons, and events
from article text to enrich the threat intelligence dataset.
"""
import logging
import pandas as pd
from tqdm import tqdm

log = logging.getLogger(__name__)

# Lazy-load spaCy model to avoid slow import at module level
_nlp = None


def _get_nlp():
    global _nlp
    if _nlp is None:
        import spacy
        log.info("Loading spaCy model en_core_web_sm ...")
        _nlp = spacy.load("en_core_web_sm", disable=["parser", "lemmatizer"])
    return _nlp


ENTITY_LABELS = {"ORG", "GPE", "PERSON", "EVENT", "FAC", "NORP", "LOC"}


def extract_entities(text: str) -> dict:
    """
    Run spaCy NER on text, return dict mapping label → deduplicated list of entity strings.
    Only processes first 5000 chars to keep runtime manageable.
    """
    if not text or not isinstance(text, str):
        return {lbl: [] for lbl in ENTITY_LABELS}

    nlp = _get_nlp()
    doc = nlp(text[:5000])

    result = {lbl: [] for lbl in ENTITY_LABELS}
    seen = set()
    for ent in doc.ents:
        if ent.label_ in ENTITY_LABELS:
            key = (ent.label_, ent.text.strip())
            if key not in seen:
                seen.add(key)
                result[ent.label_].append(ent.text.strip())
    return result


def entity_count(entities: dict) -> int:
    """Total number of distinct named entities across all labels."""
    return sum(len(v) for v in entities.values())


def enrich_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply NER to every article's search_text.
    Adds columns:
        entities_org, entities_gpe, entities_person,
        entities_event, entity_count
    """
    log.info(f"Running NER on {len(df)} articles ...")
    df = df.copy()

    ents_list = []
    for text in tqdm(df["search_text"], desc="NER"):
        ents_list.append(extract_entities(text))

    df["entities_org"] = ["|".join(e.get("ORG", [])) for e in ents_list]
    df["entities_gpe"] = ["|".join(e.get("GPE", []) + e.get("LOC", [])) for e in ents_list]
    df["entities_person"] = ["|".join(e.get("PERSON", [])) for e in ents_list]
    df["entities_event"] = ["|".join(e.get("EVENT", [])) for e in ents_list]
    df["entities_norp"] = ["|".join(e.get("NORP", [])) for e in ents_list]
    df["entity_count"] = [entity_count(e) for e in ents_list]

    log.info(f"NER complete. Avg entity count: {df['entity_count'].mean():.1f}")
    return df
