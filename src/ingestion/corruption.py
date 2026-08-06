from __future__ import annotations

from pathlib import Path

import pandas as pd

from core.utils import read_json, write_json


def _frozen_doc_ids(output_log_path: Path) -> list[str]:
    """Read document IDs used by the frozen evaluation set."""
    test_set_path = output_log_path.parent.parent / "eval" / "test_set.json"
    if not test_set_path.exists():
        return []
    try:
        test_set = read_json(test_set_path)
    except (OSError, ValueError):
        return []

    doc_ids: list[str] = []
    for sample in test_set if isinstance(test_set, list) else []:
        if not isinstance(sample, dict):
            continue
        for doc_id in sample.get("ground_truth_doc_ids", []):
            value = str(doc_id).strip()
            if value and value not in doc_ids:
                doc_ids.append(value)
    return doc_ids


def _rebuild_embedding_text(df: pd.DataFrame) -> None:
    """Rebuild the clean embedding representation after field corruption."""
    df["text_for_embedding"] = (
        "Title: "
        + df["title"].fillna("").astype(str)
        + " | Authors: "
        + df["authors_joined"].fillna("").astype(str)
        + " | Summary: "
        + df["summary"].fillna("").astype(str)
    )


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path) -> pd.DataFrame:
    """Create controlled corruption that overlaps the frozen evaluation set.

    Pseudo-code:
    1. Drop mot so latest records.
    2. Blank summary o mot so dong.
    3. Inject noise vao text.
    4. Lam title bi truncate.
    5. Lam published date cu di.
    6. Add duplicate rows.
    7. Rebuild `text_for_embedding`.
    8. Ghi corruption log vao output_log_path.
    """
    required_columns = {
        "paper_id",
        "title",
        "summary",
        "published",
        "authors_joined",
        "text_for_embedding",
    }
    missing = required_columns - set(df.columns)
    if missing:
        raise ValueError(f"Clean dataframe is missing required columns: {sorted(missing)}")
    if df.empty:
        raise ValueError("Cannot corrupt an empty clean dataframe.")

    output_log = Path(output_log_path)
    corrupted = df.copy(deep=True).reset_index(drop=True)
    frozen_ids = _frozen_doc_ids(output_log)
    available_ids = set(corrupted["paper_id"].astype(str))
    target_ids = [paper_id for paper_id in frozen_ids if paper_id in available_ids]
    if not target_ids:
        target_ids = [str(corrupted.iloc[0]["paper_id"])]

    row_for_id = {
        str(row["paper_id"]): index
        for index, row in corrupted.iterrows()
    }

    def index_for(position: int) -> int:
        paper_id = target_ids[position % len(target_ids)]
        return row_for_id[paper_id]

    changes: list[dict[str, object]] = []

    summary_index = index_for(0)
    summary_id = str(corrupted.at[summary_index, "paper_id"])
    original_summary = str(corrupted.at[summary_index, "summary"])
    corrupted.at[summary_index, "summary"] = ""
    changes.append(
        {
            "scenario": "blank_summary",
            "paper_ids": [summary_id],
            "changed_fields": {"summary": {"from_length": len(original_summary), "to": ""}},
        }
    )

    stale_index = index_for(1)
    stale_id = str(corrupted.at[stale_index, "paper_id"])
    original_date = str(corrupted.at[stale_index, "published"])
    corrupted.at[stale_index, "published"] = "2000-01-01"
    changes.append(
        {
            "scenario": "stale_date",
            "paper_ids": [stale_id],
            "changed_fields": {"published": {"from": original_date, "to": "2000-01-01"}},
        }
    )

    duplicate_index = index_for(2)
    duplicate_id = str(corrupted.at[duplicate_index, "paper_id"])
    duplicate = corrupted.iloc[[duplicate_index]].copy()
    corrupted = pd.concat([corrupted, duplicate], ignore_index=True)
    changes.append(
        {
            "scenario": "duplicate",
            "paper_ids": [duplicate_id],
            "changed_fields": {"row_count_added": 1, "paper_id_preserved": True},
        }
    )

    noise_index = index_for(3)
    noise_id = str(corrupted.at[noise_index, "paper_id"])
    original_embedding = str(corrupted.at[noise_index, "text_for_embedding"])
    _rebuild_embedding_text(corrupted)
    noise = " [NOISE::unrelated_weather_report_7f3a]"
    corrupted.at[noise_index, "text_for_embedding"] = original_embedding + noise
    changes.append(
        {
            "scenario": "add_noise",
            "paper_ids": [noise_id],
            "changed_fields": {"text_for_embedding_suffix": noise},
        }
    )

    corrupted_csv = output_log.parent.parent / "clean" / "papers_clean_corrupted.csv"
    corrupted_json = output_log.parent.parent / "clean" / "papers_clean_corrupted.json"
    corrupted_csv.parent.mkdir(parents=True, exist_ok=True)
    corrupted.to_csv(corrupted_csv, index=False)
    corrupted.to_json(corrupted_json, orient="records", indent=2, force_ascii=False)
    write_json(
        output_log,
        {
            "source": "clean dataset",
            "frozen_test_set_doc_ids": frozen_ids,
            "overlap_doc_ids": sorted(
                {paper_id for change in changes for paper_id in change["paper_ids"]}
                & set(frozen_ids)
            ),
            "original_row_count": int(len(df)),
            "corrupted_row_count": int(len(corrupted)),
            "scenarios": changes,
            "artifacts": {
                "csv": str(corrupted_csv),
                "json": str(corrupted_json),
            },
        },
    )
    return corrupted
