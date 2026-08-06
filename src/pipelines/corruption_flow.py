from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from core.config import load_settings
from core.utils import read_json
from evaluation.metrics import evaluate_pipeline
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from retrieval.index import LocalEmbeddingIndex


def _save_dataframe(df: pd.DataFrame, csv_path: Path, json_path: Path) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(csv_path, index=False)
    df.to_json(json_path, orient="records", indent=2, force_ascii=False)


def _refresh_age_days(df: pd.DataFrame, run_date: datetime) -> pd.DataFrame:
    """Keep age_days consistent with a deliberately corrupted published date."""
    result = df.copy()
    today = pd.Timestamp(run_date).tz_localize(None).normalize()
    published = pd.to_datetime(result["published"], errors="coerce")
    result["age_days"] = (today - published.dt.tz_localize(None).dt.normalize()).dt.days
    return result


def _comparison_report(
    path: Path,
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    baseline_quality: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    baseline_freshness: dict[str, Any],
    corrupted_freshness: dict[str, Any],
    repaired_freshness: dict[str, Any],
) -> None:
    metric_names = (
        ("Retrieval hit rate", "retrieval_hit_rate"),
        ("Mean token F1", "mean_token_f1"),
        ("Judge accuracy", "judge_accuracy"),
        ("Mean judge score", "mean_judge_score"),
    )
    metric_rows = "\n".join(
        f"| {label} | {baseline_metrics.get(key, 'N/A')} | "
        f"{corrupted_metrics.get(key, 'N/A')} | {repaired_metrics.get(key, 'N/A')} |"
        for label, key in metric_names
    )
    observability_rows = "\n".join(
        [
            f"| Quality overall passed | {baseline_quality.get('overall_passed', 'N/A')} | "
            f"{corrupted_quality.get('overall_passed', 'N/A')} | {repaired_quality.get('overall_passed', 'N/A')} |",
            f"| Duplicate IDs | {baseline_quality.get('paper_id', {}).get('duplicate_count', 'N/A')} | "
            f"{corrupted_quality.get('paper_id', {}).get('duplicate_count', 'N/A')} | "
            f"{repaired_quality.get('paper_id', {}).get('duplicate_count', 'N/A')} |",
            f"| Short summaries | {baseline_quality.get('summary', {}).get('too_short_count', 'N/A')} | "
            f"{corrupted_quality.get('summary', {}).get('too_short_count', 'N/A')} | "
            f"{repaired_quality.get('summary', {}).get('too_short_count', 'N/A')} |",
            f"| Freshness passed | {baseline_freshness.get('is_fresh', 'N/A')} | "
            f"{corrupted_freshness.get('is_fresh', 'N/A')} | {repaired_freshness.get('is_fresh', 'N/A')} |",
            f"| Stale rows | {baseline_freshness.get('stale_rows', 'N/A')} | "
            f"{corrupted_freshness.get('stale_rows', 'N/A')} | {repaired_freshness.get('stale_rows', 'N/A')} |",
        ]
    )
    content = f"""# Phase 2: Corruption, Repair & Comparison

## Evaluation metrics

| Metric | Baseline | Corrupted | Repaired |
|---|---:|---:|---:|
{metric_rows}

## Data quality and freshness

| Signal | Baseline | Corrupted | Repaired |
|---|---:|---:|---:|
{observability_rows}

## Interpretation

The corrupted state intentionally modifies records used by the frozen evaluation
set. Repair starts from `data/raw/crossref_records.json` and reruns the standard
cleaning logic, so it does not preserve corruption from the derived clean file.
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main() -> dict[str, Any]:
    """Run corrupted evaluation, raw-snapshot repair, and three-state comparison."""
    settings = load_settings(Path(__file__).resolve().parents[2])
    run_date = datetime.now(UTC)

    if not settings.paths.baseline_metrics.exists():
        raise RuntimeError("Baseline metrics are missing. Run phase1 before corruption_flow.")
    if not settings.paths.clean_csv.exists():
        raise RuntimeError("Clean CSV is missing. Run phase1 before corruption_flow.")
    if not settings.paths.eval_testset.exists():
        raise RuntimeError("Frozen test set is missing. Run phase1 before corruption_flow.")

    clean_df = pd.read_csv(settings.paths.clean_csv)
    if not settings.paths.corrupted_clean_csv.exists() or not settings.paths.corruption_log.exists():
        corrupted_df = corrupt_clean_dataframe(clean_df, settings.paths.corruption_log)
    else:
        corrupted_df = pd.read_csv(settings.paths.corrupted_clean_csv)
    corrupted_df = _refresh_age_days(corrupted_df, run_date)
    _save_dataframe(
        corrupted_df,
        settings.paths.corrupted_clean_csv,
        settings.paths.corrupted_clean_json,
    )

    corrupted_index = LocalEmbeddingIndex.build(
        corrupted_df,
        settings,
        embeddings_output_path=settings.paths.corrupted_embeddings_json,
    )
    corrupted_bundle = evaluate_pipeline(
        settings,
        corrupted_index,
        settings.paths.eval_testset,
        settings.paths.corrupted_metrics,
        settings.paths.corrupted_answers,
    )
    corrupted_quality = run_data_quality_checks(corrupted_df, settings, "corrupted_quality")
    corrupted_freshness = build_freshness_report(
        corrupted_df,
        settings,
        settings.paths.quality_dir / "corrupted_freshness.json",
    )

    raw_records = load_raw_records(settings.paths.raw_records_json)
    if not raw_records:
        raise RuntimeError("Raw Crossref records are missing; repair cannot proceed.")
    repaired_df = build_clean_dataframe(raw_records, run_date)
    if repaired_df.empty:
        raise RuntimeError("Repair cleaning produced no records.")
    _save_dataframe(
        repaired_df,
        settings.paths.repaired_clean_csv,
        settings.paths.repaired_clean_json,
    )

    repaired_index = LocalEmbeddingIndex.build(
        repaired_df,
        settings,
        embeddings_output_path=settings.paths.repaired_embeddings_json,
    )
    repaired_bundle = evaluate_pipeline(
        settings,
        repaired_index,
        settings.paths.eval_testset,
        settings.paths.repaired_metrics,
        settings.paths.repaired_answers,
    )
    repaired_quality = run_data_quality_checks(repaired_df, settings, "repaired_quality")
    repaired_freshness = build_freshness_report(
        repaired_df,
        settings,
        settings.paths.quality_dir / "repaired_freshness.json",
    )

    baseline_metrics = read_json(settings.paths.baseline_metrics)
    baseline_quality_path = settings.paths.quality_dir / "baseline_quality.json"
    baseline_quality = (
        read_json(baseline_quality_path)
        if baseline_quality_path.exists()
        else run_data_quality_checks(clean_df, settings, "baseline_quality")
    )
    baseline_freshness = (
        read_json(settings.paths.freshness_report)
        if settings.paths.freshness_report.exists()
        else build_freshness_report(clean_df, settings, settings.paths.freshness_report)
    )
    _comparison_report(
        settings.paths.comparison_report,
        baseline_metrics,
        corrupted_bundle.summary,
        repaired_bundle.summary,
        baseline_quality,
        corrupted_quality,
        repaired_quality,
        baseline_freshness,
        corrupted_freshness,
        repaired_freshness,
    )

    return {
        "baseline": baseline_metrics,
        "corrupted": corrupted_bundle.summary,
        "repaired": repaired_bundle.summary,
        "report": str(settings.paths.comparison_report),
    }
