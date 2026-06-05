# AI Data Quality Checker

Point it at any CSV. It runs 8 automated quality checks using pandas, sends the findings to Claude, and writes a plain-English markdown report telling you what's wrong and what to fix — ranked by severity, not by column order.

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
2. Profiles it across 8 quality dimensions
3. Sends structured findings to Claude for analyst-level interpretation
4. Writes a markdown report to `reports/`

The report leads with an executive summary and a prioritized issue list. The raw stats are collapsed at the bottom for anyone who wants to dig in.

---

## Checks Performed

| Check | What It Catches |
|-------|----------------|
| Missing values | Null count and percentage per column |
| Duplicate rows | Exact row duplicates with examples |
| Data type issues | Object columns whose values are mostly numeric |
| Cardinality | Columns with only one unique value |
| Outliers | Values flagged by Z-score (3 SD) or IQR (1.5x fence) — both methods run so a single extreme outlier doesn't mask others |
| String consistency | Mixed casing ("Calgary"/"calgary"/"CALGARY") and leading/trailing whitespace |
| Date format issues | Columns named `*date*` checked for parse failures and mixed formats |
| Summary statistics | Min, max, mean, median for all numeric columns |

---

## Example Output

Running against the included sample dataset (`sample_data/messy_sample.csv`):

**Executive summary:**

> This dataset has moderate quality issues that must be resolved before analysis. The core problems are incomplete data (with years_experience missing in 10.5% of rows), three exact duplicate records, obvious data entry errors (a negative salary and an implausible $999,999 value), inconsistent formatting in city names and hire dates, and a small number of missing values in key employment fields.

**Issue detail (missing values):**

| Column | Null Count | % Missing |
|--------|-----------|-----------|
| `years_experience` | 4 | 10.5% |
| `department` | 3 | 7.9% |
| `hire_date` | 3 | 7.9% |
| `salary` | 1 | 2.6% |

**Outliers detected:**

| Column | Count | Values |
|--------|-------|--------|
| `salary` | 2 | `999999.0, -5000.0` |

The full report includes prioritized issues, specific recommended fixes, and a collapsible raw profile block.

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
| Data profiling | pandas |
| Outlier detection | pandas + numpy (Z-score and IQR) |
| LLM interpretation | Claude API via `anthropic` SDK |
| CLI | argparse |
| Report output | Markdown |
| Environment | python-dotenv |

---

## Project Structure

```
data-quality-checker/
    run_check.py          # Entry point
    src/
        loader.py         # CSV loading and validation
        profiler.py       # All 8 quality checks
        analyst.py        # Claude API: interprets findings
        reporter.py       # Assembles and writes the markdown report
    sample_data/
        messy_sample.csv  # Dirty sample dataset for testing
    reports/              # Output — one .md report per run
```
