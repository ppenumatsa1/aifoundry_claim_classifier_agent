param location string
param environmentName string
param tags object = {}
param workspaceResourceId string = ''

var insightsName = toLower(format('{0}-appi-{1}', replace(environmentName, ' ', ''), substring(uniqueString(resourceGroup().id, environmentName), 0, 6)))

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
	name: insightsName
	location: location
	tags: tags
	kind: 'web'
	properties: union({
			Application_Type: 'web'
			DisableIpMasking: true
		},
		empty(workspaceResourceId) ? {} : {
			WorkspaceResourceId: workspaceResourceId
		}
	)
}

output appInsightsName string = appInsights.name
output instrumentationKey string = appInsights.properties.InstrumentationKey
output connectionString string = appInsights.properties.ConnectionString
