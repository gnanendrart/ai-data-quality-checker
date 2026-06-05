"""
Phase 2: CSV loader with error handling and basic validation.
"""

import logging
import pandas as pd

logger = logging.getLogger(__name__)


def load_csv(filepath: str) -> pd.DataFrame:
    """
    Load a CSV file and return a DataFrame.

    Args:
        filepath: Path to the CSV file.

    Returns:
        pd.DataFrame with the loaded data.

    Raises:
        FileNotFoundError: If the file does not exist.
        pd.errors.ParserError: If the file cannot be parsed as CSV.
    """
    logger.info(f"Loading CSV: {filepath}")

    try:
        df = pd.read_csv(filepath)

    except FileNotFoundError:
        logger.error(f"File not found: {filepath}")
        raise FileNotFoundError(
            f"CSV file not found: {filepath}. "
            "Check that the path is correct and the file exists."
        )

    except pd.errors.ParserError as e:
        logger.error(f"Failed to parse CSV: {filepath} — {e}")
        raise pd.errors.ParserError(
            f"Could not parse '{filepath}' as a CSV file. "
            f"Error: {e}"
        )

    except Exception as e:
        logger.error(f"Unexpected error loading '{filepath}': {e}")
        raise

    rows, cols = df.shape
    logger.info(f"Loaded {rows} rows x {cols} columns from '{filepath}'")

    return df


if __name__ == "__main__":
    # Quick smoke test against the sample file
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s"
    )

    df = load_csv("sample_data/messy_sample.csv")
    print(df.head())
    print(f"\nShape: {df.shape}")
    print(f"Columns: {list(df.columns)}")
    print("\nPhase 2 checkpoint passed. Loader works correctly.")
