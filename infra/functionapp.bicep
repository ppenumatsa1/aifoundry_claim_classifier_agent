param location string
param environmentName string
param tags object = {}
param functionAppName string
param functionStorageAccountName string
param functionStorageBlobServiceUri string
param functionStorageQueueServiceUri string
param functionStorageTableServiceUri string
param dataStorageAccountName string
param dataStorageAccountUrl string
param inputContainer string
param outputContainer string
param appInsightsConnectionString string
param projectEndpoint string
param modelDeploymentName string
param functionDeploymentContainerUrl string
@minValue(1)
@maxValue(1000)
param maximumInstanceCount int = 100
@allowed([
  512
  2048
  4096
])
param functionInstanceMemoryMB int = 2048

var normalizedEnv = toLower(replace(environmentName, ' ', '-'))
var resolvedFunctionAppName = toLower(functionAppName)
var planName = format('{0}-flex-plan', resolvedFunctionAppName)
resource plan 'Microsoft.Web/serverfarms@2023-12-01' = {
  name: planName
  location: location
  tags: tags
  kind: 'functionapp'
  sku: {
    name: 'FC1'
    tier: 'FlexConsumption'
    size: 'FC1'
    family: 'FC'
    capacity: 0
  }
  properties: {
    reserved: true
  }
}

resource site 'Microsoft.Web/sites@2023-12-01' = {
  name: resolvedFunctionAppName
  location: location
  kind: 'functionapp,linux'
  tags: union(tags, {
    'azd-service-name': 'functionApp'
    'azd-environment': normalizedEnv
  })
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    httpsOnly: true
    serverFarmId: plan.id
    siteConfig: {
      minTlsVersion: '1.2'
      ftpsState: 'FtpsOnly'
    }
    functionAppConfig: {
      deployment: {
        storage: {
          type: 'blobContainer'
          value: functionDeploymentContainerUrl
          authentication: {
            type: 'SystemAssignedIdentity'
          }
        }
      }
      scaleAndConcurrency: {
        maximumInstanceCount: maximumInstanceCount
        instanceMemoryMB: functionInstanceMemoryMB
      }
      runtime: {
        name: 'python'
        version: '3.10'
      }
    }
  }
  resource configAppSettings 'config' = {
    name: 'appsettings'
    properties: {
      AzureWebJobsStorage__accountName: functionStorageAccountName
      AzureWebJobsStorage__credential: 'managedidentity'
      AzureWebJobsStorage__blobServiceUri: functionStorageBlobServiceUri
      AzureWebJobsStorage__queueServiceUri: functionStorageQueueServiceUri
      AzureWebJobsStorage__tableServiceUri: functionStorageTableServiceUri
      // BLOB_ACCOUNT for data storage using Managed Identity
      BLOB_ACCOUNT__accountName: dataStorageAccountName
      BLOB_ACCOUNT__blobServiceUri: '${dataStorageAccountUrl}/'
      BLOB_ACCOUNT__credential: 'managedidentity'
      BLOB_ACCOUNT_URL: dataStorageAccountUrl
      INPUT_CONTAINER: inputContainer
      OUTPUT_CONTAINER: outputContainer
      PROJECT_ENDPOINT: projectEndpoint
      MODEL_DEPLOYMENT_NAME: modelDeploymentName
      APPLICATIONINSIGHTS_CONNECTION_STRING: appInsightsConnectionString
    }
  }
}

// Existing storage accounts to scope managed identity role assignments
resource functionStorage 'Microsoft.Storage/storageAccounts@2024-01-01' existing = {
  name: functionStorageAccountName
}

resource dataStorage 'Microsoft.Storage/storageAccounts@2024-01-01' existing = {
  name: dataStorageAccountName
}


// Assign storage data-plane roles to the Function App's system-assigned identity
resource functionStorageBlobContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(functionStorage.id, site.id, 'StorageBlobDataContributor')
  scope: functionStorage
  properties: {
    principalId: site.identity.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'ba92f5b4-2d11-453d-a403-e96b0029c9fe')
  }
}

resource functionStorageQueueContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(functionStorage.id, site.id, 'StorageQueueDataContributor')
  scope: functionStorage
  properties: {
    principalId: site.identity.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '974c5e8b-45b9-4653-ba55-5f855dd0fb88')
  }
}

resource functionStorageTableContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(functionStorage.id, site.id, 'StorageTableDataContributor')
  scope: functionStorage
  properties: {
    principalId: site.identity.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '0a9a7e1f-b9d0-4cc4-a60d-0319b160aaa3')
  }
}

resource dataStorageBlobContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(dataStorage.id, site.id, 'DataStorageBlobContributor')
  scope: dataStorage
  properties: {
    principalId: site.identity.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'ba92f5b4-2d11-453d-a403-e96b0029c9fe')
  }
}


output functionAppName string = site.name
output functionAppResourceId string = site.id
output principalId string = site.identity.principalId
output defaultHostname string = site.properties.defaultHostName
