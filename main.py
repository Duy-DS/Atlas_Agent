from pathlib import Path
import os

import pandas as pd
import requests


DATA_DIR = Path("/data")
PUBLIC_TEST_PATH = DATA_DIR / "public_test.csv"
PRIVATE_TEST_PATH = DATA_DIR / "private_test.csv"

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
MODEL_NAME = os.getenv("MODEL_NAME", "qwen3:0.6b")


def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    public_df = pd.read_csv(PUBLIC_TEST_PATH)
    private_df = pd.read_csv(PRIVATE_TEST_PATH)

    print(f"Loaded public_test.csv: {public_df.shape}")
    print(f"Loaded private_test.csv: {private_df.shape}")

    return public_df, private_df


def ask_ollama(prompt: str) -> str:
    response = requests.post(
        f"{OLLAMA_BASE_URL}/api/generate",
        json={
            "model": MODEL_NAME,
            "prompt": prompt,
            "stream": False,
        },
        timeout=180,
    )
    response.raise_for_status()
    return response.json()["response"]


def summarize_dataframe(df: pd.DataFrame, name: str) -> str:
    columns = list(df.columns)
    sample = df.head(3).to_dict(orient="records")

    prompt = f"""
You are analyzing a CSV file named {name}.

Columns:
{columns}

First 3 rows:
{sample}

Briefly describe what this dataset seems to contain.
"""
    return ask_ollama(prompt)


def main():
    public_df, private_df = load_data()

    public_summary = summarize_dataframe(public_df, "public_test.csv")
    private_summary = summarize_dataframe(private_df, "private_test.csv")

    print("\n=== Public Summary ===")
    print(public_summary)

    print("\n=== Private Summary ===")
    print(private_summary)


if __name__ == "__main__":
    main()