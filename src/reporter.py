"""
Threat report generation and export.
Produces a ranked DataFrame and exports to CSV/JSON.
"""
import json
import logging
import textwrap
import pandas as pd
from src.config import OUTPUTS, THREAT_TAXONOMY

log = logging.getLogger(__name__)

REPORT_COLUMNS = [
    "title", "published", "section_name", "threat_category",
    "severity_label", "risk_score", "keyword_score",
    "entities_org", "entities_gpe", "url",
]


def generate_threat_report(df: pd.DataFrame) -> pd.DataFrame:
    """Return a sorted, trimmed DataFrame suitable for presenting as the threat report."""
    report = (
        df[REPORT_COLUMNS]
        .copy()
        .sort_values("risk_score", ascending=False)
        .reset_index(drop=True)
    )
    report.index = report.index + 1  # 1-based rank
    report.index.name = "rank"
    return report


def export_report(df: pd.DataFrame, output_dir=None) -> tuple[str, str]:
    """
    Save the threat report as CSV and JSON.
    Returns (csv_path, json_path).
    """
    if output_dir is None:
        output_dir = OUTPUTS

    report = generate_threat_report(df)

    csv_path = output_dir / "threat_report.csv"
    json_path = output_dir / "threat_report.json"

    report.to_csv(csv_path)
    report.reset_index().to_json(json_path, orient="records", indent=2, date_format="iso")

    log.info(f"Report saved: {csv_path}")
    log.info(f"Report saved: {json_path}")
    return str(csv_path), str(json_path)


def print_summary(df: pd.DataFrame, top_n: int = 10) -> None:
    """Print a formatted top-N threat summary to stdout."""
    report = generate_threat_report(df).head(top_n)

    print("\n" + "=" * 80)
    print(f"  OSINT THREAT INTELLIGENCE REPORT — Top {top_n} Threats")
    print("=" * 80)

    for rank, row in report.iterrows():
        pub = row["published"].strftime("%Y-%m-%d") if pd.notna(row["published"]) else "N/A"
        title = textwrap.shorten(row["title"], width=65, placeholder="...")
        print(
            f"\n[{rank:>2}] [{row['severity_label']:>8}] Score: {row['risk_score']:.2f}/10"
        )
        print(f"     Category : {row['threat_category']}")
        print(f"     Published: {pub}  |  Section: {row['section_name']}")
        print(f"     Title    : {title}")
        orgs = row["entities_org"]
        if orgs:
            print(f"     Key orgs : {textwrap.shorten(orgs, 60, placeholder='...')}")
        print(f"     URL      : {row['url']}")

    print("\n" + "=" * 80)
    print("Severity distribution:")
    dist = df["severity_label"].value_counts().reindex(["Critical", "High", "Medium", "Low"], fill_value=0)
    for label, count in dist.items():
        bar = "█" * (count * 40 // max(dist.max(), 1))
        print(f"  {label:>8}: {bar} {count}")
    print("=" * 80 + "\n")


def intelligence_briefs(df: pd.DataFrame, top_per_category: int = 2) -> dict:
    """
    Extract top-N articles per threat category as structured intelligence briefs.
    Returns dict: category → list of brief dicts.
    """
    briefs = {}
    categories = list(THREAT_TAXONOMY.keys()) + ["Unknown"]
    for cat in categories:
        subset = df[df["threat_category"] == cat].nlargest(top_per_category, "risk_score")
        if subset.empty:
            continue
        briefs[cat] = []
        for _, row in subset.iterrows():
            briefs[cat].append({
                "title": row["title"],
                "risk_score": row["risk_score"],
                "severity": row["severity_label"],
                "published": str(row["published"])[:10],
                "url": row["url"],
                "key_orgs": row.get("entities_org", ""),
                "key_locations": row.get("entities_gpe", ""),
            })
    return briefs
