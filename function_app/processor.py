import os
import datetime
from urllib.parse import urlparse
from azure.storage.blob import BlobClient
import pandas as pd
from dotenv import load_dotenv

try:
    # Try package-relative import (for local tests)
    from function_app.foundry_client import FoundryClient
    from function_app.logging_config import setup_logger
except ImportError:
    # Fall back to root-level import (for Azure flat deployment)
    from foundry_client import FoundryClient
    from logging_config import setup_logger

# Load environment variables from .env file
load_dotenv()

logger = setup_logger(__name__)


def process_file(input_path: str, output_path: str, batch_size: int = 100):
    """Reads CSV, classifies claims, writes output CSV, and returns the written path."""
    logger.info(f"Starting file processing: {input_path}")

    try:
        df = pd.read_csv(input_path)
        logger.info(f"Loaded CSV with {len(df)} rows")
    except Exception as e:
        logger.error(f"Failed to read CSV from {input_path}: {e}")
        raise

    # Append timestamp to output file
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    if ".csv" in output_path:
        output_path = output_path.replace(".csv", f"_{ts}.csv")
    else:
        output_path = f"{output_path}_{ts}"

    client = FoundryClient()
    results = []
    total_batches = (len(df) + batch_size - 1) // batch_size
    logger.info(
        f"Processing {len(df)} claims in {total_batches} batches of size {batch_size}"
    )

    for batch_num, i in enumerate(range(0, len(df), batch_size), 1):
        batch = df.iloc[i : i + batch_size]
        claims = batch["claim_text"].tolist()
        logger.info(
            f"Batch {batch_num}/{total_batches}: Processing rows {i} to {i + len(claims) - 1}"
        )

        try:
            responses = client.classify_claims(claims)
            results.extend(responses)
            logger.info(
                f"Batch {batch_num}/{total_batches}: Successfully classified {len(responses)} claims"
            )
        except Exception as e:
            logger.error(
                f"Batch {batch_num}/{total_batches}: Failed to classify claims: {e}"
            )
            raise

    logger.info(
        f"Classification complete. Creating output dataframe with {len(results)} results"
    )
    out_df = pd.DataFrame(results)
    if out_df.empty:
        logger.error("No classification results returned for %s rows", len(df))
        raise ValueError(
            "Classification results were empty; see earlier logs for details"
        )

    df = df.reset_index(drop=True)
    out_df = out_df.reset_index(drop=True)
    df["classification"] = out_df["classification"]
    df["reasoning"] = out_df["reasoning"]

    try:
        df.to_csv(output_path, index=False)
        logger.info(f"Successfully saved output to {output_path}")
    except Exception as e:
        logger.error(f"Failed to write output CSV to {output_path}: {e}")
        raise

    # Delete input blob if it is a blob URL or path
    if (
        input_path.startswith("https://")
        or input_path.startswith("http://")
        or "/blob.core.windows.net/" in input_path
    ):
        try:
            # Parse container and blob name from input_path
            parsed = urlparse(input_path)
            path_parts = parsed.path.lstrip("/").split("/", 1)
            if len(path_parts) == 2:
                container, blob = path_parts
                blob_client = BlobClient.from_blob_url(input_path)
                blob_client.delete_blob()
                logger.info(f"Deleted input blob: {input_path}")
        except Exception as e:
            logger.warning(f"Failed to delete input blob {input_path}: {e}")

    return output_path
