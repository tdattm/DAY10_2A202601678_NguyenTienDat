from __future__ import annotations

from typing import Any
from pathlib import Path


def generate_phase1_report(
    report_path: Path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    """Markdown report for baseline phase."""
    
    md_content = f"""# Phase 1: Baseline Data & Evaluation Report

## 1. Source Summary
- Source API: {source_summary.get('api', 'N/A')}
- Query: {source_summary.get('query', 'N/A')}
- Total Documents: {source_summary.get('total_documents', 'N/A')}

## 2. Evaluation Metrics
- Hit Rate: {metrics.get('retrieval_hit_rate', 'N/A')}
- Token F1: {metrics.get('mean_token_f1', 'N/A')}
- Judge Accuracy: {metrics.get('judge_accuracy', 'N/A')}
- Mean Judge Score: {metrics.get('mean_judge_score', 'N/A')}

## 3. Data Quality & Freshness
- Quality Passed: {quality.get('overall_passed', 'N/A')}
- Freshness Passed: {freshness.get('is_fresh', 'N/A')}
- Stale Rows: {freshness.get('stale_rows', 0)} / {freshness.get('total_rows', 0)}
- Latest Published: {freshness.get('latest_published', 'N/A')}
"""
    
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(md_content)


def generate_corruption_report(
    report_path: Path,
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    corrupted_freshness: dict[str, Any],
    repaired_freshness: dict[str, Any],
) -> None:
    """Markdown report comparing baseline/corrupted/repaired."""
    
    md_content = f"""# Phase 2: Data Corruption & Repair Comparison

## 1. Evaluation Metrics Comparison

| Metric | Baseline | Corrupted | Repaired |
|---|---|---|---|
| Hit Rate | {baseline_metrics.get('retrieval_hit_rate', 'N/A')} | {corrupted_metrics.get('retrieval_hit_rate', 'N/A')} | {repaired_metrics.get('retrieval_hit_rate', 'N/A')} |
| Token F1 | {baseline_metrics.get('mean_token_f1', 'N/A')} | {corrupted_metrics.get('mean_token_f1', 'N/A')} | {repaired_metrics.get('mean_token_f1', 'N/A')} |
| Judge Accuracy | {baseline_metrics.get('judge_accuracy', 'N/A')} | {corrupted_metrics.get('judge_accuracy', 'N/A')} | {repaired_metrics.get('judge_accuracy', 'N/A')} |
| Judge Score | {baseline_metrics.get('mean_judge_score', 'N/A')} | {corrupted_metrics.get('mean_judge_score', 'N/A')} | {repaired_metrics.get('mean_judge_score', 'N/A')} |

## 2. Quality & Freshness Comparison

| Attribute | Corrupted | Repaired |
|---|---|---|
| Quality Passed | {corrupted_quality.get('overall_passed', 'N/A')} | {repaired_quality.get('overall_passed', 'N/A')} |
| Freshness Passed | {corrupted_freshness.get('is_fresh', 'N/A')} | {repaired_freshness.get('is_fresh', 'N/A')} |
| Stale Rows | {corrupted_freshness.get('stale_rows', 'N/A')} / {corrupted_freshness.get('total_rows', 'N/A')} | {repaired_freshness.get('stale_rows', 'N/A')} / {repaired_freshness.get('total_rows', 'N/A')} |
"""

    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(md_content)
