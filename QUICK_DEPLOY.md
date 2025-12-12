# Quick Deployment Guide

This is a condensed version of the full deployment guide. For detailed instructions, see [AZURE_DEPLOYMENT.md](./AZURE_DEPLOYMENT.md).

## Quick Start (5 Steps)

### 1. Create Azure Resources

```bash
# Using Azure CLI (optional)
az group create --name accounting-rg --location eastus
az cosmosdb create --name your-accounting-db --resource-group accounting-rg --kind GlobalDocumentDB
az webapp create --name your-accounting-api --resource-group accounting-rg --runtime "PYTHON:3.12" --plan your-plan
```

Or use Azure Portal to create:
- Azure Cosmos DB (SQL API)
- Azure App Service (Python 3.12, Linux)
- Azure Static Web App

### 2. Configure App Service Environment Variables

In Azure Portal → App Service → Configuration → Application settings:

```
USE_COSMOS_DB=1
COSMOS_ENDPOINT=https://your-account.documents.azure.com:443/
COSMOS_KEY=your-key
DATABASE_NAME=accounting-db
ENABLE_AUTH=1
AZURE_TENANT_ID=your-tenant-id
AZURE_CLIENT_ID=your-client-id
FLASK_ENV=production
BUILD_FRONTEND=1
PORT=8000
```

### 3. Configure Static Web App Environment Variables

In Azure Portal → Static Web App → Configuration → Application settings:

```
VITE_API_BASE_URL=https://your-accounting-api.azurewebsites.net/api
```

### 4. Add GitHub Secrets

Go to GitHub → Repository → Settings → Secrets and variables → Actions:

- `AZURE_STATIC_WEB_APPS_API_TOKEN`: From Static Web App → Manage deployment token
- `AZURE_WEBAPP_NAME`: Your App Service name
- `AZURE_CREDENTIALS`: Azure Service Principal credentials (JSON) - see below

**Create Azure Service Principal** (using Azure CLI):

```bash
az login
az ad sp create-for-rbac --name "github-actions-accounting" \
  --role contributor \
  --scopes /subscriptions/YOUR_SUBSCRIPTION_ID/resourceGroups/YOUR_RESOURCE_GROUP \
  --sdk-auth
```

Copy the JSON output and paste it as the `AZURE_CREDENTIALS` secret.

### 5. Push to Main Branch

```bash
git add .
git commit -m "Prepare for Azure deployment"
git push origin main
```

GitHub Actions will automatically deploy both frontend and backend!

## Verify Deployment

1. **Frontend**: `https://your-app.azurestaticapps.net`
2. **Backend**: `https://your-api.azurewebsites.net/api/businesses` (should return 401 if auth enabled)

## Troubleshooting

- **Frontend 404s**: Check `staticwebapp.config.json`
- **API errors**: Verify `VITE_API_BASE_URL` in Static Web App settings
- **CORS errors**: Check App Service CORS configuration
- **Auth failures**: Verify Azure AD redirect URIs include Static Web App URL

## Files Created

- `staticwebapp.config.json` - Static Web App routing configuration
- `.github/workflows/azure-static-web-apps.yml` - Frontend deployment workflow
- `.github/workflows/azure-app-service.yml` - Backend deployment workflow
- `azure-app-service-requirements.txt` - Production Python dependencies
- `azure-app-service-startup.sh` - App Service startup script
- `AZURE_DEPLOYMENT.md` - Full deployment guide
- `DEPLOYMENT_CHECKLIST.md` - Pre-deployment checklist

## Next Steps

1. Test the deployed application
2. Configure custom domains (optional)
3. Set up monitoring and alerts
4. Review [DEPLOYMENT_CHECKLIST.md](./DEPLOYMENT_CHECKLIST.md) for completeness

