"""
AI Data Quality Checker — entry point.

Usage:
    python run_check.py --file path/to/data.csv
    python run_check.py --file path/to/data.csv --output path/to/reports/
"""

import argparse
import logging
import sys
import time


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "AI Data Quality Checker — audit any CSV and generate "
            "a plain-English report using Claude."
        )
    )
    parser.add_argument(
        "--file",
        required=True,
        metavar="PATH",
        help="Path to the CSV file to check.",
    )
    parser.add_argument(
        "--output",
        default="reports/",
        metavar="DIR",
        help="Directory to write the report into (default: reports/).",
    )
    return parser.parse_args()


def main() -> None:
    setup_logging()
    logger = logging.getLogger(__name__)
    args = parse_args()

    logger.info("=" * 55)
    logger.info("  AI Data Quality Checker")
    logger.info(f"  File  : {args.file}")
    logger.info(f"  Output: {args.output}")
    logger.info("=" * 55)

    t_start = time.time()

    # Step 1: Load
    logger.info("[1/4] Loading CSV...")
    t = time.time()
    from src.loader import load_csv
    df = load_csv(args.file)
    logger.info(
        f"      {df.shape[0]} rows x {df.shape[1]} columns "
        f"({time.time() - t:.2f}s)"
    )

    # Step 2: Profile
    logger.info("[2/4] Running quality checks...")
    t = time.time()
    from src.profiler import profile
    findings = profile(df)
    issues_found = sum([
        bool(findings.get("missing")),
        findings.get("duplicates", {}).get("count", 0) > 0,
        bool(findings.get("outliers")),
        bool(findings.get("string_consistency")),
        bool(findings.get("date_issues")),
    ])
    logger.info(f"      {issues_found} issue categories detected ({time.time() - t:.2f}s)")

    # Step 3: Interpret via Claude
    logger.info("[3/4] Sending findings to Claude for analysis...")
    t = time.time()
    from src.analyst import interpret
    analysis = interpret(findings, args.file)
    logger.info(f"      Analysis received ({time.time() - t:.2f}s)")

    # Step 4: Generate report
    logger.info("[4/4] Generating report...")
    t = time.time()
    from src.reporter import generate_report
    output_path = generate_report(args.file, findings, analysis, args.output)
    logger.info(f"      Report written ({time.time() - t:.2f}s)")

    total = time.time() - t_start
    logger.info("=" * 55)
    logger.info(f"  Report: {output_path}")
    logger.info(f"  Total runtime: {total:.2f}s")
    logger.info("=" * 55)


if __name__ == "__main__":
    main()
