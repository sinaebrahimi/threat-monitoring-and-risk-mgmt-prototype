# CLAUDE.md — Project Context for AI Agents

This file gives an AI agent everything it needs to understand, extend, or debug this project without reading every source file first.

---

## What This Project Is

A **prototype** AI-driven OSINT (Open-Source Intelligence) threat monitoring and risk assessment system, built as a KTP Associate technical assessment for the University of Wolverhampton. The brief explicitly states it does **not** need to be production-ready — focus is on demonstrating technical reasoning, pipeline design, and clear communication of design decisions.

**The system answers:** *"Which publicly reported news articles represent the most urgent security threats, and why?"*

---

## Data Source

**The Guardian Open Platform API**
- Base URL: `https://content.guardianapis.com`
- API key stored in `.env` as `GUARDIAN_API_KEY`
- Developer tier: free, full article body text, max 50 results/page
- Docs: https://open-platform.theguardian.com/documentation/

The collector queries 15 threat-oriented search terms (ransomware, espionage, terrorism, etc.) across the past 6 months, deduplicates by article ID, and stores raw JSON at `data/raw/guardian_raw.json`. Subsequent runs reload from cache — no re-fetching needed.

---

## Five-Stage Pipeline

```
Guardian API → Preprocessing → NER → Classification → Risk Scoring → Threat Report
```

| Stage | Module | Input → Output |
|-------|--------|---------------|
| 1. Ingest | `src/collector.py` | API → `data/raw/guardian_raw.json` + DataFrame |
| 2. Preprocess | `src/preprocessor.py` | HTML body → clean text, `search_text` field |
| 3. NER | `src/ner.py` | text → ORG / GPE / PERSON entity columns |
| 4. Classify | `src/classifier.py` | text → `threat_category`, `keyword_score`, `zs_category` |
| 5. Score | `src/risk_scorer.py` | features → `risk_score` (0–10), `severity_label` |
| 6. Report | `src/reporter.py` | scored DataFrame → CSV + JSON + printed summary |

---

## Module Reference

### `src/config.py`
Central configuration. **Edit this to change behaviour without touching other files.**
- `GUARDIAN_API_KEY` — loaded from `.env` via `python-dotenv`
- `THREAT_QUERIES` — 15 search terms sent to the API
- `THREAT_TAXONOMY` — dict mapping 5 categories → keyword lists:
  - `"Cyber"`, `"Geopolitical"`, `"Terrorism"`, `"Disinformation"`, `"Critical Infrastructure"`
- `SEVERITY_BASE` — per-category risk multiplier (Terrorism=1.5, Cyber=1.3, …)
- `WEIGHT_*` — scoring weights (must sum to 1.0): keyword=0.35, sentiment=0.25, recency=0.20, entity=0.20
- `RECENCY_HALF_LIFE_DAYS = 30`
- `DATE_FROM` — auto-computed as 180 days ago; `DATE_TO` — today

### `src/collector.py`
- `GuardianCollector` class; call `collect_threat_corpus()` to fetch everything
- `GuardianCollector.load_raw(path)` — static method to reload from JSON without API call
- Paginates up to `MAX_PAGES=3` per query (50×3 = 150 articles/term max)
- 0.25 s sleep between requests to respect rate limits
- Output columns: `id, title, section, section_name, published, url, byline, standfirst, body_html, wordcount, query_hits`

### `src/preprocessor.py`
- `strip_html(html)` — BeautifulSoup + lxml parser
- `clean_text(text)` — collapse whitespace, drop control chars
- `preprocess_dataframe(df)` — adds `body_clean`, `title_clean`, `standfirst_clean`, `search_text`
- `search_text` = `title×3 + standfirst + body` (title repeated to upweight classification)
- Articles with body < 50 chars are dropped (gallery/video-only content)
- Saves to `data/processed/articles_clean.csv`

### `src/ner.py`
- Uses `spacy en_core_web_sm` (12 MB, CPU-only)
- Only processes first 5000 chars per article for speed
- Entity types: `ORG, GPE, PERSON, EVENT, FAC, NORP, LOC`
- Output columns: `entities_org`, `entities_gpe`, `entities_person`, `entities_event`, `entities_norp`, `entity_count`
- Entities stored as pipe-delimited strings: `"Google|NSA|GCHQ"`
- `entity_count` is used as a risk signal — more named actors = more specific threat

### `src/classifier.py`
Two-stage approach:

**Stage 1 — Keyword classifier (all articles, fast)**
- `keyword_classify(text)` → `(category, normalised_score)`
- Score = keyword hit density / 0.05, clipped to [0,1]
- Returns `"Unknown"` with score 0.0 if no keywords match

**Stage 2 — Zero-shot NLI (top-50 by keyword score only)**
- Model: `cross-encoder/nli-MiniLM2-L6-H768` (~85 MB, CPU-friendly, ~2 s/article)
- Downloaded from HuggingFace on first run, cached afterwards
- `ZS_SAMPLE_SIZE = 50` — intentional limit for prototype runtime
- Output: `zs_category`, `zs_confidence` (NaN for articles not in top-50)
- `classify_dataframe(df, run_zero_shot=True/False)` — set `False` to skip Stage 2

Also adds per-category raw score columns: `score_cyber`, `score_geopolitical`, etc. (useful for radar charts).

### `src/risk_scorer.py`
**Composite score formula:**
```
Risk = (0.35×S_keyword + 0.25×S_sentiment + 0.20×S_recency + 0.20×S_entity)
       × severity_base[category] × 10
```
- `S_sentiment` = VADER negativity = (1 − compound) / 2; more negative → higher risk
- `S_recency` = exp(−ln2 × days_old / 30); halves every 30 days
- `S_entity` = entity_count / corpus_max, clipped to [0,1]
- Final score clipped to [0, 10]
- Severity labels: Low [0,3), Medium [3,6), High [6,8), Critical [8,10]
- VADER is applied to `title + standfirst` only (faster, captures headline tone)

### `src/reporter.py`
- `generate_threat_report(df)` → sorted DataFrame, 1-based rank index
- `export_report(df)` → saves `outputs/threat_report.csv` + `outputs/threat_report.json`
- `print_summary(df, top_n=10)` → formatted terminal output with severity bars
- `intelligence_briefs(df, top_per_category=2)` → dict of per-category top articles

---

## Main Deliverable: `notebooks/threat_monitoring.ipynb`

Run top-to-bottom with `Kernel → Restart & Run All`. Sections:

| Section | Key output |
|---------|-----------|
| 0. Setup | Import check, print config |
| 1. Data Collection | Load or fetch corpus, show stats |
| 2. Preprocessing | Before/after HTML strip example |
| 3. NER | Entity examples, top-20 organisations bar chart |
| 4. Classification | Category distribution bar chart, keyword vs zero-shot agreement |
| 5. Risk Scoring | Score stats, severity distribution |
| 6. Visualisations | Histogram, pie chart, scatter, word cloud, time series |
| 7. Threat Report | Colour-coded top-15 table, intelligence briefs |
| 8. Discussion | Markdown cells: limitations, ethics, scalability table |

Saved plots: `outputs/top_organisations.png`, `threat_category_dist.png`, `risk_score_dist.png`, `risk_vs_sentiment.png`, `risk_by_category.png`, `entity_wordcloud.png`, `articles_over_time.png`

---

## Report: `report/main.tex`

IEEE one-column format: `\documentclass[12pt,lettersize,journal,onecolumn]{IEEEtran}` with `\doublespacing`.

Sections: Abstract → Introduction → Related Work → System Architecture (TikZ pipeline diagram) → Data Collection → AI & Analytical Methods → Risk Assessment Framework → Results → Key Considerations → Conclusion & Future Work → References

Bibliography: `report/main.bib` — 14 OSINT/NLP/security references (spaCy, VADER, BERT, MITRE ATT&CK, Guardian API, OpenCTI, MISP, CVSS, etc.)

Compile: `cd report && pdflatex main.tex && pdflatex main.tex` (twice for citation numbering).

---

## Environment

- **Python 3.10.11**, Windows 11, PowerShell
- **venv** at `venv/` — activate with `.\venv\Scripts\Activate.ps1`
- All packages installed; no GPU required (torch CPU build)
- spaCy model: `en_core_web_sm-3.7.1` installed as a package
- NLTK data: `vader_lexicon`, `punkt`, `stopwords` downloaded

Key packages: `spacy==3.7.4`, `transformers==4.40.1`, `torch==2.2.2+cpu`, `pandas==2.2.2`, `nltk==3.8.1`, `scikit-learn==1.4.2`, `wordcloud==1.9.3`, `jupyter`, `ipykernel`

---

## Key Design Decisions (important for understanding trade-offs)

1. **Single source (Guardian only)** — simplicity for prototype; production would aggregate Reuters, AP, CISA, CVE feeds
2. **Keyword-first, zero-shot second** — keyword classifier is fast and fully explainable (essential for report discussion); zero-shot demonstrates ML capability on a sample without requiring GPU or long runtime
3. **VADER over transformer sentiment** — runs in milliseconds, no model download; good enough for news headlines
4. **No database** — raw JSON + CSV adequate for prototype; report explicitly discusses SQLite/vector DB as production next step
5. **spaCy small model** — 12 MB, CPU-only, F1≈0.85 on OntoNotes; sufficient for ORG/GPE NER
6. **Cache-first data collection** — if `data/raw/guardian_raw.json` exists, reload without re-fetching API; avoids hitting rate limits during iterative notebook development
7. **Recency half-life = 30 days** — configurable in `config.py`; shorter = older articles penalised more

---

## What to Change for Common Tasks

| Task | Where to edit |
|------|--------------|
| Add a new threat keyword | `src/config.py` → `THREAT_TAXONOMY` |
| Add a new search query | `src/config.py` → `THREAT_QUERIES` |
| Change scoring weights | `src/config.py` → `WEIGHT_*` constants |
| Change date window | `src/config.py` → `LOOKBACK_DAYS` |
| Run zero-shot on more articles | `src/classifier.py` → `ZS_SAMPLE_SIZE` |
| Add a new data source | Create a new collector class alongside `GuardianCollector` |
| Change report columns | `src/reporter.py` → `REPORT_COLUMNS` list |
| Add a visualisation | Notebook section 6 |

---

## Constraints and Gotchas

- `.env` file is gitignored — never commit the API key
- `data/` and `outputs/` directories are gitignored (auto-created at runtime)
- The spaCy `python -m spacy download` command has a bug with this version — install the model wheel directly: `pip install https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.7.1/en_core_web_sm-3.7.1-py3-none-any.whl`
- Zero-shot model downloads ~85 MB on first run (cached in HuggingFace `~/.cache/`)
- `publish` column is timezone-aware UTC — always use `pd.Timestamp` with `tzinfo` when comparing
- The notebook path resolution (`ROOT = pathlib.Path().resolve().parent`) assumes the notebook is in `notebooks/` and `src/` is one level up at the project root
