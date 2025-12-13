# Fix: Deployment 403 Error

## The Issue

GitHub Actions deployment is failing with:
```
Error: Failed to deploy web package to App Service.
Error: The deployment to your web app failed with HTTP status code 403.
```

## Possible Causes

1. **Service Principal doesn't have correct permissions**
2. **Network restrictions** (Private Endpoints, IP restrictions)
3. **SCM site access blocked**
4. **Deployment credentials issue**

## Solutions

### Solution 1: Check Service Principal Permissions

The Service Principal needs **Contributor** or **Website Contributor** role:

1. **Check current role assignment**:
   ```bash
   az role assignment list --assignee <service-principal-client-id> \
     --scope /subscriptions/<subscription-id>/resourceGroups/<resource-group> \
     --query '[].{Role:roleDefinitionName}' -o table
   ```

2. **If no Contributor role, add it**:
   ```bash
   az role assignment create \
     --assignee <service-principal-client-id> \
     --role "Contributor" \
     --scope /subscriptions/<subscription-id>/resourceGroups/<resource-group>
   ```

### Solution 2: Check Network Restrictions

1. Go to **Azure Portal** → **App Service** → **Networking**
2. Check:
   - **Access restrictions**: Make sure not blocking all access
   - **Private endpoints**: If enabled, might block deployment
   - **VNet integration**: If enabled, might need configuration

3. **Temporarily disable restrictions for testing**:
   - Go to **Networking** → **Access restrictions**
   - Ensure there's an "Allow" rule or temporarily disable restrictions
   - **Note**: Re-enable after testing for security

### Solution 3: Enable SCM Site Access

The deployment uses the SCM (Kudu) site. Check if it's accessible:

1. Go to **Azure Portal** → **App Service** → **Configuration** → **General settings**
2. Make sure:
   - **SCM site always on**: Enabled
   - **HTTP Version**: 2.0 (or leave default)

3. **Test SCM site access**:
   ```bash
   curl -I https://igtacct-api-azaghzb4chhagvc3.eastus-01.azurewebsites.net/.scm/health
   ```
   
   Should return 200 OK. If 403, there's a network restriction.

### Solution 4: Use Deployment Credentials Instead

If Service Principal isn't working, try using deployment credentials:

1. **Generate deployment credentials**:
   ```bash
   az webapp deployment user set --user-name <username> --password <password>
   ```

2. **Update GitHub workflow** to use deployment credentials (not recommended for production, but works for testing)

### Solution 5: Check App Service Configuration

1. Go to **Azure Portal** → **App Service** → **Configuration** → **General settings**
2. Verify:
   - **Always On**: Enabled (recommended)
   - **Managed pipeline mode**: Integrated (or Classic)
   - **Platform**: 64 Bit (if needed)

### Solution 6: Use Zip Deploy with Different Method

The workflow uses `azure/webapps-deploy@v2`. Try updating to use different deployment method:

Update `.github/workflows/azure-app-service.yml` to use `zipDeploy` with specific options.

## Quick Fix: Verify Service Principal Permissions

Most common issue is incorrect Service Principal permissions.

1. **Get your Service Principal Client ID**:
   - From GitHub Secrets → `AZURE_CREDENTIALS` → `clientId` value
   - Or from Azure Portal → Azure AD → App registrations

2. **Check role**:
   ```bash
   # Get resource group ID
   RESOURCE_GROUP="your-resource-group"
   SUBSCRIPTION_ID=$(az account show --query id -o tsv)
   
   # Check assignments
   az role assignment list \
     --scope /subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP \
     --query "[?principalName=='<service-principal-name>'].{Role:roleDefinitionName, Principal:principalName}" \
     -o table
   ```

3. **Add Contributor role if missing**:
   ```bash
   az role assignment create \
     --assignee <service-principal-client-id> \
     --role "Contributor" \
     --scope /subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP
   ```

## Alternative: Deploy Manually First

To test if it's a permissions issue, try manual deployment:

```bash
# Create a zip of your code
cd /path/to/your/repo
zip -r deploy.zip . -x "*.git*" "node_modules/*" "venv/*" "*.db"

# Deploy using Azure CLI
az webapp deployment source config-zip \
  --resource-group YOUR_RESOURCE_GROUP \
  --name igtacct-api \
  --src deploy.zip
```

If this works, the issue is with the Service Principal permissions in GitHub Actions.

## Most Likely Fix

**Service Principal needs Contributor role on the resource group or subscription.**

Run this (replace placeholders):

```bash
# Get Service Principal Client ID from GitHub Secrets
CLIENT_ID="your-service-principal-client-id"

# Get resource group name
RESOURCE_GROUP="your-resource-group"

# Add Contributor role
az role assignment create \
  --assignee $CLIENT_ID \
  --role "Contributor" \
  --scope /subscriptions/$(az account show --query id -o tsv)/resourceGroups/$RESOURCE_GROUP
```

Then re-run the GitHub Actions workflow.

## Verify Fix

After applying fixes:

1. Re-run the GitHub Actions workflow
2. Check if deployment succeeds
3. Test API endpoint:
   ```bash
   curl -I https://igtacct-api-azaghzb4chhagvc3.eastus-01.azurewebsites.net/api/businesses
   ```

