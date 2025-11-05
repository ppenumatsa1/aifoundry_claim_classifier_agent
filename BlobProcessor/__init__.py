import logging
import os

from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv

from function_app.processor import process_file

# Load environment variables from .env file when running locally
load_dotenv()


def main(blob: bytes, name: str):
    """Blob trigger entry point. Invoked when CSV is uploaded to input container."""
    logging.info("Processing blob: %s", name)

    # Environment variables
    account_url = os.environ.get("BLOB_ACCOUNT_URL")
    input_container = os.environ.get("INPUT_CONTAINER", "claims-input")
    output_container = os.environ.get("OUTPUT_CONTAINER", "claims-output")

    if not account_url:
        raise KeyError(
            "BLOB_ACCOUNT_URL environment variable is required when using DefaultAzureCredential."
        )

    credential = DefaultAzureCredential()
    blob_service = BlobServiceClient(account_url=account_url, credential=credential)
    input_blob_client = blob_service.get_blob_client(input_container, name)
    output_blob_client = blob_service.get_blob_client(output_container, name)

    # Download blob locally (temp)
    local_input_path = f"/tmp/{name}"
    with open(local_input_path, "wb") as f:
        f.write(blob)

    local_output_path = f"/tmp/output_{name}"

    # Process CSV file via Foundry agent
    process_file(local_input_path, local_output_path)

    # Upload output CSV
    with open(local_output_path, "rb") as data:
        output_blob_client.upload_blob(data, overwrite=True)

    logging.info("Completed processing for %s", name)
