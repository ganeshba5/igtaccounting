# Quick Fix: "Basic Authentication is Disabled"

If you see **"Basic authentication is disabled"** when trying to download the publish profile from Azure App Service, **don't worry!** 

We use a more secure method that doesn't require publish profiles or enabling basic authentication.

## Solution: Use Azure Service Principal

Instead of publish profiles, we use Azure Service Principal authentication, which is:
- ✅ More secure (OAuth token-based)
- ✅ No need to enable basic authentication
- ✅ Recommended by Microsoft for CI/CD

## Quick Setup (2 minutes)

1. **Create Service Principal** (using Azure CLI):
   ```bash
   az login
   az ad sp create-for-rbac --name "github-actions-accounting" \
     --role contributor \
     --scopes /subscriptions/YOUR_SUBSCRIPTION_ID/resourceGroups/YOUR_RESOURCE_GROUP \
     --sdk-auth
   ```

2. **Copy the JSON output** and add it as a GitHub secret:
   - Go to: GitHub → Your Repo → Settings → Secrets and variables → Actions
   - Click "New repository secret"
   - Name: `AZURE_CREDENTIALS`
   - Value: Paste the entire JSON output

3. **That's it!** Your deployment will now work without publish profiles.

## Detailed Instructions

For complete step-by-step instructions, see:
- **[AZURE_SERVICE_PRINCIPAL_SETUP.md](./AZURE_SERVICE_PRINCIPAL_SETUP.md)** - Detailed setup guide
- **[AZURE_DEPLOYMENT.md](./AZURE_DEPLOYMENT.md)** - Full deployment guide

## Alternative: Enable Basic Auth (Not Recommended)

If you must use publish profiles, you can enable basic authentication:

1. Azure Portal → App Service → Configuration → General settings
2. Find "Basic Authentication" section
3. Enable "SCM Basic Auth Publishing Credentials" and "FTP Basic Auth Publishing Credentials"
4. Click "Save" and restart the app

**However, using Service Principal is more secure and recommended!**

