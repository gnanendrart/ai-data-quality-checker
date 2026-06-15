# AI Data Quality Checker

Point it at any CSV. It runs 11 automated quality checks using pandas, sends the findings to Claude, and writes a plain-English markdown report telling you what's wrong and what to fix — ranked by severity, not by column order.

---

## Why This Exists

I spent years doing these checks by hand before data went out to stakeholders.

One project: billing records feeding a downstream revenue report. The source system had duplicate rows and a handful of impossible values. Nobody caught it before the report ran. The discrepancy took two weeks to trace back to the source. One automated pass at load time would have caught it in seconds.

Another project: two systems feeding the same dashboard. The city column in one had "Calgary," "calgary," and "CALGARY" treated as three distinct values. Every location-level analysis was wrong until someone noticed the totals didn't add up.

Both failures were preventable. The checks existed — they just weren't automated. This tool automates them.

---

## What It Does

```
python run_check.py --file your_data.csv
```

One command runs the full pipeline:

1. Loads the CSV
2. Profiles it across 11 quality dimensions
3. Sends structured findings to Claude for analyst-level interpretation
4. Writes a markdown report to `reports/`

The report leads with an executive summary and a prioritized issue list. The raw stats are collapsed at the bottom for anyone who wants to dig in.

---

## Checks Performed

| Check | What It Catches |
|-------|----------------|
| Column name issues | Non-breaking spaces (U+00A0) and other invisible Unicode characters in column headers — the kind that break joins silently |
| Missing values | Null count and percentage per column |
| Duplicate rows | Exact row duplicates with examples |
| Data type issues | Object columns whose values are mostly numeric; currency strings (`$`, `£`, `€`, `¥`) stored as text; embedded citation artifacts (`[1]`, `[2]`) from web-scraped data |
| Cardinality | Columns with only one unique value |
| Outliers | Values flagged by Z-score (3 SD) or IQR (1.5x fence) — both methods run so a single extreme outlier doesn't mask others |
| String consistency | Mixed casing ("Calgary"/"calgary"/"CALGARY") and leading/trailing whitespace |
| Date format issues | Columns with date-like names checked for parse failures and mixed formats |
| Primary key violations | Columns matching ID patterns checked for duplicate values that should be unique |
| Summary statistics | Min, max, mean, median for all numeric columns |

---

## Example Output

See [`examples/sample_report.md`](examples/sample_report.md) for a full report generated against a real dirty dataset: Wikipedia-scraped data on women's concert tours. It found non-breaking spaces in column names, citation artifacts across four columns, three currency fields stored as text, a duplicate in what should be a unique rank column, and 70% missing data in two peak columns.

Excerpt from the executive summary:

> This dataset has moderate data quality issues that stem primarily from its origin as web-scraped content. While the core structure is sound (no duplicate rows, consistent strings), the data contains pervasive citation artifacts, systematic missing values in two columns, and inconsistent data type handling for currency fields. The duplicate rank value and unparseable dates add minor friction. These issues are manageable but require cleaning before the dataset can be reliably analyzed or merged with other sources.

---

## Installation

```bash
git clone git@github.com:gnanendrart/ai-data-quality-checker.git
cd ai-data-quality-checker

conda activate data-eng   # or your Python 3.11+ environment
pip install -r requirements.txt

cp .env.example .env
# Add your ANTHROPIC_API_KEY to .env
```

---

## Usage

```bash
# Check any CSV
python run_check.py --file path/to/your_data.csv

# Specify a custom output directory
python run_check.py --file path/to/your_data.csv --output path/to/reports/
```

Report is saved to `reports/{filename}_{timestamp}.md`.

---

## Tech Stack

| Component | Tool |
|-----------|------|
| Language | Python 3.11+ |
| Data profiling | pandas + numpy |
| Outlier detection | Z-score (3 SD) and IQR (1.5x fence) |
| LLM interpretation | Claude Haiku via `anthropic` SDK |
| CLI | argparse |
| Report output | Markdown |
| Environment | python-dotenv |

---

## Project Structure

```
ai-data-quality-checker/
    run_check.py          # Entry point
    src/
        loader.py         # CSV loading and validation
        profiler.py       # All 11 quality checks
        analyst.py        # Claude API: interprets findings
        reporter.py       # Assembles and writes the markdown report
    examples/
        sample_report.md  # Sample report generated against a real dirty dataset
    sample_data/
        messy_sample.csv  # Dirty sample dataset for testing
    reports/              # Output — one .md report per run
```
