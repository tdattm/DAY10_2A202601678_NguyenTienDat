from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from core.utils import first_sentence, normalize_whitespace, read_json, write_json


REQUIRED_COLUMNS = {
    "paper_id",
    "title",
    "summary",
    "published",
    "authors_joined",
    "categories_joined",
}


def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
    """Build and freeze a deterministic 5–10 question evaluation set."""
    output = Path(output_path)
    if output.exists():
        frozen = read_json(output)
        if isinstance(frozen, list) and len(frozen) == 17:
            return frozen

    missing_columns = REQUIRED_COLUMNS - set(df.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"Clean dataframe is missing required columns: {missing}")
    if df.empty:
        raise ValueError("Cannot build an evaluation set from an empty dataframe.")
    if len(df) < 2:
        raise ValueError("At least 2 cleaned papers are required.")

    selected = df.sort_values(
        by=["published", "paper_id"],
        ascending=[False, True],
        kind="stable",
    ).head(6).reset_index(drop=True)

    def topic_hint(title: str) -> str:
        hint = title.split(":", 1)[0]
        hint = hint.replace("Large-Language-Model-Based", "large language model")
        hint = hint.replace("Retrieval-Augmented", "retrieval augmented")
        return hint.strip().lower()

    def summary_sentences(summary: str) -> list[str]:
        normalized = normalize_whitespace(summary)
        first = first_sentence(normalized)
        remainder = normalized[len(first) :].strip()
        second = first_sentence(remainder) if remainder else ""
        return [sentence for sentence in (first, second) if sentence]

    candidates: list[dict[str, Any]] = []
    for _, row in selected.iterrows():
        paper_id = normalize_whitespace(str(row["paper_id"] or ""))
        title = normalize_whitespace(str(row["title"] or ""))
        summary = normalize_whitespace(str(row["summary"] or ""))
        published = normalize_whitespace(str(row["published"] or ""))
        authors = normalize_whitespace(str(row["authors_joined"] or ""))
        categories = normalize_whitespace(str(row["categories_joined"] or ""))

        if not paper_id or not title or not summary or not published:
            continue

        hint = topic_hint(title)
        sentences = summary_sentences(summary)
        if authors:
            candidates.append(
                {
                    "question_type": "factual",
                    "question": f"Who authored the study on {hint}?",
                    "ground_truth": authors,
                    "ground_truth_doc_ids": [paper_id],
                }
            )
        if categories:
            candidates.append(
                {
                    "question_type": "factual",
                    "question": f"Which research categories are associated with work on {hint}?",
                    "ground_truth": categories,
                    "ground_truth_doc_ids": [paper_id],
                }
            )
        candidates.append(
            {
                "question_type": "factual",
                "question": f"When was the study about {hint} published?",
                "ground_truth": published,
                "ground_truth_doc_ids": [paper_id],
            }
        )
        candidates.append(
            {
                "question_type": "factual",
                "question": f"What main problem or application is described in the work on {hint}?",
                "ground_truth": sentences[1] if len(sentences) > 1 else sentences[0],
                "ground_truth_doc_ids": [paper_id],
            }
        )

    if len(candidates) < 5:
        raise ValueError("At least 5 valid evaluation questions are required.")

    test_set = [
        {"id": f"q{index}", **sample}
        for index, sample in enumerate(candidates[:17], start=1)
    ]
    if not test_set:
        raise ValueError("No valid evaluation samples could be generated.")

    write_json(output_path, test_set)
    return test_set
