"""
Phase 4: Claude analyst.
Sends profiler findings to Claude and returns a plain-English interpretation.
"""

import json
import logging
import os
from dotenv import load_dotenv
import anthropic

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a senior data analyst reviewing an automated data quality report.
You have been given structured quality findings for a CSV dataset.
Your job is to interpret these findings for a data team and produce:

1. A one-paragraph executive summary of overall data quality
2. A prioritized list of issues, most critical first, with a plain-English explanation of why each matters
3. A list of specific, actionable recommended fixes

Be direct. Do not repeat the raw numbers back — interpret them.
A "5% null rate in a primary key column" is critical. A "2% null rate in an optional comments field" is low priority.
Apply that kind of judgment throughout.

Format your response with these exact section headers:
## Executive Summary
## Issues (Most Critical First)
## Recommended Fixes"""


def _build_prompt(profile_dict: dict, filename: str) -> str:
    """Format the profiler output into a readable prompt for Claude."""
    shape = profile_dict.get("shape", {})
    rows = shape.get("rows", "unknown")
    cols = shape.get("columns", "unknown")

    sections = [
        f"Dataset: {filename}",
        f"Size: {rows} rows x {cols} columns",
        "",
        "--- Quality Findings ---",
        "",
    ]

    # Column name issues
    col_name_issues = profile_dict.get("column_name_issues", {})
    if col_name_issues:
        sections.append("COLUMN NAME ISSUES:")
        for col, info in col_name_issues.items():
            sections.append(f"  '{col}': {'; '.join(info['issues'])}")
    else:
        sections.append("COLUMN NAME ISSUES: None detected")
    sections.append("")

    # Missing values
    missing = profile_dict.get("missing", {})
    if missing:
        sections.append("MISSING VALUES:")
        for col, stats in missing.items():
            sections.append(f"  {col}: {stats['count']} nulls ({stats['pct']}% of rows)")
    else:
        sections.append("MISSING VALUES: None detected")
    sections.append("")

    # Duplicates
    dupes = profile_dict.get("duplicates", {})
    dupe_count = dupes.get("count", 0)
    if dupe_count > 0:
        sections.append(f"DUPLICATE ROWS: {dupe_count} duplicate rows detected")
        examples = dupes.get("examples", [])
        if examples:
            sections.append(f"  Example duplicated record: {json.dumps(examples[0], default=str)}")
    else:
        sections.append("DUPLICATE ROWS: None detected")
    sections.append("")

    # Data type issues
    dtypes = profile_dict.get("dtypes", {})
    flagged = {
        col: v for col, v in dtypes.items()
        if v.get("looks_numeric") or v.get("looks_currency") or v.get("has_citation_artifacts")
    }
    if flagged:
        sections.append("DATA TYPE / CONTENT ISSUES:")
        for col, v in flagged.items():
            parts = []
            if v.get("looks_numeric"):
                parts.append("stored as text, values look numeric")
            if v.get("looks_currency"):
                parts.append(
                    f"stored as text, values look like currency "
                    f"({v.get('currency_parse_rate', '?')}% parseable after stripping symbols)"
                )
            if v.get("has_citation_artifacts"):
                parts.append("contains embedded citation references (e.g. [1], [2]) — likely scraped data")
            sections.append(f"  {col}: {'; '.join(parts)}")
    else:
        sections.append("DATA TYPE ISSUES: None detected")
    sections.append("")

    # Primary key violations
    pk_violations = profile_dict.get("primary_key_violations", {})
    if pk_violations:
        sections.append("PRIMARY KEY / IDENTIFIER VIOLATIONS:")
        for col, stats in pk_violations.items():
            vals = ", ".join(f"{k} (×{v})" for k, v in stats["duplicate_values"].items())
            sections.append(
                f"  {col}: {stats['duplicate_count']} rows share duplicate values — {vals}"
            )
    else:
        sections.append("PRIMARY KEY VIOLATIONS: None detected")
    sections.append("")

    # Outliers
    outliers = profile_dict.get("outliers", {})
    if outliers:
        sections.append("OUTLIERS (Z-score or IQR method):")
        for col, stats in outliers.items():
            sections.append(
                f"  {col}: {stats['count']} outlier(s) — values: {stats['values']}"
            )
    else:
        sections.append("OUTLIERS: None detected")
    sections.append("")

    # String consistency
    string_issues = profile_dict.get("string_consistency", {})
    if string_issues:
        sections.append("STRING CONSISTENCY ISSUES:")
        for col, stats in string_issues.items():
            issues = []
            if stats.get("mixed_case"):
                issues.append("mixed casing (e.g. Calgary/calgary/CALGARY)")
            if stats.get("has_whitespace"):
                issues.append("leading/trailing whitespace")
            sections.append(f"  {col}: {', '.join(issues)}")
    else:
        sections.append("STRING CONSISTENCY: No issues detected")
    sections.append("")

    # Date issues
    date_issues = profile_dict.get("date_issues", {})
    if date_issues:
        sections.append("DATE FORMAT ISSUES:")
        for col, stats in date_issues.items():
            parts = []
            if stats.get("parse_failures"):
                parts.append(f"{stats['parse_failures']} unparseable values")
            if stats.get("mixed_formats"):
                parts.append(
                    f"mixed formats ({stats.get('non_iso_count', '?')} non-ISO values)"
                )
            sections.append(f"  {col}: {', '.join(parts)}")
    else:
        sections.append("DATE FORMAT ISSUES: None detected")
    sections.append("")

    # Summary stats
    stats = profile_dict.get("summary_stats", {})
    if stats:
        sections.append("NUMERIC COLUMN RANGES:")
        for col, s in stats.items():
            if col.lower() in ("record_id", "rank", "id"):
                continue
            sections.append(
                f"  {col}: min={s['min']}, max={s['max']}, "
                f"mean={s['mean']}, median={s['median']}"
            )

    return "\n".join(sections)


def interpret(profile_dict: dict, filename: str) -> str:
    """
    Send profiler findings to Claude and return a plain-English interpretation.
    """
    load_dotenv()
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError(
            "ANTHROPIC_API_KEY not found. "
            "Check that .env exists and contains your key."
        )

    prompt = _build_prompt(profile_dict, filename)
    logger.info(f"Sending quality findings for '{filename}' to Claude...")
    logger.debug(f"Prompt:\n{prompt}")

    client = anthropic.Anthropic(api_key=api_key)

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    response = message.content[0].text
    logger.info("Analysis received from Claude.")
    return response
