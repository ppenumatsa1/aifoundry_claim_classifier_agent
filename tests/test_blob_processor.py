from __future__ import annotations

import io
from pathlib import Path

import pytest

from function_app.BlobProcessor.__init__ import main as blob_main


class FakeBlobClient:
    def __init__(self, contents: bytes):
        self._contents = contents
        self.uploaded: io.BytesIO | None = None
        self.deleted: bool = False

    def download_blob(self):
        class Downloader:
            def __init__(self, payload: bytes):
                self._payload = payload

            def readall(self) -> bytes:
                return self._payload

        return Downloader(self._contents)

    def upload_blob(self, data, overwrite: bool):
        if not overwrite:
            raise AssertionError("overwrite flag must be True")
        payload = data.read()
        self.uploaded = io.BytesIO(payload)

    def delete_blob(self):
        self.deleted = True


class FakeBlobServiceClient:
    def __init__(self, input_client: FakeBlobClient, output_client: FakeBlobClient):
        self._input_client = input_client
        self._output_client = output_client
        self.requests: list[tuple[str, str]] = []

    def get_blob_client(self, *, container: str, blob: str):
        self.requests.append((container, blob))
        if container == "claims-input":
            return self._input_client
        if container == "claims-output":
            return self._output_client
        raise AssertionError(f"Unexpected container {container}")


class FakeEvent:
    def __init__(self):
        self.id = "evt-1"
        self.event_type = "Microsoft.Storage.BlobCreated"
        self.subject = "/blobServices/default/containers/claims-input/blobs/test.csv"
        self._data = {
            "url": "https://acct.blob.core.windows.net/claims-input/test.csv",
        }

    def get_json(self):
        return self._data


@pytest.fixture(autouse=True)
def set_env(monkeypatch):
    monkeypatch.setenv("INPUT_CONTAINER", "claims-input")
    monkeypatch.setenv("OUTPUT_CONTAINER", "claims-output")
    monkeypatch.setenv("BLOB_ACCOUNT_URL", "https://acct.blob.core.windows.net")


def test_main_processes_blob(monkeypatch, tmp_path):
    input_blob = FakeBlobClient(b"col\nvalue\n")
    output_blob = FakeBlobClient(b"")
    fake_service = FakeBlobServiceClient(input_blob, output_blob)

    def fake_process_file(src: str, dest: str):
        final_path = Path(dest).with_name("processed-test.csv")
        with open(final_path, "w", encoding="utf-8") as handle:
            handle.write("col,classification\nvalue,ok\n")
        return str(final_path)

    monkeypatch.setattr(
        "function_app.BlobProcessor.__init__.BlobServiceClient",
        lambda **_: fake_service,
    )
    monkeypatch.setattr(
        "function_app.BlobProcessor.__init__.DefaultAzureCredential",
        lambda **_: object(),
    )
    monkeypatch.setattr(
        "function_app.BlobProcessor.__init__.process_file", fake_process_file
    )

    blob_main(FakeEvent())

    assert output_blob.uploaded is not None
    assert output_blob.uploaded.getvalue() == b"col,classification\nvalue,ok\n"
    assert ("claims-output", "processed-test.csv") in fake_service.requests
    assert input_blob.deleted is True


def test_main_handles_percent_encoded_paths(monkeypatch):
    input_blob = FakeBlobClient(b"col\nvalue\n")
    output_blob = FakeBlobClient(b"")
    fake_service = FakeBlobServiceClient(input_blob, output_blob)

    class EncodedEvent(FakeEvent):
        def __init__(self):
            super().__init__()
            self._data["url"] = (
                "https://acct.blob.core.windows.net/claims-input/folder%2Fmy%20file.csv"
            )

    def fake_process_file(src: str, dest: str):
        final_path = Path(dest).with_name("processed-encoded.csv")
        with open(final_path, "w", encoding="utf-8") as handle:
            handle.write("col,classification\nvalue,ok\n")
        return str(final_path)

    monkeypatch.setattr(
        "function_app.BlobProcessor.__init__.BlobServiceClient",
        lambda **_: fake_service,
    )
    monkeypatch.setattr(
        "function_app.BlobProcessor.__init__.DefaultAzureCredential",
        lambda **_: object(),
    )
    monkeypatch.setattr(
        "function_app.BlobProcessor.__init__.process_file", fake_process_file
    )

    blob_main(EncodedEvent())

    assert ("claims-input", "folder/my file.csv") in fake_service.requests
    assert ("claims-output", "folder/processed-encoded.csv") in fake_service.requests
