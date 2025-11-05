import logging

import pandas as pd
from dotenv import load_dotenv

from .foundry_client import FoundryClient

# Load environment variables from .env file
load_dotenv()


def process_file(input_path: str, output_path: str, batch_size: int = 100):
    """Reads CSV, classifies claims, and writes output CSV."""
    df = pd.read_csv(input_path)
    client = FoundryClient()
    results = []

    for i in range(0, len(df), batch_size):
        batch = df.iloc[i : i + batch_size]
        claims = batch["claim_text"].tolist()
        logging.info(f"Processing rows {i} to {i + len(claims)}")
        responses = client.classify_claims(claims)
        results.extend(responses)

    out_df = pd.DataFrame(results)
    df["classification"] = out_df["classification"]
    df["reasoning"] = out_df["reasoning"]
    df.to_csv(output_path, index=False)
    logging.info(f"Saved output to {output_path}")
