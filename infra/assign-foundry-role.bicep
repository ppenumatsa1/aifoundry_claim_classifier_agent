targetScope = 'resourceGroup'

param principalId string
param projectAccountName string
@description('Role definition to grant the Function App access to manage Azure AI agents.')
param roleDefinitionId string = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '4d97b98b-1d4f-4787-a291-c67834d212e7')

resource projectAccount 'Microsoft.CognitiveServices/accounts@2023-05-01' existing = {
  name: projectAccountName
}

resource foundryOpenAiContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(projectAccount.id, principalId, 'FoundryOpenAiContributor')
  scope: projectAccount
  properties: {
    principalId: principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: roleDefinitionId
  }
}

// Add Azure AI User role assignment
resource foundryAIUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(projectAccount.id, principalId, 'FoundryAIUser')
  scope: projectAccount
  properties: {
    principalId: principalId
    principalType: 'ServicePrincipal'
    // Azure AI User built-in role definition ID
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'a80b1c59-3c2c-4b7b-9c7d-8b8f8b7e3c7d')
  }
}
