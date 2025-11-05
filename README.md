# Insurance Claim Fraud Classifier (Azure AI Foundry Agent)

## Overview

This project processes insurance claim CSV files, classifies each claim (e.g., Fraud / Not Fraud), and generates reasoning using Azure AI Foundry Agents.  
It is triggered automatically when a new CSV file is uploaded to Azure Blob Storage.

## 🏗️ Architecture

1. CSV uploaded → Blob Storage (`input` container)
2. Azure Function Trigger → Downloads CSV
3. Function invokes Azure AI Foundry Agent for each claim
4. Outputs new CSV with `classification` and `reasoning`
5. Uploads result to Blob Storage (`output` container)

## 📂 Project Structure

```
infra/                 # IaC (Bicep/Terraform)
.github/               # CI/CD pipelines
BlobProcessor/         # Azure Function (blob trigger)
function_app/          # Core business logic and Foundry client
│  ├─ processor.py
│  ├─ foundry_client.py
│  └─ prompts/
tests/                 # Unit tests
data/                  # Sample CSVs for local testing
README.md
requirements.txt
host.json
```

## ⚙️ Environment Variables

| Variable                | Description                                                                                           |
| ----------------------- | ----------------------------------------------------------------------------------------------------- |
| `PROJECT_ENDPOINT`      | Azure AI Foundry project endpoint (`https://<resource>.services.ai.azure.com/api/projects/<project>`) |
| `MODEL_DEPLOYMENT_NAME` | Name of the model deployment used by the agent                                                        |
| `BLOB_ACCOUNT_URL`      | Blob Storage account URL (`https://<account>.blob.core.windows.net`)                                  |
| `INPUT_CONTAINER`       | Container for input CSV files                                                                         |
| `OUTPUT_CONTAINER`      | Container for output CSV files                                                                        |

## 🚀 Local Development

1. Create `.env` file with variables above
2. Install dependencies

   ```bash
   pip install -r requirements.txt
   ```

3. Run locally with sample CSV
   ```bash
   python - <<'PY'
   from function_app.processor import process_file
   ```

process_file("data/sample_claims.csv", "/tmp/output.csv")
PY

````

## ✅ Testing

Run unit tests using:

```bash
pytest -v
````

## 🧰 Deployment

- Use Azure Functions with Blob Trigger.
- Connect to Azure AI Foundry via managed identity or service principal.
- Use GitHub Actions or Bicep templates for CI/CD.

## 📈 Future Enhancements

- Batch parallelization for large CSVs
- Integration with Service Bus for queue-based orchestration
- Multi-agent setup (classification + reasoning verifier)
- Streamlined observability via App Insights
