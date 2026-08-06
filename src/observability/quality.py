from __future__ import annotations

import json
from typing import Any
import pandas as pd
from core.config import Settings

def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Data quality checks for the clean dataset."""
    row_count = len(df)
    
    # 1. Check `paper_id` not null and unique.
    paper_id_nulls = df['paper_id'].isnull().sum()
    paper_id_duplicates = df['paper_id'].duplicated().sum()
    paper_id_valid = (paper_id_nulls == 0) and (paper_id_duplicates == 0)
    
    # 2. Check `title` not null.
    title_nulls = df['title'].isnull().sum()
    title_valid = (title_nulls == 0)
    
    # 3. Check `summary` length. (e.g., must be > 10 chars)
    # Handle possible NaN values in summary before checking length
    summary_short = df['summary'].fillna("").apply(lambda x: len(str(x)) < 10).sum()
    summary_valid = (summary_short == 0)
        
    # 4. Check freshness using `age_days`.
    stale_rows = (df['age_days'] > settings.freshness_threshold_days).sum()
    freshness_valid = (stale_rows == 0)
    
    passed = paper_id_valid and title_valid and summary_valid and freshness_valid
    
    results = {
        "row_count": int(row_count),
        "paper_id": {
            "null_count": int(paper_id_nulls),
            "duplicate_count": int(paper_id_duplicates),
            "passed": bool(paper_id_valid)
        },
        "title": {
            "null_count": int(title_nulls),
            "passed": bool(title_valid)
        },
        "summary": {
            "too_short_count": int(summary_short),
            "passed": bool(summary_valid)
        },
        "freshness": {
            "stale_count": int(stale_rows),
            "passed": bool(freshness_valid)
        },
        "overall_passed": bool(passed)
    }
    
    # 5. Ghi ket qua vao `data/quality/`.
    settings.paths.quality_dir.mkdir(parents=True, exist_ok=True)
    report_file = settings.paths.quality_dir / f"{report_name}.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4)
        
    return results

def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    """Build freshness report from dataset."""
    # 1. Tim latest va oldest published date.
    if 'published' in df.columns and len(df) > 0:
        latest_published = df['published'].max()
        oldest_published = df['published'].min()
    else:
        latest_published = None
        oldest_published = None
        
    # 2. Dem so dong stale.
    stale_rows = (df['age_days'] > settings.freshness_threshold_days).sum()
    total_rows = len(df)
    
    # 3. Tao payload:
    payload = {
        "latest_published": str(latest_published) if latest_published else None,
        "oldest_published": str(oldest_published) if oldest_published else None,
        "stale_rows": int(stale_rows),
        "total_rows": int(total_rows),
        "is_fresh": bool(stale_rows == 0)
    }
    
    # 4. Ghi JSON report.
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=4)
        
    return payload
