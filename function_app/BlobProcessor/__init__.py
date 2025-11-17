import logging
import os
import tempfile
from pathlib import Path
from urllib.parse import urlparse, unquote

import azure.functions as func
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv

try:
    # When imported as package (tests, local dev)
    from function_app.processor import process_file
except (ImportError, ModuleNotFoundError):
    # When deployed to Azure (processor.py is at root)
    from processor import process_file

# Load environment variables from .env file when running locally
load_dotenv()

logger = logging.getLogger(__name__)


def main(event: func.EventGridEvent):
    """Handle BlobCreated events by downloading, processing, and re-uploading CSVs."""
    data = event.get_json() or {}
    blob_url = data.get("url")
    if not blob_url:
        logger.warning("Event %s missing blob URL", getattr(event, "id", "<unknown>"))
        return

    account_url = os.getenv("BLOB_ACCOUNT_URL")
    input_container = os.getenv("INPUT_CONTAINER")
    output_container = os.getenv("OUTPUT_CONTAINER")
    if not account_url or not input_container or not output_container:
        raise RuntimeError(
            "BLOB_ACCOUNT_URL, INPUT_CONTAINER, and OUTPUT_CONTAINER must be set"
        )

    blob_service = BlobServiceClient(
        account_url=account_url,
        credential=DefaultAzureCredential(exclude_interactive_browser_credential=True),
    )

    parsed = urlparse(blob_url)
    path_parts = parsed.path.lstrip("/").split("/", 1)
    if len(path_parts) != 2:
        logger.warning(
            "Event %s missing container/blob path", getattr(event, "id", "<unknown>")
        )
        return

    container, encoded_blob_path = path_parts
    blob_path = unquote(encoded_blob_path)
    if container != input_container:
        logger.info(
            "Skipping blob %s in container %s (expected %s)",
            blob_path,
            container,
            input_container,
        )
        return

    logger.info("Processing blob %s from %s", blob_path, container)

    input_blob = blob_service.get_blob_client(container=container, blob=blob_path)
    with tempfile.TemporaryDirectory() as tmp:
        local_input = Path(tmp) / Path(blob_path).name
        local_output = Path(tmp) / f"output_{Path(blob_path).name}"

        logger.info("Downloading blob to %s", local_input)
        with open(local_input, "wb") as handle:
            handle.write(input_blob.download_blob().readall())

        logger.info("Running classifier on %s", local_input)
        actual_output = Path(process_file(str(local_input), str(local_output)))

        output_blob_path = Path(blob_path)
        if output_blob_path.parent != Path("."):
            final_blob_path = str(output_blob_path.parent / actual_output.name)
        else:
            final_blob_path = actual_output.name

        output_blob = blob_service.get_blob_client(
            container=output_container, blob=final_blob_path
        )

        logger.info(
            "Uploading processed results from %s to %s/%s",
            actual_output,
            output_container,
            final_blob_path,
        )
        with open(actual_output, "rb") as handle:
            output_blob.upload_blob(handle, overwrite=True)

        try:
            input_blob.delete_blob()
            logger.info("Deleted input blob %s from container %s", blob_path, container)
        except Exception as exc:
            logger.warning("Failed to delete input blob %s: %s", blob_path, exc)

    logger.info("Completed processing for %s", blob_path)
