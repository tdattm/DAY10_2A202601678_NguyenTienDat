from __future__ import annotations

from datetime import datetime

import pandas as pd

from core.utils import normalize_whitespace
from ingestion.crossref import PaperRecord


CLEAN_COLUMNS = [
    "paper_id",
    "title",
    "summary",
    "published",
    "authors_joined",
    "categories_joined",
    "age_days",
    "text_for_embedding",
    "abs_url",
    "pdf_url",
]


def _normalize_list(values: list[str] | None) -> list[str]:
    """Normalize string lists and remove case-insensitive duplicates."""
    if not isinstance(values, list):
        return []

    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = normalize_whitespace(str(value or ""))
        key = text.casefold()
        if text and key not in seen:
            normalized.append(text)
            seen.add(key)
    return normalized


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Convert raw Crossref records to the agreed clean data contract."""
    run_timestamp = pd.Timestamp(run_date)
    if run_timestamp.tzinfo is not None:
        run_timestamp = run_timestamp.tz_localize(None)
    run_timestamp = run_timestamp.normalize()

    rows: list[dict] = []
    for record in records:
        paper_id = normalize_whitespace(str(record.paper_id or ""))
        title = normalize_whitespace(str(record.title or ""))
        summary = normalize_whitespace(str(record.summary or ""))
        abs_url = normalize_whitespace(str(record.abs_url or ""))
        pdf_url = normalize_whitespace(str(record.pdf_url or ""))

        if not paper_id or not title or not summary:
            continue

        published_timestamp = pd.to_datetime(record.published, errors="coerce")
        if pd.isna(published_timestamp):
            continue
        published_timestamp = pd.Timestamp(published_timestamp)
        if published_timestamp.tzinfo is not None:
            published_timestamp = published_timestamp.tz_localize(None)
        published_timestamp = published_timestamp.normalize()

        age_days = int((run_timestamp - published_timestamp).days)
        if age_days < 0:
            continue

        published = published_timestamp.strftime("%Y-%m-%d")
        authors_joined = ", ".join(_normalize_list(record.authors))
        categories_joined = ", ".join(_normalize_list(record.categories))

        text_parts = [f"Title: {title}."]
        if authors_joined:
            text_parts.append(f"Authors: {authors_joined}.")
        if categories_joined:
            text_parts.append(f"Categories: {categories_joined}.")
        text_parts.extend([f"Published: {published}.", f"Summary: {summary}"])
        text_for_embedding = normalize_whitespace(" ".join(text_parts))

        rows.append(
            {
                "paper_id": paper_id,
                "title": title,
                "summary": summary,
                "published": published,
                "authors_joined": authors_joined,
                "categories_joined": categories_joined,
                "age_days": age_days,
                "text_for_embedding": text_for_embedding,
                "abs_url": abs_url,
                "pdf_url": pdf_url,
            }
        )

    df = pd.DataFrame(rows, columns=CLEAN_COLUMNS)
    if df.empty:
        return df

    df["_paper_id_key"] = df["paper_id"].str.casefold()
    df = df.drop_duplicates(subset="_paper_id_key", keep="first")
    df = df.drop(columns="_paper_id_key")
    df = df.sort_values(
        by=["published", "paper_id"],
        ascending=[False, True],
        kind="stable",
    ).reset_index(drop=True)
    return df[CLEAN_COLUMNS]
