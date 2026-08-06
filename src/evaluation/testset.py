from __future__ import annotations

from typing import Any

import pandas as pd

from core.utils import first_sentence, normalize_whitespace, write_json


REQUIRED_COLUMNS = {
    "paper_id",
    "title",
    "summary",
    "published",
    "authors_joined",
    "categories_joined",
}


def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
    """Build a deterministic evaluation set from the clean data contract."""
    missing_columns = REQUIRED_COLUMNS - set(df.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"Clean dataframe is missing required columns: {missing}")
    if df.empty:
        raise ValueError("Cannot build an evaluation set from an empty dataframe.")
    if len(df) < 2:
        raise ValueError("At least 2 cleaned papers are required.")

    selected = (
        df.sort_values(
            by=["published", "paper_id"],
            ascending=[False, True],
            kind="stable",
        )
        .head(4)
        .reset_index(drop=True)
    )

    test_set: list[dict[str, Any]] = []
    for index, row in selected.iterrows():
        paper_id = normalize_whitespace(str(row["paper_id"] or ""))
        title = normalize_whitespace(str(row["title"] or ""))
        summary = normalize_whitespace(str(row["summary"] or ""))
        published = normalize_whitespace(str(row["published"] or ""))
        authors = normalize_whitespace(str(row["authors_joined"] or ""))
        categories = normalize_whitespace(str(row["categories_joined"] or ""))

        if not paper_id or not title or not summary or not published:
            continue

        sample_number = index + 1
        test_set.append(
            {
                "id": f"summary-{sample_number}",
                "question_type": "summary",
                "question": f"What is the paper '{title}' about?",
                "ground_truth": first_sentence(summary),
                "ground_truth_doc_ids": [paper_id],
            }
        )
        if authors:
            test_set.append(
                {
                    "id": f"authors-{sample_number}",
                    "question_type": "authors",
                    "question": f"Who authored the paper '{title}'?",
                    "ground_truth": authors,
                    "ground_truth_doc_ids": [paper_id],
                }
            )
        test_set.append(
            {
                "id": f"date-{sample_number}",
                "question_type": "date",
                "question": f"When was the paper '{title}' published?",
                "ground_truth": published,
                "ground_truth_doc_ids": [paper_id],
            }
        )
        if categories:
            test_set.append(
                {
                    "id": f"categories-{sample_number}",
                    "question_type": "categories",
                    "question": f"What categories are associated with the paper '{title}'?",
                    "ground_truth": categories,
                    "ground_truth_doc_ids": [paper_id],
                }
            )

    if not test_set:
        raise ValueError("No valid evaluation samples could be generated.")

    write_json(output_path, test_set)
    return test_set
