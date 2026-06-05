"""
Phase 3: Data quality profiler.
Runs 8 quality checks and returns structured findings as a dict.

Usage:
    from src.loader import load_csv
    from src.profiler import profile
    import json

    df = load_csv("sample_data/messy_sample.csv")
    result = profile(df)
    print(json.dumps(result, indent=2, default=str))
"""

import logging
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


def profile(df: pd.DataFrame) -> dict:
    """
    Run all quality checks on a DataFrame.

    Args:
        df: Input DataFrame to profile.

    Returns:
        dict with keys: shape, missing, duplicates, dtypes, cardinality,
        outliers, string_consistency, date_issues, summary_stats.
    """
    logger.info(f"Profiling DataFrame: {df.shape[0]} rows x {df.shape[1]} columns")

    result = {
        "shape":              _check_shape(df),
        "missing":            _check_missing(df),
        "duplicates":         _check_duplicates(df),
        "dtypes":             _check_dtypes(df),
        "cardinality":        _check_cardinality(df),
        "outliers":           _check_outliers(df),
        "string_consistency": _check_string_consistency(df),
        "date_issues":        _check_date_issues(df),
        "summary_stats":      _check_summary_stats(df),
    }

    logger.info("Profiling complete.")
    return result


# ---------------------------------------------------------------------------
# Individual check functions
# ---------------------------------------------------------------------------

def _check_shape(df: pd.DataFrame) -> dict:
    return {"rows": int(df.shape[0]), "columns": int(df.shape[1])}


def _check_missing(df: pd.DataFrame) -> dict:
    """Count and percentage of nulls per column. Only reports columns with nulls."""
    findings = {}
    for col in df.columns:
        count = int(df[col].isna().sum())
        if count > 0:
            pct = round(count / len(df) * 100, 1)
            findings[col] = {"count": count, "pct": pct}
    return findings


def _check_duplicates(df: pd.DataFrame) -> dict:
    """Count of exact duplicate rows and up to 3 examples."""
    # duplicated() marks second+ occurrences; keep=False marks all copies
    count = int(df.duplicated().sum())

    examples = []
    if count > 0:
        dup_df = df[df.duplicated(keep=False)].drop_duplicates()
        examples = dup_df.head(3).to_dict(orient="records")

    return {"count": count, "examples": examples}


def _check_dtypes(df: pd.DataFrame) -> dict:
    """
    Flag object columns whose values are mostly numeric.
    A column is 'looks_numeric' if >= 80% of non-null values parse as numbers.
    """
    findings = {}
    for col in df.select_dtypes(include=object).columns:
        non_null = df[col].dropna()
        if len(non_null) == 0:
            continue
        converted = pd.to_numeric(non_null, errors="coerce")
        numeric_rate = float(converted.notna().mean())
        looks_numeric = numeric_rate >= 0.8
        findings[col] = {
            "actual": "object",
            "looks_numeric": looks_numeric,
        }
    return findings


def _check_cardinality(df: pd.DataFrame) -> dict:
    """
    For string columns: unique value count and a flag for single-value columns.
    """
    findings = {}
    for col in df.select_dtypes(include=object).columns:
        unique_count = int(df[col].nunique(dropna=True))
        findings[col] = {
            "unique_count": unique_count,
            "single_value": unique_count == 1,
        }
    return findings


def _check_outliers(df: pd.DataFrame) -> dict:
    """
    For numeric columns: flag outliers using two methods and take the union.

    - Z-score (3 SD): catches outliers when the distribution is roughly normal.
    - IQR (1.5x fence): robust against extreme values that inflate the SD,
      which causes the 3-SD rule to miss moderate outliers on the other end.

    Using both ensures a single extreme value (e.g. 999999) doesn't mask
    a second outlier (e.g. -5000) by inflating the standard deviation.
    """
    findings = {}
    for col in df.select_dtypes(include=np.number).columns:
        series = df[col].dropna()
        if len(series) < 4:
            continue

        # Z-score method
        std = series.std()
        zscore_mask = pd.Series(False, index=series.index)
        if std > 0:
            mean = series.mean()
            zscore_mask = (series - mean).abs() > 3 * std

        # IQR method
        q1 = series.quantile(0.25)
        q3 = series.quantile(0.75)
        iqr = q3 - q1
        iqr_mask = pd.Series(False, index=series.index)
        if iqr > 0:
            lower_fence = q1 - 1.5 * iqr
            upper_fence = q3 + 1.5 * iqr
            iqr_mask = (series < lower_fence) | (series > upper_fence)

        combined_mask = zscore_mask | iqr_mask
        outlier_values = series[combined_mask].tolist()

        if outlier_values:
            findings[col] = {
                "count": len(outlier_values),
                "values": [round(float(v), 2) for v in outlier_values[:10]],
            }
    return findings


def _check_string_consistency(df: pd.DataFrame) -> dict:
    """
    For string columns:
    - mixed_case: same value appears with different casings (e.g. Calgary/calgary/CALGARY)
    - has_whitespace: any value has leading or trailing whitespace
    Only reports columns where at least one issue is found.
    """
    findings = {}
    for col in df.select_dtypes(include=object).columns:
        series = df[col].dropna().astype(str)
        if len(series) == 0:
            continue

        # Build a map from lowercased value -> set of original casings
        lower_to_originals: dict[str, set] = {}
        for val in series.unique():
            lower_to_originals.setdefault(val.lower(), set()).add(val)

        mixed_case = any(len(v) > 1 for v in lower_to_originals.values())
        has_whitespace = any(val != val.strip() for val in series)

        if mixed_case or has_whitespace:
            findings[col] = {
                "mixed_case": mixed_case,
                "has_whitespace": has_whitespace,
            }
    return findings


def _check_date_issues(df: pd.DataFrame) -> dict:
    """
    For columns whose name contains 'date':
    - parse_failures: values that cannot be parsed as dates at all
    - mixed_formats: column contains both ISO (YYYY-MM-DD) and non-ISO formats
    """
    findings = {}
    date_cols = [col for col in df.columns if "date" in col.lower()]

    for col in date_cols:
        series = df[col].dropna().astype(str)
        if len(series) == 0:
            continue

        # Count hard parse failures
        failures = 0
        for val in series:
            try:
                pd.to_datetime(val)
            except (ValueError, TypeError):
                failures += 1

        # Detect mixed formats: try strict ISO, count how many don't match
        iso_parsed = pd.to_datetime(series, format="%Y-%m-%d", errors="coerce")
        non_iso_count = int(iso_parsed.isna().sum())
        # mixed_formats = some values ARE ISO and some are NOT
        mixed_formats = 0 < non_iso_count < len(series)

        if failures > 0 or mixed_formats:
            entry: dict = {}
            if failures > 0:
                entry["parse_failures"] = failures
            if mixed_formats:
                entry["mixed_formats"] = True
                entry["non_iso_count"] = non_iso_count
            findings[col] = entry

    return findings


def _check_summary_stats(df: pd.DataFrame) -> dict:
    """Min, max, mean, median for all numeric columns."""
    findings = {}
    for col in df.select_dtypes(include=np.number).columns:
        series = df[col].dropna()
        if len(series) == 0:
            continue
        findings[col] = {
            "min":    round(float(series.min()), 2),
            "max":    round(float(series.max()), 2),
            "mean":   round(float(series.mean()), 2),
            "median": round(float(series.median()), 2),
        }
    return findings


# ---------------------------------------------------------------------------
# Smoke test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import json
    import sys
    import os

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s"
    )

    # Allow running from either project root or src/
    csv_path = "sample_data/messy_sample.csv"
    if not os.path.exists(csv_path):
        csv_path = "../sample_data/messy_sample.csv"

    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from src.loader import load_csv

    df = load_csv(csv_path)
    result = profile(df)

    print(json.dumps(result, indent=2, default=str))

    # Verify all 5 deliberate issues are caught
    print("\n--- Checkpoint Verification ---")
    assert result["missing"],                                    "FAIL: missing values not detected"
    assert result["duplicates"]["count"] >= 3,                   "FAIL: fewer than 3 duplicates detected"
    assert "salary" in result["outliers"],                       "FAIL: salary outliers not detected"
    assert "city" in result["string_consistency"],               "FAIL: city casing issue not detected"
    assert "hire_date" in result["date_issues"],                 "FAIL: hire_date mixed formats not detected"
    print("All 5 deliberate issues caught. Phase 3 checkpoint passed.")
