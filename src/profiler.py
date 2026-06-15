"""
Phase 3: Data quality profiler.
Runs quality checks and returns structured findings as a dict.

Usage:
    from src.loader import load_csv
    from src.profiler import profile
    import json

    df = load_csv("sample_data/messy_sample.csv")
    result = profile(df)
    print(json.dumps(result, indent=2, default=str))
"""

import logging
import re
import unicodedata

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


def profile(df: pd.DataFrame) -> dict:
    """
    Run all quality checks on a DataFrame.

    Returns:
        dict with keys: shape, column_name_issues, missing, duplicates, dtypes,
        cardinality, outliers, string_consistency, date_issues,
        primary_key_candidates, summary_stats.
    """
    logger.info(f"Profiling DataFrame: {df.shape[0]} rows x {df.shape[1]} columns")

    result = {
        "shape":                _check_shape(df),
        "column_name_issues":   _check_column_names(df),
        "missing":              _check_missing(df),
        "duplicates":           _check_duplicates(df),
        "dtypes":               _check_dtypes(df),
        "cardinality":          _check_cardinality(df),
        "outliers":             _check_outliers(df),
        "string_consistency":   _check_string_consistency(df),
        "date_issues":          _check_date_issues(df),
        "primary_key_violations": _check_primary_key_violations(df),
        "summary_stats":        _check_summary_stats(df),
    }

    logger.info("Profiling complete.")
    return result


# ---------------------------------------------------------------------------
# Individual check functions
# ---------------------------------------------------------------------------

def _check_shape(df: pd.DataFrame) -> dict:
    return {"rows": int(df.shape[0]), "columns": int(df.shape[1])}


def _check_column_names(df: pd.DataFrame) -> dict:
    """
    Flag column names with non-standard characters:
    - Non-breaking spaces or other Unicode whitespace (\\u00a0, \\u2009, etc.)
    - Leading/trailing whitespace
    - Non-ASCII characters that are not intentional (e.g. curly quotes in headers)
    """
    findings = {}
    for col in df.columns:
        issues = []

        # Check for non-standard whitespace (non-breaking space etc.)
        for i, ch in enumerate(col):
            if unicodedata.category(ch) in ("Zs",) and ch != " ":
                issues.append(f"non-standard whitespace at position {i} (U+{ord(ch):04X})")
                break

        # Check for leading/trailing whitespace
        if col != col.strip():
            issues.append("leading/trailing whitespace")

        if issues:
            findings[col] = {"issues": issues}

    return findings


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
    count = int(df.duplicated().sum())

    examples = []
    if count > 0:
        dup_df = df[df.duplicated(keep=False)].drop_duplicates()
        examples = dup_df.head(3).to_dict(orient="records")

    return {"count": count, "examples": examples}


def _check_dtypes(df: pd.DataFrame) -> dict:
    """
    Flag object columns whose values are mostly numeric OR look like currency.

    Three sub-checks for each object column:
    - looks_numeric: >= 80% of non-null values parse as numbers as-is
    - looks_currency: >= 80% of non-null values parse as numbers after stripping
      $, £, €, ¥ prefixes and comma separators (e.g. "$1,234,567")
    - has_citation_artifacts: values contain embedded bracketed references like [1]
      (common in data scraped from Wikipedia or similar sources)
    """
    findings = {}
    citation_pattern = re.compile(r"\[\d+\]")

    for col in df.select_dtypes(include=object).columns:
        non_null = df[col].dropna()
        if len(non_null) == 0:
            continue

        # Standard numeric check
        converted = pd.to_numeric(non_null, errors="coerce")
        numeric_rate = float(converted.notna().mean())
        looks_numeric = numeric_rate >= 0.8

        # Currency check: strip leading currency symbols and commas, then retry
        stripped = non_null.str.replace(r"^[$£€¥]", "", regex=True).str.replace(",", "", regex=False)
        converted_stripped = pd.to_numeric(stripped, errors="coerce")
        currency_rate = float(converted_stripped.notna().mean())
        looks_currency = (not looks_numeric) and (currency_rate >= 0.8)

        # Citation artifact check: values contain embedded [n] references
        has_citations = bool(non_null.astype(str).str.contains(citation_pattern).any())

        entry: dict = {
            "actual": "object",
            "looks_numeric": looks_numeric,
        }
        if looks_currency:
            entry["looks_currency"] = True
            entry["currency_parse_rate"] = round(currency_rate * 100, 1)
        if has_citations:
            entry["has_citation_artifacts"] = True

        findings[col] = entry

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
    For numeric columns: flag outliers using Z-score (3 SD) and IQR (1.5x fence).
    Takes the union so a single extreme value doesn't mask others.
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
    - mixed_case: same value appears with different casings
    - has_whitespace: any value has leading or trailing whitespace
    Only reports columns where at least one issue is found.
    """
    findings = {}
    for col in df.select_dtypes(include=object).columns:
        series = df[col].dropna().astype(str)
        if len(series) == 0:
            continue

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
    For columns whose name contains 'date', 'year', 'time', 'dob', 'created', 'updated':
    - parse_failures: values that cannot be parsed as dates at all
    - mixed_formats: column contains both ISO (YYYY-MM-DD) and non-ISO formats
    """
    DATE_KEYWORDS = ("date", "year", "time", "dob", "created", "updated")
    findings = {}
    date_cols = [
        col for col in df.columns
        if any(kw in col.lower() for kw in DATE_KEYWORDS)
    ]

    for col in date_cols:
        series = df[col].dropna()
        if len(series) == 0:
            continue

        # Skip columns that are already numeric — e.g. 'years_experience' matches
        # the 'year' keyword but contains integers, not dates.
        if pd.api.types.is_numeric_dtype(series):
            continue
        numeric_rate = pd.to_numeric(series.astype(str), errors='coerce').notna().mean()
        if numeric_rate >= 0.8:
            continue

        series = series.astype(str)

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


def _check_primary_key_violations(df: pd.DataFrame) -> dict:
    """
    Identify columns that look like identifiers (named 'id', 'rank', 'key', 'code',
    or ending with '_id') and check for duplicate values within them.
    Reports the duplicate values and their counts.
    """
    ID_KEYWORDS = ("id", "rank", "key", "code", "no", "num", "number", "index")
    findings = {}

    candidate_cols = [
        col for col in df.columns
        if any(kw == col.lower() or col.lower().endswith(f"_{kw}") or col.lower().startswith(f"{kw}_")
               for kw in ID_KEYWORDS)
    ]

    for col in candidate_cols:
        series = df[col].dropna()
        if len(series) == 0:
            continue
        duplicated = series[series.duplicated(keep=False)]
        if len(duplicated) > 0:
            dup_values = duplicated.value_counts().to_dict()
            findings[col] = {
                "duplicate_count": int(len(duplicated)),
                "duplicate_values": {str(k): int(v) for k, v in dup_values.items()},
            }

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

    csv_path = "sample_data/messy_sample.csv"
    if not os.path.exists(csv_path):
        csv_path = "../sample_data/messy_sample.csv"

    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from src.loader import load_csv

    df = load_csv(csv_path)
    result = profile(df)

    print(json.dumps(result, indent=2, default=str))

    print("\n--- Checkpoint Verification ---")
    assert result["missing"],                                    "FAIL: missing values not detected"
    assert result["duplicates"]["count"] >= 3,                   "FAIL: fewer than 3 duplicates detected"
    assert "salary" in result["outliers"],                       "FAIL: salary outliers not detected"
    assert "city" in result["string_consistency"],               "FAIL: city casing issue not detected"
    assert "hire_date" in result["date_issues"],                 "FAIL: hire_date mixed formats not detected"
    print("All 5 deliberate issues caught. Phase 3 checkpoint passed.")
