# Insurance Claim Fraud Classifier (Azure AI Foundry Agent)

## Overview

This project processes insurance claim CSV files, classifies each claim (e.g., Fraud / Not Fraud), and generates reasoning using Azure AI Foundry Agents. It is triggered automatically when a new CSV file is uploaded to Azure Blob Storage.

## 🏗️ User Flow

1. CSV uploaded → Blob Storage (`input` container)
2. Azure Function Trigger → Downloads CSV
3. Function invokes Azure AI Foundry Agent for each claim
4. Outputs new CSV with `classification` and `reasoning`
5. Uploads timestamped result to Blob Storage (`output` container) and deletes the processed source blob
6. Sends logs and metrics to Azure Application Insights for observability

## 📂 Project Structure

```
infra/                 # IaC (Bicep modules)
│  ├─ main.bicep
│  ├─ functionapp.bicep
│  ├─ storage.bicep
│  ├─ appinsights.bicep
│  └─ assign-foundry-role.bicep
function_app/          # Azure Function project root
│  ├─ host.json
│  ├─ requirements.txt
│  ├─ BlobProcessor/    # Event Grid trigger entrypoint
│  ├─ processor.py
│  ├─ foundry_client.py
│  └─ prompts/
scripts/               # Deployment helpers
│  └─ create_event_subscription.sh
tests/                 # Unit tests
data/                  # Sample CSVs for local testing
azure.yaml             # azd environment configuration
README.md
```

## ⚙️ Environment Variables

| Variable                         | Description                                                                                           | Set By |
| -------------------------------- | ----------------------------------------------------------------------------------------------------- | ------ |
| `FUNCTION_APP_NAME`              | Name for the Azure Function App                                                                       | User   |
| `PROJECT_ENDPOINT`               | Azure AI Foundry project endpoint (`https://<resource>.services.ai.azure.com/api/projects/<project>`) | User   |
| `MODEL_DEPLOYMENT_NAME`          | Name of the model deployment used by the agent                                                        | User   |
| `PROJECT_ACCOUNT_RESOURCE_GROUP` | Resource group containing the AI Foundry account                                                      | User   |
| `BLOB_ACCOUNT_URL`               | Blob Storage account URL (auto-generated after provisioning)                                          | azd    |
| `INPUT_CONTAINER`                | Container for input CSV files (`claims-input`)                                                        | azd    |
| `OUTPUT_CONTAINER`               | Container for output CSV files (`claims-output`)                                                      | azd    |

## 🚀 Getting Started

### Prerequisites

- Install Azure Developer CLI (azd):

  ```bash
  curl -fsSL https://aka.ms/install-azd.sh | bash
  ```

- Install Azure CLI (if not already):

  ```bash
  curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
  ```

- Login to Azure and select your subscription:

  ```bash
  az login
  az account set --subscription <your-subscription-id>
  ```

### 1. Download and Setup

```bash
git clone https://github.com/<owner>/aifoundry_claim_classifier_agent.git
cd aifoundry_claim_classifier_agent
pip install -r function_app/requirements.txt
```

### 2. Run Tests

```bash
pytest -v
```

### 3. Configure azd Environment

```bash
# Create environment
azd env new <env-name>

# Set required variables
azd env set FUNCTION_APP_NAME "<your-function-app-name>"
azd env set PROJECT_ENDPOINT "https://<resource>.services.ai.azure.com/api/projects/<project>"
azd env set MODEL_DEPLOYMENT_NAME "<deployment-name>"
azd env set PROJECT_ACCOUNT_RESOURCE_GROUP "<ai-foundry-resource-group>"
```

Storage account details are automatically set after provisioning.

### 4. Deploy to Azure

```bash
# Provision infrastructure
azd provision

# Deploy application
azd deploy

# (Optional) Create Event Grid subscription
bash scripts/create_event_subscription.sh
```

To clean up resources:

```bash
azd down
```

## 🔄 CI/CD

The GitHub workflow `.github/workflows/azure-dev.yml` provisions a fresh resource group per environment and deploys via azd using OIDC. Managed identity is enabled on the Function App; the pipeline never handles storage keys.

## 🔁 Processing Details

- Output CSV filenames have a `_YYYYMMDD_HHMMSS` suffix so each run produces a unique blob even when the source name is reused.
- The Blob trigger honours any folder structure on the input and writes the timestamped file back to the matching path in the output container.
- After a successful upload the original input blob is deleted, keeping the `claims-input` container tidy.
- Claims are processed in configurable batches (default 100 rows) to balance latency and throughput.
- Logs, metrics, and exceptions are sent to Azure Application Insights for monitoring.
- All behaviors have unit tests in `tests/` to guard against regressions.
