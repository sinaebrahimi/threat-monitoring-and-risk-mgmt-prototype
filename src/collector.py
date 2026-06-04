"""
Guardian Open Platform API collector.
Fetches articles matching threat-relevant queries and returns a unified DataFrame.
"""
import json
import time
import logging
import requests
import pandas as pd
from tqdm import tqdm
from src.config import (
    GUARDIAN_API_KEY, BASE_URL, DATE_FROM, DATE_TO,
    SHOW_FIELDS, PAGE_SIZE, MAX_PAGES,
    THREAT_QUERIES, DATA_RAW,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)


class GuardianCollector:
    """Fetches and deduplicates Guardian articles for a set of threat queries."""

    def __init__(self, api_key: str = GUARDIAN_API_KEY):
        if not api_key:
            raise ValueError("GUARDIAN_API_KEY is not set. Check your .env file.")
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "OSINT-Prototype/1.0"})

    def _fetch_page(self, query: str, page: int) -> dict:
        """Fetch a single page of results from /search."""
        params = {
            "q": query,
            "api-key": self.api_key,
            "from-date": DATE_FROM,
            "to-date": DATE_TO,
            "show-fields": SHOW_FIELDS,
            "page-size": PAGE_SIZE,
            "page": page,
            "order-by": "newest",
        }
        resp = self.session.get(f"{BASE_URL}/search", params=params, timeout=15)
        resp.raise_for_status()
        return resp.json()["response"]

    def fetch_articles(self, query: str, max_pages: int = MAX_PAGES) -> list[dict]:
        """Fetch up to max_pages pages for a single query, return list of article dicts."""
        articles = []
        try:
            first = self._fetch_page(query, page=1)
            total_pages = min(first.get("pages", 1), max_pages)
            articles.extend(first.get("results", []))

            for page in range(2, total_pages + 1):
                time.sleep(0.25)  # respect rate limits
                data = self._fetch_page(query, page=page)
                articles.extend(data.get("results", []))
        except requests.RequestException as e:
            log.warning(f"Query '{query}' failed: {e}")
        return articles

    def collect_threat_corpus(self, queries: list[str] = None) -> pd.DataFrame:
        """
        Run all threat queries, deduplicate by article id, return a DataFrame.
        Also saves raw JSON to data/raw/guardian_raw.json.
        """
        if queries is None:
            queries = THREAT_QUERIES

        all_articles: dict[str, dict] = {}  # id → article (for dedup)
        id_to_queries: dict[str, list[str]] = {}

        log.info(f"Fetching {len(queries)} queries from {DATE_FROM} to {DATE_TO} ...")
        for query in tqdm(queries, desc="Collecting articles"):
            results = self.fetch_articles(query)
            for art in results:
                art_id = art["id"]
                if art_id not in all_articles:
                    all_articles[art_id] = art
                    id_to_queries[art_id] = []
                id_to_queries[art_id].append(query)

        log.info(f"Collected {len(all_articles)} unique articles.")

        # Save raw
        raw_path = DATA_RAW / "guardian_raw.json"
        with open(raw_path, "w", encoding="utf-8") as f:
            json.dump(list(all_articles.values()), f, ensure_ascii=False, indent=2)
        log.info(f"Raw JSON saved to {raw_path}")

        return self._to_dataframe(all_articles, id_to_queries)

    @staticmethod
    def _to_dataframe(articles: dict, id_to_queries: dict) -> pd.DataFrame:
        """Flatten Guardian API response dicts into a tidy DataFrame."""
        rows = []
        for art_id, art in articles.items():
            fields = art.get("fields", {})
            rows.append({
                "id": art_id,
                "title": fields.get("headline") or art.get("webTitle", ""),
                "section": art.get("sectionId", ""),
                "section_name": art.get("sectionName", ""),
                "published": art.get("webPublicationDate", ""),
                "url": art.get("webUrl", ""),
                "byline": fields.get("byline", ""),
                "standfirst": fields.get("standfirst", ""),
                "body_html": fields.get("body", ""),
                "wordcount": int(fields.get("wordcount") or 0),
                "query_hits": "|".join(id_to_queries.get(art_id, [])),
            })
        df = pd.DataFrame(rows)
        df["published"] = pd.to_datetime(df["published"], utc=True, errors="coerce")
        df = df.sort_values("published", ascending=False).reset_index(drop=True)
        return df

    @staticmethod
    def load_raw(path=None) -> pd.DataFrame:
        """Reload a previously saved raw JSON without re-fetching the API."""
        if path is None:
            path = DATA_RAW / "guardian_raw.json"
        with open(path, "r", encoding="utf-8") as f:
            articles = json.load(f)
        dummy_collector = GuardianCollector.__new__(GuardianCollector)
        id_to_queries = {a["id"]: [] for a in articles}
        return GuardianCollector._to_dataframe({a["id"]: a for a in articles}, id_to_queries)
