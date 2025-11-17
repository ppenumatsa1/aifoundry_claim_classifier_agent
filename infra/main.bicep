targetScope = 'subscription'

param location string = deployment().location
@description('Short environment name (e.g. dev, test, prod).')
param environmentName string
@description('Optional override for the Function App resource name. Defaults to <env>-claims-func.')
param functionAppName string = ''
@description('Azure AI Foundry project endpoint, e.g. https://<project>.project.azure-ai.azure.com.')
param projectEndpoint string
@description('Azure AI Foundry model deployment name to invoke.')
param modelDeploymentName string
@description('Resource group containing the Azure AI (Cognitive Services) account backing the Foundry project. Leave blank to skip role assignment.')
param projectAccountResourceGroup string = ''
param tags object = {}

var sanitizedEnv = toLower(replace(environmentName, ' ', '-'))
var resolvedFunctionAppName = empty(functionAppName) ? toLower(format('{0}-claims-func', sanitizedEnv)) : toLower(functionAppName)
var resourceGroupName = format('{0}-claims-rg', sanitizedEnv)
var resourceTags = union(tags, {
  // Required to bypass default policy set in training subscriptions
  SecurityControl: 'Ignore'
})
var projectEndpointHost = split(replace(replace(projectEndpoint, 'https://', ''), 'http://', ''), '/')[0]
var projectAccountName = split(projectEndpointHost, '.')[0]

// Create an isolated resource group for each environment deployment
resource functionResourceGroup 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: resourceGroupName
  location: location
  tags: resourceTags
}

module storage 'storage.bicep' = {
  name: 'storage'
  scope: resourceGroup(functionResourceGroup.name)
  params: {
    location: location
    environmentName: sanitizedEnv
    tags: resourceTags
  }
}

module insights 'appinsights.bicep' = {
  name: 'appInsights'
  scope: resourceGroup(functionResourceGroup.name)
  params: {
    location: location
    environmentName: sanitizedEnv
    tags: resourceTags
  }
}

module functionApp 'functionapp.bicep' = {
  name: 'functionApp'
  scope: resourceGroup(functionResourceGroup.name)
  params: {
    location: location
    environmentName: sanitizedEnv
    tags: resourceTags
    functionAppName: resolvedFunctionAppName
    functionStorageAccountName: storage.outputs.functionStorageAccountName
    functionStorageBlobServiceUri: storage.outputs.functionStorageBlobServiceUri
    functionStorageQueueServiceUri: storage.outputs.functionStorageQueueServiceUri
    functionStorageTableServiceUri: storage.outputs.functionStorageTableServiceUri
    dataStorageAccountName: storage.outputs.dataStorageAccountName
    dataStorageAccountUrl: storage.outputs.dataStorageAccountUrl
    inputContainer: storage.outputs.inputContainer
    outputContainer: storage.outputs.outputContainer
    appInsightsConnectionString: insights.outputs.connectionString
    projectEndpoint: projectEndpoint
    modelDeploymentName: modelDeploymentName
    functionDeploymentContainerUrl: storage.outputs.functionDeploymentContainerUrl
  }
}


module foundryRoleAssignment 'assign-foundry-role.bicep' = if (!empty(projectAccountResourceGroup)) {
  name: 'foundryRoleAssignment'
  scope: resourceGroup(subscription().subscriptionId, projectAccountResourceGroup)
  params: {
    principalId: functionApp.outputs.principalId
    projectAccountName: projectAccountName
  }
}

output functionAppName string = functionApp.outputs.functionAppName
output functionAppHostName string = functionApp.outputs.defaultHostname
output functionDataStorageUrl string = storage.outputs.dataStorageAccountUrl
output dataStorageAccountName string = storage.outputs.dataStorageAccountName
output dataStorageResourceId string = storage.outputs.dataStorageResourceId
output inputContainerName string = storage.outputs.inputContainer
output outputContainerName string = storage.outputs.outputContainer
output resourceGroupName string = functionResourceGroup.name

// Service outputs for azd
output AZURE_FUNCTION_APP_NAME string = functionApp.outputs.functionAppName
output AZURE_RESOURCE_GROUP string = functionResourceGroup.name
output AZURE_DATA_STORAGE_ACCOUNT_NAME string = storage.outputs.dataStorageAccountName
output AZURE_DATA_STORAGE_ACCOUNT_ID string = storage.outputs.dataStorageResourceId

// Environment variables for the function app
output BLOB_ACCOUNT_URL string = storage.outputs.dataStorageAccountUrl
output INPUT_CONTAINER string = storage.outputs.inputContainer
output OUTPUT_CONTAINER string = storage.outputs.outputContainer
