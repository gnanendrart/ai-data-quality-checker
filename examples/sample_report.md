# Data Quality Report: `my_file (1).csv`

| | |
|---|---|
| **Dataset** | `my_file (1).csv` |
| **Run timestamp** | 2026-06-15 18:01:19 |
| **Rows** | 20 |
| **Columns** | 11 |

## Executive Summary

This dataset has moderate data quality issues that stem primarily from its origin as web-scraped content. While the core structure is sound (no duplicate rows, consistent strings), the data contains pervasive citation artifacts, systematic missing values in two columns, and inconsistent data type handling for currency fields. The duplicate rank value and unparseable dates add minor friction. These issues are manageable but require cleaning before the dataset can be reliably analyzed or merged with other sources.

## Issue Details

### Column Name Issues

- **`Actual gross`**: non-standard whitespace at position 6 (U+00A0)
- **`Adjusted gross (in 2022 dollars)`**: non-standard whitespace at position 8 (U+00A0)


### Missing Values

| Column | Null Count | % Missing |
|--------|-----------|-----------|
| `All Time Peak` | 14 | 70.0% |
| `Peak` | 11 | 55.0% |


### Duplicate Rows

No duplicate rows detected.


### Data Type / Content Issues

| Column | Issue |
|--------|-------|
| `Peak` | Contains embedded citation references (e.g. `[1]`, `[2]`) |
| `All Time Peak` | Contains embedded citation references (e.g. `[1]`, `[2]`) |
| `Actual gross` | Currency stored as text (90.0% parseable after stripping symbols) |
| `Adjusted gross (in 2022 dollars)` | Currency stored as text (100.0% parseable after stripping symbols) |
| `Tour title` | Contains embedded citation references (e.g. `[1]`, `[2]`) |
| `Average gross` | Currency stored as text (100.0% parseable after stripping symbols) |
| `Ref.` | Contains embedded citation references (e.g. `[1]`, `[2]`) |


### Primary Key Violations

- **`Rank`**: 2 rows share the same value — `7` (x2)


### Outliers

| Column | Count | Values |
|--------|-------|--------|
| `Shows` | 1 | `325.0` |


### String Consistency

No string consistency issues detected.


### Date Format Issues

- **`All Time Peak`**: 6 unparseable value(s)
- **`Year(s)`**: 14 unparseable value(s)


## Prioritized Issues

(Most Critical First)

1. **Embedded citation references across multiple columns (Peak, All Time Peak, Tour title, Ref.)** — This is classic web scraping artifact. Citations like "[1]" pollute the actual data values, making analysis impossible and breaking any text-based comparisons or aggregations. This affects at least 4 columns and likely every row in some columns.

2. **55–70% missing values in Peak and All Time Peak columns** — With over half the data missing in these columns, any analysis relying on them will be severely compromised. You cannot reliably compute statistics or trends on columns this sparse. These columns may need to be dropped entirely or their purpose reconsidered.

3. **Currency values stored as text instead of numeric** — Three columns (Actual gross, Adjusted gross, Average gross) are stored as strings when they should be numbers. While they're mostly parseable, this prevents direct numerical calculations and creates processing friction. The 90% parseability of "Actual gross" suggests ~2 rows have malformed values.

4. **Non-standard whitespace in column names** — The non-breaking spaces (U+00A0) in 'Actual gross' and 'Adjusted gross (in 2022 dollars)' will cause downstream tools to fail silently or create duplicate column references. This breaks automation and is easily overlooked.

5. **Duplicate Rank values** — Two rows both have Rank=7, violating what should be a unique identifier. This creates ambiguity about which row is "7th" and breaks join operations keyed on Rank.

6. **Unparseable dates** — 14 out of 20 rows (70%) have unparseable Year(s) values, and 6 rows have unparseable All Time Peak dates. This suggests inconsistent date formats or corrupted entries during scraping.

7. **Outlier in Shows column** — One row has 325 shows versus a median of 87, roughly 3.7× the typical value. Verify this is a real anomaly (perhaps a long-running tour) and not a data entry error.

## Recommended Fixes

1. **Remove or strip citation references** — Use regex to identify and remove patterns like `[0-9]+` from Peak, All Time Peak, Tour title, and Ref. columns. Validate the resulting values make sense after removal.

2. **Decide on Peak/All Time Peak columns** — Assess whether these columns are critical to your analysis. If yes, investigate the data source to backfill missing values. If no, drop them to reduce noise. Do not impute them.

3. **Convert currency columns to numeric** — Strip `$`, `,`, and any other symbols from Actual gross, Adjusted gross, and Average gross. Convert to float. Flag and review the ~2 unparseable rows in Actual gross separately.

4. **Standardize column names** — Replace non-breaking spaces (U+00A0) with regular spaces in column headers. Consider renaming to shorter, code-friendly names (e.g., 'actual_gross', 'adjusted_gross_2022').

5. **Fix Rank duplicates** — Examine the two rows with Rank=7. Determine if one is a data entry error or if the original source has ambiguous rankings. Correct or remove one row.

6. **Standardize and parse dates** — Identify the intended date format for Year(s) and All Time Peak. Reparse or manually correct the 14 + 6 unparseable rows. If dates cannot be recovered, document why and decide whether to drop those rows.

7. **Validate the Shows=325 outlier** — Cross-reference against your source data. If legitimate, document it. If erroneous, correct it.

## Raw Profile Stats

<details>
<summary>Click to expand</summary>


```json
{
  "shape": {
    "rows": 20,
    "columns": 11
  },
  "column_name_issues": {
    "Actual\u00a0gross": {
      "issues": [
        "non-standard whitespace at position 6 (U+00A0)"
      ]
    },
    "Adjusted\u00a0gross (in 2022 dollars)": {
      "issues": [
        "non-standard whitespace at position 8 (U+00A0)"
      ]
    }
  },
  "missing": {
    "Peak": {
      "count": 11,
      "pct": 55.0
    },
    "All Time Peak": {
      "count": 14,
      "pct": 70.0
    }
  },
  "duplicates": {
    "count": 0,
    "examples": []
  },
  "dtypes": {
    "Peak": {
      "actual": "object",
      "looks_numeric": false,
      "has_citation_artifacts": true
    },
    "All Time Peak": {
      "actual": "object",
      "looks_numeric": false,
      "has_citation_artifacts": true
    },
    "Actual\u00a0gross": {
      "actual": "object",
      "looks_numeric": false,
      "looks_currency": true,
      "currency_parse_rate": 90.0
    },
    "Adjusted\u00a0gross (in 2022 dollars)": {
      "actual": "object",
      "looks_numeric": false,
      "looks_currency": true,
      "currency_parse_rate": 100.0
    },
    "Artist": {
      "actual": "object",
      "looks_numeric": false
    },
    "Tour title": {
      "actual": "object",
      "looks_numeric": false,
      "has_citation_artifacts": true
    },
    "Year(s)": {
      "actual": "object",
      "looks_numeric": false
    },
    "Average gross": {
      "actual": "object",
      "looks_numeric": false,
      "looks_currency": true,
      "currency_parse_rate": 100.0
    },
    "Ref.": {
      "actual": "object",
      "looks_numeric": false,
      "has_citation_artifacts": true
    }
  },
  "cardinality": {
    "Peak": {
      "unique_count": 7,
      "single_value": false
    },
    "All Time Peak": {
      "unique_count": 6,
      "single_value": false
    },
    "Actual\u00a0gross": {
      "unique_count": 20,
      "single_value": false
    },
    "Adjusted\u00a0gross (in 2022 dollars)": {
      "unique_count": 20,
      "single_value": false
    },
    "Artist": {
      "unique_count": 9,
      "single_value": false
    },
    "Tour title": {
      "unique_count": 20,
      "single_value": false
    },
    "Year(s)": {
      "unique_count": 16,
      "single_value": false
    },
    "Average gross": {
      "unique_count": 20,
      "single_value": false
    },
    "Ref.": {
      "unique_count": 20,
      "single_value": false
    }
  },
  "outliers": {
    "Shows": {
      "count": 1,
      "values": [
        325.0
      ]
    }
  },
  "string_consistency": {},
  "date_issues": {
    "All Time Peak": {
      "parse_failures": 6
    },
    "Year(s)": {
      "parse_failures": 14
    }
  },
  "primary_key_violations": {
    "Rank": {
      "duplicate_count": 2,
      "duplicate_values": {
        "7": 2
      }
    }
  },
  "summary_stats": {
    "Rank": {
      "min": 1.0,
      "max": 20.0,
      "mean": 10.45,
      "median": 10.5
    },
    "Shows": {
      "min": 41.0,
      "max": 325.0,
      "mean": 110.0,
      "median": 87.0
    }
  }
}
```

</details>
