import pandas as pd

from function_app.processor import process_file


def test_process_file(monkeypatch, tmp_path):
    """Basic test that ensures process_file runs end-to-end with mock client."""
    # Create mock input CSV
    input_file = tmp_path / "claims.csv"
    pd.DataFrame({"claim_text": ["Test claim one", "Suspicious claim two"]}).to_csv(
        input_file, index=False
    )

    # Patch FoundryClient
    class MockClient:
        def classify_claims(self, claims):
            return [
                {"classification": "Not Fraud", "reasoning": "Looks legitimate"}
                for _ in claims
            ]

    monkeypatch.setattr("function_app.processor.FoundryClient", MockClient)

    output_file = tmp_path / "output.csv"
    process_file(str(input_file), str(output_file))

    out_df = pd.read_csv(output_file)
    assert "classification" in out_df.columns
    assert "reasoning" in out_df.columns
    assert len(out_df) == 2
