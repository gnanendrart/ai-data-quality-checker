"""
Phase 1 checkpoint: verify the Claude API connection works.

Usage:
    python src/test_api.py
"""

import os
import logging
from dotenv import load_dotenv
import anthropic

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


def test_api_connection() -> None:
    """Send a test message to Claude and print the response."""
    load_dotenv()

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError(
            "ANTHROPIC_API_KEY not found. "
            "Copy .env.example to .env and add your key."
        )

    logger.info("API key loaded. Sending test message to Claude...")

    client = anthropic.Anthropic(api_key=api_key)

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=100,
        messages=[
            {"role": "user", "content": "Say hello and confirm you are working."}
        ]
    )

    response_text = message.content[0].text
    logger.info("Response received successfully.")

    print("\n--- Claude Response ---")
    print(response_text)
    print("----------------------")
    print("\nPhase 1 checkpoint passed. API connection confirmed.")


if __name__ == "__main__":
    test_api_connection()
