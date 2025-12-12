# Azure Service Principal Setup for GitHub Actions

This guide explains how to set up an Azure Service Principal for secure GitHub Actions deployment without needing to enable basic authentication or use publish profiles.

## Why Use Service Principal?

- **More Secure**: Uses OAuth token-based authentication instead of basic auth
- **No Basic Auth Required**: Doesn't require enabling basic authentication on App Service
- **Better Access Control**: Can be scoped to specific resource groups
- **Recommended by Microsoft**: Best practice for CI/CD pipelines

## Method 1: Using Azure CLI (Easiest)

### Prerequisites
- Azure CLI installed ([Install guide](https://docs.microsoft.com/cli/azure/install-azure-cli))
- Owner or Contributor access to the Azure subscription

### Steps

1. **Login to Azure**:
   ```bash
   az login
   ```

2. **Get your subscription ID**:
   ```bash
   az account show --query id -o tsv
   ```
   Copy this value for the next step.

3. **Create Service Principal**:
   ```bash
   az ad sp create-for-rbac --name "github-actions-accounting" \
     --role contributor \
     --scopes /subscriptions/YOUR_SUBSCRIPTION_ID/resourceGroups/YOUR_RESOURCE_GROUP \
     --sdk-auth
   ```
   
   Replace:
   - `YOUR_SUBSCRIPTION_ID`: Your Azure subscription ID from step 2
   - `YOUR_RESOURCE_GROUP`: Your resource group name (e.g., `accounting-rg`)

4. **Copy the JSON output**:
   The command will output JSON like this:
   ```json
   {
     "clientId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
     "clientSecret": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
     "subscriptionId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
     "tenantId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
     "activeDirectoryEndpointUrl": "https://login.microsoftonline.com",
     "resourceManagerEndpointUrl": "https://management.azure.com/",
     "activeDirectoryGraphResourceId": "https://graph.windows.net/",
     "sqlManagementEndpointUrl": "https://management.core.windows.net:8443/",
     "galleryEndpointUrl": "https://gallery.azure.com/",
     "managementEndpointUrl": "https://management.core.windows.net/"
   }
   ```

5. **Add to GitHub Secrets**:
   - Go to your GitHub repository
   - Settings → Secrets and variables → Actions
   - Click "New repository secret"
   - Name: `AZURE_CREDENTIALS`
   - Value: Paste the entire JSON output (all in one line is fine)

## Method 2: Using Azure Portal

### Step 1: Create App Registration

1. Go to [Azure Portal](https://portal.azure.com)
2. Navigate to **Azure Active Directory** → **App registrations**
3. Click **New registration**
4. Fill in:
   - **Name**: `github-actions-accounting`
   - **Supported account types**: Accounts in this organizational directory only
   - Click **Register**

5. **Copy the following values** (you'll need them later):
   - **Application (client) ID**: Copy this
   - **Directory (tenant) ID**: Copy this

### Step 2: Create Client Secret

1. In your app registration, go to **Certificates & secrets**
2. Click **New client secret**
3. Fill in:
   - **Description**: `GitHub Actions deployment`
   - **Expires**: Choose an appropriate expiration (12-24 months)
4. Click **Add**
5. **IMPORTANT**: Copy the **Value** immediately (you won't see it again)

### Step 3: Assign Permissions

1. Go to your **Resource Group** in Azure Portal
2. Click **Access control (IAM)**
3. Click **Add role assignment**
4. Fill in:
   - **Role**: Select **Contributor**
   - **Assign access to**: User, group, or service principal
   - **Select**: Search for `github-actions-accounting` and select it
5. Click **Save**

### Step 4: Get Subscription ID

1. Go to **Subscriptions** in Azure Portal
2. Click on your subscription
3. Copy the **Subscription ID**

### Step 5: Create JSON Credentials

Create a JSON file with the following structure (replace placeholders):

```json
{
  "clientId": "your-application-client-id",
  "clientSecret": "your-client-secret-value",
  "subscriptionId": "your-subscription-id",
  "tenantId": "your-tenant-id",
  "activeDirectoryEndpointUrl": "https://login.microsoftonline.com",
  "resourceManagerEndpointUrl": "https://management.azure.com/",
  "activeDirectoryGraphResourceId": "https://graph.windows.net/",
  "sqlManagementEndpointUrl": "https://management.core.windows.net:8443/",
  "galleryEndpointUrl": "https://gallery.azure.com/",
  "managementEndpointUrl": "https://management.core.windows.net/"
}
```

### Step 6: Add to GitHub Secrets

1. Go to your GitHub repository
2. Settings → Secrets and variables → Actions
3. Click "New repository secret"
4. Name: `AZURE_CREDENTIALS`
5. Value: Paste the entire JSON (you can paste it all on one line)

## Verify Setup

After adding the secret, your GitHub Actions workflow should be able to:
- Authenticate with Azure
- Deploy to App Service
- Access Azure resources

## Troubleshooting

### "Authentication failed" error

- Verify the JSON format is correct
- Check that client secret hasn't expired
- Ensure service principal has Contributor role on the resource group

### "Authorization failed" error

- Verify role assignment was successful
- Check that scope includes the resource group
- Try assigning role at subscription level for testing

### Secret expired

- Create a new client secret in Azure Portal
- Update the `AZURE_CREDENTIALS` secret in GitHub with new JSON

## Security Best Practices

1. **Scope Permissions**: Only grant Contributor role to the specific resource group, not the entire subscription
2. **Rotate Secrets**: Regularly rotate client secrets (every 6-12 months)
3. **Use Separate Service Principals**: Use different service principals for different environments (dev, staging, prod)
4. **Monitor Usage**: Regularly review Azure AD sign-in logs for service principal usage

## Alternative: More Restrictive Permissions

If you want to be more restrictive, you can create a custom role with only the permissions needed for deployment:

```bash
az role definition create --role-definition '{
  "Name": "GitHub Actions Deploy",
  "Description": "Custom role for GitHub Actions deployment",
  "Actions": [
    "Microsoft.Web/sites/*",
    "Microsoft.Web/sites/publishxml/Action"
  ],
  "AssignableScopes": ["/subscriptions/YOUR_SUBSCRIPTION_ID"]
}'

az role assignment create --role "GitHub Actions Deploy" \
  --assignee "your-service-principal-id" \
  --scope /subscriptions/YOUR_SUBSCRIPTION_ID/resourceGroups/YOUR_RESOURCE_GROUP
```

## Additional Resources

- [Azure Service Principals Documentation](https://docs.microsoft.com/azure/active-directory/develop/app-objects-and-service-principals)
- [GitHub Actions Azure Login Action](https://github.com/Azure/login)
- [Best Practices for Service Principals](https://docs.microsoft.com/azure/active-directory/develop/app-objects-and-service-principals)

