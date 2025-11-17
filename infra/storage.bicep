param location string
param environmentName string
param tags object = {}

var sanitizedEnv = toLower(replace(environmentName, ' ', ''))
var baseHash = uniqueString(resourceGroup().id, environmentName)
var functionStorageAccountName = toLower(format('st{0}{1}', take(replace(sanitizedEnv, '-', ''), 12), substring(baseHash, 0, 6)))
var dataStorageAccountName = toLower(format('st{0}{1}data', take(replace(sanitizedEnv, '-', ''), 9), substring(baseHash, 0, 6)))
var inputContainerName = 'claims-input'
var outputContainerName = 'claims-output'
var functionPackageContainerName = 'function-packages'

resource functionStorage 'Microsoft.Storage/storageAccounts@2024-01-01' = {
  name: functionStorageAccountName
  location: location
  tags: tags
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    supportsHttpsTrafficOnly: true
    allowSharedKeyAccess: false
    defaultToOAuthAuthentication: true
  }
}
resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-01-01' = {
  name: 'default'
  parent: functionStorage
}

resource functionPackageContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  name: functionPackageContainerName
  parent: blobService
}

resource dataStorage 'Microsoft.Storage/storageAccounts@2024-01-01' = {
  name: dataStorageAccountName
  location: location
  tags: tags
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    defaultToOAuthAuthentication: true
    supportsHttpsTrafficOnly: true
    allowSharedKeyAccess: false
  }
}
resource dataBlobService 'Microsoft.Storage/storageAccounts/blobServices@2023-01-01' = {
  name: 'default'
  parent: dataStorage
}

resource dataInputContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  name: inputContainerName
  parent: dataBlobService
}

resource dataOutputContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  name: outputContainerName
  parent: dataBlobService
}


output functionStorageAccountName string = functionStorage.name
output functionStorageResourceId string = functionStorage.id
output functionStorageBlobServiceUri string = functionStorage.properties.primaryEndpoints.blob
output functionStorageQueueServiceUri string = functionStorage.properties.primaryEndpoints.queue
output functionStorageTableServiceUri string = functionStorage.properties.primaryEndpoints.table
output functionDeploymentContainerUrl string = uri(functionStorage.properties.primaryEndpoints.blob, functionPackageContainerName)
output dataStorageAccountUrl string = format('https://{0}.blob.{1}', dataStorage.name, environment().suffixes.storage)
output dataStorageAccountName string = dataStorage.name
output dataStorageResourceId string = dataStorage.id
output dataStorageAccountUrlPublic string = format('https://{0}.blob.{1}', dataStorage.name, environment().suffixes.storage)
output inputContainer string = inputContainerName
output outputContainer string = outputContainerName
