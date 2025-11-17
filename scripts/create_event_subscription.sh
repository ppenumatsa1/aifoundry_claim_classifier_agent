#!/usr/bin/env bash
set -euo pipefail

if ! command -v az >/dev/null 2>&1; then
  echo "Azure CLI (az) is required" >&2
  exit 1
fi

workspace_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$workspace_dir"


if [[ -f ./.env ]]; then
  set -a
  # shellcheck disable=SC1091
  source ./.env
  set +a
fi

get_azd_env() {
  if command -v azd >/dev/null 2>&1; then
    azd env get-value "$1" 2>/dev/null || true
  fi
}

subscription_id=${AZURE_SUBSCRIPTION_ID:-$(get_azd_env AZURE_SUBSCRIPTION_ID)}
resource_group=${AZURE_RESOURCE_GROUP:-$(get_azd_env AZURE_RESOURCE_GROUP)}
function_app=${AZURE_FUNCTION_APP_NAME:-$(get_azd_env AZURE_FUNCTION_APP_NAME)}
data_storage_account=${AZURE_DATA_STORAGE_ACCOUNT_NAME:-$(get_azd_env AZURE_DATA_STORAGE_ACCOUNT_NAME)}
input_container=${INPUT_CONTAINER:-$(get_azd_env INPUT_CONTAINER)}
function_name=${EVENT_GRID_FUNCTION_NAME:-BlobProcessor}

if [[ -z "$subscription_id" || -z "$resource_group" || -z "$function_app" || -z "$data_storage_account" || -z "$input_container" ]]; then
  echo "Missing required environment values. Populate .env or export AZURE_* variables before running." >&2
  exit 1
fi

source_resource_id="/subscriptions/${subscription_id}/resourceGroups/${resource_group}/providers/Microsoft.Storage/storageAccounts/${data_storage_account}"
function_resource_id="/subscriptions/${subscription_id}/resourceGroups/${resource_group}/providers/Microsoft.Web/sites/${function_app}/functions/${function_name}"
subscription_name="${function_app}-blobcreated"
subject_prefix="/blobServices/default/containers/${input_container}/blobs/"

if az eventgrid event-subscription show --name "$subscription_name" --source-resource-id "$source_resource_id" >/dev/null 2>&1; then
  echo "Event Grid subscription ${subscription_name} already exists; skipping creation."
  exit 0
fi

az_eventgrid_args=(
  --name "$subscription_name"
  --source-resource-id "$source_resource_id"
  --endpoint-type azurefunction
  --endpoint "$function_resource_id"
  --included-event-types Microsoft.Storage.BlobCreated
  --subject-begins-with "$subject_prefix"
)

az eventgrid event-subscription create "${az_eventgrid_args[@]}"
