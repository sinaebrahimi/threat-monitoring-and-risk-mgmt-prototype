# AI-Driven OSINT Threat Monitoring & Risk Assessment

A prototype system that automatically collects, processes, and prioritises open-source threat intelligence from The Guardian Open Platform, using NLP and a composite risk-scoring model.

Built as a technical assessment for a KTP (Knowledge Transfer Partnership) Associate role at the University of West London (Ref: COMP0092).

---

## What It Does

1. **Collects** news articles from The Guardian API using 15 threat-oriented search queries (ransomware, espionage, terrorism, disinformation, etc.)
2. **Preprocesses** article text — strips HTML, normalises whitespace, builds a weighted search field
3. **Extracts entities** — organisations, countries, persons using spaCy Named Entity Recognition
4. **Classifies threats** into 5 categories using a keyword taxonomy + zero-shot NLI model
5. **Scores risk** using a composite formula combining keyword density, sentiment negativity, recency, and entity specificity
6. **Reports** — produces a ranked threat list with severity labels (Low / Medium / High / Critical), exported as CSV and JSON

The full pipeline runs in a single Jupyter notebook: [`notebooks/threat_monitoring.ipynb`](notebooks/threat_monitoring.ipynb)

---

## Project Structure

```
threat-monitoring-and-risk-mgmt-prototype/
│
├── .env                        # Guardian API key (create this — see Setup)
├── .env.example                # Template for .env
├── requirements.txt            # All Python dependencies
├── setup.ps1                   # One-command environment setup (Windows)
│
├── src/                        # Pipeline modules (importable package)
│   ├── config.py               # API settings, threat taxonomy, scoring weights
│   ├── collector.py            # Guardian API fetcher with pagination & dedup
│   ├── preprocessor.py         # HTML stripping, text cleaning
│   ├── ner.py                  # spaCy NER — extracts ORG, GPE, PERSON entities
│   ├── classifier.py           # Keyword classifier + zero-shot NLI (top-50)
│   ├── risk_scorer.py          # Composite risk score formula (0–10 scale)
│   └── reporter.py             # Ranked threat report, CSV/JSON export
│
├── notebooks/
│   └── threat_monitoring.ipynb # Main end-to-end notebook (run this)
│
├── data/                       # Auto-created on first run
│   ├── raw/                    # guardian_raw.json — cached API responses
│   └── processed/              # articles_clean.csv — preprocessed corpus
│
├── outputs/                    # Auto-created on first run
│   ├── threat_report.csv       # Ranked threat report
│   ├── threat_report.json
│   └── *.png                   # Visualisation charts
│
└── report/                     # IEEE one-column LaTeX report
    ├── main.tex                # Full written report
    ├── main.bib                # Bibliography (OSINT/NLP references)
    └── IEEEtran_modified.bst   # IEEE bibliography style
```

---

## Requirements

- Python **3.10** or 3.11
- Windows (PowerShell) — the setup script uses `.ps1`; Linux/macOS users can run the equivalent `pip install` commands manually
- Internet connection for first run (API fetch + model download ~100 MB total)
- No GPU required — everything runs on CPU

---

## Setup

### 1. Clone / open the project

```powershell
cd "path\to\threat-monitoring-and-risk-mgmt-prototype"
```

### 2. Create your `.env` file

```powershell
Copy-Item .env.example .env
# Then open .env and paste your Guardian API key:
# GUARDIAN_API_KEY=your-key-here
```

> Get a free key at https://open-platform.theguardian.com/access/

### 3. Run the setup script

```powershell
.\setup.ps1
```

This will:
- Create a `venv/` virtual environment
- Install all packages from `requirements.txt`
- Download the spaCy English model (`en_core_web_sm`)
- Download NLTK data (VADER lexicon, punkt tokeniser, stopwords)

> **Note:** If the spaCy model download step fails (known issue with some versions), run this manually:
> ```powershell
> .\venv\Scripts\python.exe -m pip install "https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.7.1/en_core_web_sm-3.7.1-py3-none-any.whl"
> ```

### 4. Activate the environment

```powershell
.\venv\Scripts\Activate.ps1
```

---

## Running the Notebook

```powershell
jupyter notebook notebooks/threat_monitoring.ipynb
```

Then in the browser: **Kernel → Restart & Run All**

The notebook runs the full pipeline end-to-end:

| Section | What happens |
|---------|-------------|
| 0 — Setup | Imports and config check |
| 1 — Data Collection | Fetches from Guardian API (or loads cache if already fetched) |
| 2 — Preprocessing | Strips HTML, cleans text |
| 3 — NER | Extracts named entities, shows top organisations |
| 4 — Classification | Keyword + zero-shot threat categorisation |
| 5 — Risk Scoring | Computes composite score for every article |
| 6 — Visualisations | Charts saved to `outputs/` |
| 7 — Threat Report | Ranked table + intelligence briefs |
| 8 — Discussion | Limitations, ethics, scalability notes |

**First run:** ~3–5 minutes (API fetch + zero-shot model download)  
**Subsequent runs:** ~1–2 minutes (loads cached JSON, model already cached)

---

## Outputs

After running the notebook, `outputs/` will contain:

| File | Description |
|------|-------------|
| `threat_report.csv` | All articles ranked by risk score (0–10) with severity label, category, entities, URL |
| `threat_report.json` | Same data in JSON format |
| `threat_category_dist.png` | Bar chart — articles per threat category |
| `risk_score_dist.png` | Histogram + severity pie chart |
| `risk_vs_sentiment.png` | Scatter plot — risk score vs sentiment negativity |
| `risk_by_category.png` | Box plot — score distribution per category |
| `entity_wordcloud.png` | Word cloud of all named entities |
| `articles_over_time.png` | Monthly article volume by category |
| `top_organisations.png` | Top 20 most-mentioned organisations |

---

## How the Risk Score Works

Each article receives a composite score in **[0, 10]**:

```
Risk = (0.35 × keyword_score
      + 0.25 × sentiment_score
      + 0.20 × recency_score
      + 0.20 × entity_score) × category_multiplier × 10
```

| Component | Description |
|-----------|-------------|
| `keyword_score` | Normalised density of threat keywords in article text |
| `sentiment_score` | VADER negativity — more negative news = higher risk signal |
| `recency_score` | Exponential decay; articles older than ~30 days score lower |
| `entity_score` | Normalised named entity count — more specific = more actionable |
| `category_multiplier` | Terrorism: 1.5 · Critical Infrastructure: 1.4 · Cyber: 1.3 · Geopolitical: 1.2 · Disinformation: 1.0 |

**Severity labels:**

| Score | Label |
|-------|-------|
| 0–3 | Low |
| 3–6 | Medium |
| 6–8 | High |
| 8–10 | Critical |

---

## Threat Categories

The system classifies articles into five categories using a built-in keyword taxonomy (editable in [`src/config.py`](src/config.py)):

- **Cyber** — ransomware, malware, phishing, DDoS, zero-day, data breach, APT ...
- **Geopolitical** — espionage, nation state, sanctions, military, NATO, intelligence service ...
- **Terrorism** — terrorism, extremism, bomb, radicalisation, domestic terrorism ...
- **Disinformation** — disinformation, propaganda, deepfake, influence operation, troll farm ...
- **Critical Infrastructure** — power grid, water supply, hospital attack, pipeline, SCADA, ICS ...

A zero-shot NLI classifier (`cross-encoder/nli-MiniLM2-L6-H768`, ~85 MB) is also run on the top-50 highest-scoring articles as a secondary ML-based check.

---

## Configuration

All tunable parameters are in [`src/config.py`](src/config.py):

| Parameter | Default | Effect |
|-----------|---------|--------|
| `LOOKBACK_DAYS` | 180 | How far back to collect articles |
| `MAX_PAGES` | 3 | Pages per query (50 results/page) |
| `THREAT_QUERIES` | 15 terms | Search terms sent to Guardian API |
| `THREAT_TAXONOMY` | 5 categories | Keyword lists for classification |
| `WEIGHT_KEYWORD` | 0.35 | Scoring weight (all 4 weights must sum to 1.0) |
| `RECENCY_HALF_LIFE_DAYS` | 30 | Days until recency score halves |
| `ZS_SAMPLE_SIZE` (classifier.py) | 50 | Articles sent to zero-shot model |

---

## Compiling the LaTeX Report

```powershell
cd report
pdflatex "main.tex"
pdflatex "main.tex"   # run twice for correct citation numbering
```

Requires a LaTeX installation (e.g. MiKTeX on Windows). The report uses the `IEEEtran` document class with TikZ for the architecture diagram.

---

## Limitations

- **Single source:** Only The Guardian; misses non-English and specialist technical sources
- **English only:** No multilingual NLP
- **Vocabulary-bound classifier:** Novel attack names not in the taxonomy are missed
- **Hand-tuned weights:** Scoring weights are not data-driven; no labelled ground truth
- **Prototype scope:** No database, no scheduling, no live dashboard

See Section 8 of the notebook and Section VII of the report for a full discussion.

---

## Author

Sina Ebrahimi  
University of West London / B3 Secure — KTP Associate Technical Assessment, 2026
