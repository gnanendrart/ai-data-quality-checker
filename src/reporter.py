"""
Phase 5: Report generator.
Assembles a markdown data quality report from profiler findings and Claude's analysis.
"""

import json
import logging
import math
import os
from datetime import datetime

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_report(
    filename: str,
    profile: dict,
    analysis: str,
    output_dir: str = "reports",
) -> str:
    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = os.path.splitext(os.path.basename(filename))[0]
    output_path = os.path.join(output_dir, f"{base_name}_{timestamp}.md")

    report = _assemble_report(filename, profile, analysis, timestamp)
    save_report(report, output_path)

    logger.info(f"Report saved to: {output_path}")
    return output_path


def save_report(report_content: str, output_path: str) -> None:
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report_content)


# ---------------------------------------------------------------------------
# Report assembly
# ---------------------------------------------------------------------------

def _assemble_report(filename, profile, analysis, timestamp):
    shape = profile.get("shape", {})
    rows = shape.get("rows", "?")
    cols = shape.get("columns", "?")
    run_dt = datetime.strptime(timestamp, "%Y%m%d_%H%M%S").strftime("%Y-%m-%d %H:%M:%S")

    # Use only the filename in the report header, not the full system path
    display_name = os.path.basename(filename)

    executive_summary, issues_section, recommendations = _parse_analysis(analysis)

    sections = []

    # Header
    sections.append(f"# Data Quality Report: `{display_name}`\n")
    sections.append(
        f"| | |\n"
        f"|---|---|\n"
        f"| **Dataset** | `{display_name}` |\n"
        f"| **Run timestamp** | {run_dt} |\n"
        f"| **Rows** | {rows} |\n"
        f"| **Columns** | {cols} |\n"
    )

    # Executive Summary
    sections.append("## Executive Summary\n")
    sections.append(executive_summary.strip() + "\n")

    # Issue Details
    sections.append("## Issue Details\n")
    sections.append(_format_column_name_issues(profile.get("column_name_issues", {})))
    sections.append(_format_missing(profile.get("missing", {})))
    sections.append(_format_duplicates(profile.get("duplicates", {})))
    sections.append(_format_dtype_issues(profile.get("dtypes", {})))
    sections.append(_format_primary_key_violations(profile.get("primary_key_violations", {})))
    sections.append(_format_outliers(profile.get("outliers", {})))
    sections.append(_format_string_consistency(profile.get("string_consistency", {})))
    sections.append(_format_date_issues(profile.get("date_issues", {})))

    # Analyst Issues from Claude
    if issues_section.strip():
        sections.append("## Prioritized Issues\n")
        sections.append(issues_section.strip() + "\n")

    # Recommendations
    sections.append("## Recommended Fixes\n")
    sections.append(recommendations.strip() + "\n")

    # Raw Profile Stats (collapsible)
    sections.append("## Raw Profile Stats\n")
    sections.append("<details>\n<summary>Click to expand</summary>\n")
    sections.append("\n```json\n" + json.dumps(_sanitize(profile), indent=2) + "\n```\n")
    sections.append("</details>\n")

    return "\n".join(sections)


# ---------------------------------------------------------------------------
# Section formatters
# ---------------------------------------------------------------------------

def _format_column_name_issues(col_name_issues):
    if not col_name_issues:
        return "### Column Name Issues\n\nNo column name issues detected.\n\n"
    lines = ["### Column Name Issues\n"]
    for col, info in col_name_issues.items():
        issues_str = "; ".join(info["issues"])
        lines.append(f"- **`{col}`**: {issues_str}")
    lines.append("")
    return "\n".join(lines) + "\n"


def _format_missing(missing):
    if not missing:
        return "### Missing Values\n\nNo missing values detected.\n\n"
    lines = [
        "### Missing Values\n",
        "| Column | Null Count | % Missing |",
        "|--------|-----------|-----------|",
    ]
    for col, stats in sorted(missing.items(), key=lambda x: -x[1]["count"]):
        lines.append(f"| `{col}` | {stats['count']} | {stats['pct']}% |")
    lines.append("")
    return "\n".join(lines) + "\n"


def _format_duplicates(duplicates):
    count = duplicates.get("count", 0)
    if count == 0:
        return "### Duplicate Rows\n\nNo duplicate rows detected.\n\n"
    examples = duplicates.get("examples", [])
    lines = [f"### Duplicate Rows\n", f"**{count} duplicate row(s) detected.**\n"]
    if examples:
        lines.append("Example duplicated records:\n")
        for ex in examples:
            lines.append(
                "```\n" +
                "\n".join(f"  {k}: {v}" for k, v in ex.items()) +
                "\n```\n"
            )
    lines.append("")
    return "\n".join(lines) + "\n"


def _format_dtype_issues(dtypes):
    flagged = {
        col: v for col, v in dtypes.items()
        if v.get("looks_numeric") or v.get("looks_currency") or v.get("has_citation_artifacts")
    }
    if not flagged:
        return "### Data Type / Content Issues\n\nNo data type issues detected.\n\n"
    lines = [
        "### Data Type / Content Issues\n",
        "| Column | Issue |",
        "|--------|-------|",
    ]
    for col, v in flagged.items():
        parts = []
        if v.get("looks_numeric"):
            parts.append("Stored as text, values are numeric")
        if v.get("looks_currency"):
            rate = v.get("currency_parse_rate", "?")
            parts.append(f"Currency stored as text ({rate}% parseable after stripping symbols)")
        if v.get("has_citation_artifacts"):
            parts.append("Contains embedded citation references (e.g. `[1]`, `[2]`)")
        lines.append(f"| `{col}` | {'; '.join(parts)} |")
    lines.append("")
    return "\n".join(lines) + "\n"


def _format_primary_key_violations(pk_violations):
    if not pk_violations:
        return "### Primary Key Violations\n\nNo primary key violations detected.\n\n"
    lines = ["### Primary Key Violations\n"]
    for col, stats in pk_violations.items():
        dup_vals = ", ".join(
            f"`{k}` (x{v})" for k, v in stats["duplicate_values"].items()
        )
        lines.append(
            f"- **`{col}`**: {stats['duplicate_count']} rows share the same value — {dup_vals}"
        )
    lines.append("")
    return "\n".join(lines) + "\n"


def _format_outliers(outliers):
    if not outliers:
        return "### Outliers\n\nNo outliers detected.\n\n"
    lines = [
        "### Outliers\n",
        "| Column | Count | Values |",
        "|--------|-------|--------|",
    ]
    for col, stats in outliers.items():
        vals = ", ".join(str(v) for v in stats["values"])
        lines.append(f"| `{col}` | {stats['count']} | `{vals}` |")
    lines.append("")
    return "\n".join(lines) + "\n"


def _format_string_consistency(string_issues):
    if not string_issues:
        return "### String Consistency\n\nNo string consistency issues detected.\n\n"
    lines = [
        "### String Consistency\n",
        "| Column | Mixed Case | Whitespace Issues |",
        "|--------|-----------|-------------------|",
    ]
    for col, stats in string_issues.items():
        mixed = "Yes" if stats.get("mixed_case") else "No"
        ws = "Yes" if stats.get("has_whitespace") else "No"
        lines.append(f"| `{col}` | {mixed} | {ws} |")
    lines.append("")
    return "\n".join(lines) + "\n"


def _format_date_issues(date_issues):
    if not date_issues:
        return "### Date Format Issues\n\nNo date format issues detected.\n\n"
    lines = ["### Date Format Issues\n"]
    for col, stats in date_issues.items():
        parts = []
        if stats.get("parse_failures"):
            parts.append(f"{stats['parse_failures']} unparseable value(s)")
        if stats.get("mixed_formats"):
            parts.append(
                f"mixed formats — {stats.get('non_iso_count', '?')} non-ISO value(s)"
            )
        lines.append(f"- **`{col}`**: {'; '.join(parts)}")
    lines.append("")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sanitize(obj):
    """Replace float NaN/Inf with None for valid JSON output."""
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize(v) for v in obj]
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    return obj


def _parse_analysis(analysis):
    """Extract the three sections from Claude's response."""
    SUMMARY_HEADER = "## Executive Summary"
    ISSUES_HEADER = "## Issues"
    FIXES_HEADER = "## Recommended Fixes"

    def _extract(text, start_marker, end_markers):
        start = text.find(start_marker)
        if start == -1:
            return ""
        start += len(start_marker)
        end = len(text)
        for marker in end_markers:
            pos = text.find(marker, start)
            if pos != -1:
                end = min(end, pos)
        return text[start:end].strip()

    summary = _extract(analysis, SUMMARY_HEADER, [ISSUES_HEADER, FIXES_HEADER])
    issues = _extract(analysis, ISSUES_HEADER, [FIXES_HEADER])
    fixes = _extract(analysis, FIXES_HEADER, [])

    if not summary and not fixes:
        return analysis, "", ""

    return summary, issues, fixes
