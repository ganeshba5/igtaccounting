#!/bin/bash
# Script to check and fix Service Principal permissions

echo "=== Service Principal Permission Check ==="
echo ""

# Get resource group name (update this)
RESOURCE_GROUP="your-resource-group"

# Get Service Principal Client ID from Azure AD App Registration
# Replace with your actual client ID from GitHub Secrets -> AZURE_CREDENTIALS -> clientId
CLIENT_ID="your-service-principal-client-id"

echo "Checking permissions for Service Principal: $CLIENT_ID"
echo "Resource Group: $RESOURCE_GROUP"
echo ""

# Get subscription ID
SUBSCRIPTION_ID=$(az account show --query id -o tsv)
echo "Subscription ID: $SUBSCRIPTION_ID"
echo ""

# Check current role assignments
echo "Current role assignments:"
az role assignment list \
  --assignee $CLIENT_ID \
  --scope /subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP \
  --query '[].{Role:roleDefinitionName, Scope:scope}' \
  -o table

echo ""
echo "If you don't see 'Contributor' role, run this command:"
echo ""
echo "az role assignment create \\"
echo "  --assignee $CLIENT_ID \\"
echo "  --role \"Contributor\" \\"
echo "  --scope /subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP"
echo ""

