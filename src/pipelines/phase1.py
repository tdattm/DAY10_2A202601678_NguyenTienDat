from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from core.config import load_settings
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe, save_clean_artifacts
from ingestion.crossref import fetch_source_records, load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.index import LocalEmbeddingIndex


def main() -> dict:
    """Run the Phase 1 baseline pipeline end-to-end."""
    settings = load_settings(Path(__file__).resolve().parents[2])

    raw_records_path = settings.paths.raw_records_json
    if settings.refresh_source or not raw_records_path.exists():
        records = fetch_source_records(settings)
    else:
        records = load_raw_records(raw_records_path)
        if not records:
            records = fetch_source_records(settings)

    if not records:
        raise RuntimeError("Crossref returned no valid records; cannot build the baseline.")

    clean_df = build_clean_dataframe(records, datetime.now(UTC))
    if clean_df.empty:
        raise RuntimeError("Cleaning removed all Crossref records; cannot build the baseline.")
    save_clean_artifacts(clean_df, settings)

    index = LocalEmbeddingIndex.build(clean_df, settings)
    build_test_set(clean_df, settings.paths.eval_testset)
    evaluation = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.baseline_metrics,
        answers_output_path=settings.paths.baseline_answers,
    )

    quality = run_data_quality_checks(clean_df, settings, "baseline_quality")
    freshness = build_freshness_report(clean_df, settings, settings.paths.freshness_report)
    source_summary = {
        "api": settings.source_api,
        "query": settings.source_query,
        "filter": settings.source_filter,
        "total_documents": len(records),
        "clean_documents": len(clean_df),
    }
    generate_phase1_report(
        report_path=settings.paths.baseline_report,
        source_summary=source_summary,
        metrics=evaluation.summary,
        quality=quality,
        freshness=freshness,
    )

    return {
        "source": source_summary,
        "metrics": evaluation.summary,
        "quality": quality,
        "freshness": freshness,
    }