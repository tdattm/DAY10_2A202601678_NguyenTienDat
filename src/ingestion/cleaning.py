from __future__ import annotations

from datetime import datetime
from html import unescape
import re

import pandas as pd

from core.config import Settings
from core.utils import ensure_parent, normalize_whitespace
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


def _clean_text(value: object) -> str:
    """Remove XML/HTML tags and normalize whitespace."""
    text = unescape(str(value or ""))
    text = re.sub(r"<[^>]*>", " ", text)
    return normalize_whitespace(text)


def _normalize_list(values: list[str | dict] | None) -> list[str]:
    """Flatten, normalize, and de-duplicate authors or categories."""
    if not isinstance(values, list):
        return []

    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        if isinstance(value, dict):
            text = _clean_text(
                value.get("name")
                or " ".join(
                    part for part in (value.get("given"), value.get("family")) if part
                )
            )
        else:
            text = _clean_text(value)
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
        title = _clean_text(record.title)
        summary = _clean_text(record.summary)
        abs_url = normalize_whitespace(str(record.abs_url or ""))
        pdf_url = normalize_whitespace(str(record.pdf_url or ""))

        if not paper_id or not title or len(summary) < 100:
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

        text_for_embedding = (
            f"Title: {title} | Authors: {authors_joined} | Summary: {summary}"
        )

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


def save_clean_artifacts(df: pd.DataFrame, settings: Settings) -> None:
    """Save cleaned records to the configured CSV and JSON paths."""
    ensure_parent(settings.paths.clean_csv)
    ensure_parent(settings.paths.clean_json)
    df.to_csv(settings.paths.clean_csv, index=False)
    df.to_json(settings.paths.clean_json, orient="records", indent=2, force_ascii=False)
