from __future__ import annotations

from dataclasses import asdict, dataclass
from html import unescape
from pathlib import Path
import re
import time
from typing import Any

import requests

from core.config import Settings
from core.utils import normalize_whitespace, read_json, write_json


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Parse a Crossref ``/works`` response into normalized paper records.

    Pseudo-code:
    1. Duyet `payload["message"]["items"]`.
    2. Lay DOI, title, abstract, authors, subject, dates, URLs.
    3. Chuan hoa text va bo record khong hop le.
    4. Tra ve list `PaperRecord`.
    """
    if not isinstance(payload, dict):
        return []

    message = payload.get("message", {})
    items = message.get("items", []) if isinstance(message, dict) else []
    if not isinstance(items, list):
        return []

    records: list[PaperRecord] = []
    for item in items:
        if not isinstance(item, dict):
            continue

        doi = _as_text(item.get("DOI"))
        title = _first_text(item.get("title"))
        summary = _clean_abstract(item.get("abstract") or item.get("description"))
        if not doi or not title or not summary:
            continue

        authors = []
        for author in item.get("author", []) or []:
            if not isinstance(author, dict):
                continue
            given = _as_text(author.get("given"))
            family = _as_text(author.get("family"))
            name = normalize_whitespace(f"{given} {family}")
            if name:
                authors.append(name)

        categories = [
            value
            for value in (_as_text(subject) for subject in item.get("subject", []) or [])
            if value
        ]

        published = _date_from_item(
            item, "published-online", "published-print", "published", "issued", "created"
        )
        updated = _date_from_item(item, "updated", "indexed", "created", "published")

        pdf_url = ""
        for link in item.get("link", []) or []:
            if not isinstance(link, dict):
                continue
            content_type = _as_text(link.get("content-type")).lower()
            url = _as_text(link.get("URL"))
            if url and content_type == "application/pdf":
                pdf_url = url
                break

        records.append(
            PaperRecord(
                paper_id=doi,
                title=title,
                summary=summary,
                authors=authors,
                categories=categories,
                primary_category=categories[0] if categories else "",
                published=published,
                updated=updated,
                abs_url=_as_text(item.get("URL")) or f"https://doi.org/{doi}",
                pdf_url=pdf_url,
                comment=_as_text(item.get("comment")),
            )
        )

    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Fetch, persist, parse, and persist Crossref records.

    The request retries transient rate-limit and server errors before raising
    an exception for a failed response.
    """
    params = {
        "query.bibliographic": settings.source_query,
        "filter": settings.source_filter,
        "rows": settings.max_results,
    }
    headers = {
        "Accept": "application/json",
        "User-Agent": "day10-data-observability-lab/0.1 (mailto:example@example.com)",
    }
    retryable_statuses = {429, 500, 502, 503, 504}
    response = None

    for attempt in range(4):
        response = requests.get(
            "https://api.crossref.org/works",
            params=params,
            headers=headers,
            timeout=30,
        )
        if response.status_code not in retryable_statuses or attempt == 3:
            break
        retry_after = response.headers.get("Retry-After")
        try:
            delay = float(retry_after) if retry_after else 2**attempt
        except ValueError:
            delay = 2**attempt
        time.sleep(min(delay, 30))

    assert response is not None
    response.raise_for_status()
    payload = response.json()
    write_json(settings.paths.raw_api_response, payload)

    records = parse_crossref_payload(payload)
    write_json(settings.paths.raw_records_json, [asdict(record) for record in records])
    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Load a JSON snapshot previously written by ``fetch_source_records``."""
    payload = read_json(path)
    if isinstance(payload, dict) and "records" in payload:
        payload = payload["records"]
    if not isinstance(payload, list):
        return []

    records: list[PaperRecord] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        try:
            records.append(PaperRecord(**item))
        except TypeError:
            continue
    return records


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    return normalize_whitespace(unescape(str(value)))


def _first_text(value: Any) -> str:
    if isinstance(value, list):
        for item in value:
            text = _as_text(item)
            if text:
                return text
        return ""
    return _as_text(value)


def _clean_abstract(value: Any) -> str:
    text = _as_text(value)
    text = re.sub(r"<[^>]+>", " ", text)
    return normalize_whitespace(unescape(text))


def _date_from_item(item: dict[str, Any], *field_names: str) -> str:
    for field_name in field_names:
        value = item.get(field_name)
        if not isinstance(value, dict):
            continue
        date_parts = value.get("date-parts")
        if not isinstance(date_parts, list) or not date_parts or not isinstance(date_parts[0], list):
            continue
        parts = date_parts[0]
        if not parts or not all(isinstance(part, int) for part in parts):
            continue
        year, *rest = parts
        if rest:
            month = rest[0]
            if len(rest) > 1:
                return f"{year:04d}-{month:02d}-{rest[1]:02d}"
            return f"{year:04d}-{month:02d}"
        return f"{year:04d}"
    return ""
