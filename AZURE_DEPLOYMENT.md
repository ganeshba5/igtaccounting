# Azure Deployment Guide

This guide walks you through deploying the Accounting Application to Azure using:
- **Azure Static Web Apps** for the frontend (React)
- **Azure App Service** for the backend (Flask)

## Architecture Overview

```
┌─────────────────────────────────┐
│   Azure Static Web Apps         │
│   (Frontend - React)            │
│   https://your-app.azurestaticapps.net │
└──────────────┬──────────────────┘
               │ API Calls
               │ (CORS enabled)
               ▼
┌─────────────────────────────────┐
│   Azure App Service             │
│   (Backend - Flask)             │
│   https://your-api.azurewebsites.net │
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│   Azure Cosmos DB               │
│   (Database)                    │
└─────────────────────────────────┘
```

## Prerequisites

1. **Azure Account** with active subscription
2. **GitHub Account** (for CI/CD)
3. **Azure CLI** installed locally (optional, for manual deployment)
4. **Node.js 18+** and **Python 3.12+** installed locally

## Step 1: Prepare Azure Resources

### 1.1 Create Azure Cosmos DB Account

1. Go to [Azure Portal](https://portal.azure.com)
2. Create a new **Azure Cosmos DB** account:
   - **API**: Core (SQL)
   - **Subscription**: Your subscription
   - **Resource Group**: Create new or use existing
   - **Account Name**: `your-accounting-db` (must be globally unique)
   - **Location**: Choose closest to your users
   - **Capacity mode**: Serverless (for free tier) or Provisioned

3. After creation, go to **Keys** and copy:
   - **URI** (Endpoint)
   - **Primary Key**

### 1.2 Create Azure App Service (Backend)

1. In Azure Portal, create a new **Web App**:
   - **Name**: `your-accounting-api` (must be globally unique)
   - **Runtime stack**: Python 3.12
   - **Operating System**: Linux
   - **Region**: Same as Cosmos DB
   - **App Service Plan**: Create new (Free tier for testing, or Basic/Standard for production)

2. After creation, go to **Configuration** → **Application settings** and add:

   ```
   USE_COSMOS_DB=1
   COSMOS_ENDPOINT=https://your-account.documents.azure.com:443/
   COSMOS_KEY=your-primary-key-here
   DATABASE_NAME=accounting-db
   ENABLE_AUTH=1
   AZURE_TENANT_ID=your-tenant-id
   AZURE_CLIENT_ID=your-client-id
   FLASK_ENV=production
   BUILD_FRONTEND=1
   PORT=8000
   ```

3. Configure the startup command:
   - Go to **Configuration** → **General settings**
   - **Startup Command**: `gunicorn --bind 0.0.0.0:8000 --timeout 120 --workers 4 --chdir backend app:app`
   - Click **Save**

4. Go to **Deployment Center** and set up:
   - **Source**: GitHub (or Local Git, Azure DevOps, etc.)
   - Connect your repository
   - **Branch**: `main`
   - **Build provider**: GitHub Actions (recommended)

### 1.3 Create Azure Static Web App (Frontend)

1. In Azure Portal, create a new **Static Web App**:
   - **Name**: `your-accounting-app`
   - **Resource Group**: Same as other resources
   - **Region**: Same as other resources
   - **Source**: GitHub
   - **GitHub Account**: Connect your account
   - **Organization**: Your GitHub org/username
   - **Repository**: Your repository name
   - **Branch**: `main`
   - **Build Presets**: Custom
   - **App location**: `/frontend`
   - **Output location**: `dist`
   - **API location**: (leave empty - backend is separate)

2. After creation, go to **Configuration** → **Application settings** and add:

   ```
   VITE_API_BASE_URL=https://your-accounting-api.azurewebsites.net/api
   ```

3. Copy the **Deployment token** from the **Manage deployment token** section (you'll need this for GitHub Actions)

## Step 2: Configure GitHub Secrets

1. Go to your GitHub repository → **Settings** → **Secrets and variables** → **Actions**

2. Add the following secrets:

   - `AZURE_STATIC_WEB_APPS_API_TOKEN`: Deployment token from Static Web App
   - `AZURE_WEBAPP_NAME`: Your App Service name (e.g., `your-accounting-api`)
   - `AZURE_CREDENTIALS`: Azure Service Principal credentials (JSON format) - see below

### Creating Azure Service Principal for GitHub Actions

Instead of using publish profiles (which require basic authentication), we'll use a Service Principal for more secure authentication:

#### Option A: Using Azure CLI (Recommended)

```bash
# Login to Azure
az login

# Get your subscription ID
az account show --query id -o tsv

# Create a service principal with contributor role
az ad sp create-for-rbac --name "github-actions-accounting" \
  --role contributor \
  --scopes /subscriptions/YOUR_SUBSCRIPTION_ID/resourceGroups/YOUR_RESOURCE_GROUP \
  --sdk-auth

# This will output JSON like:
# {
#   "clientId": "...",
#   "clientSecret": "...",
#   "subscriptionId": "...",
#   "tenantId": "...",
#   ...
# }
```

Copy the entire JSON output and add it as the `AZURE_CREDENTIALS` secret in GitHub.

#### Option B: Using Azure Portal

1. Go to **Azure Active Directory** → **App registrations** → **New registration**
2. Name: `github-actions-accounting`
3. Click **Register**
4. Go to **Certificates & secrets** → **New client secret**
5. Copy the secret value (you'll only see it once)
6. Go to your **Resource Group** → **Access control (IAM)** → **Add role assignment**
7. Role: **Contributor**
8. Assign access to: **User, group, or service principal**
9. Select your newly created app registration
10. Create a JSON with the following format and add as `AZURE_CREDENTIALS`:

```json
{
  "clientId": "your-client-id-from-app-registration",
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

## Step 3: Update Frontend Configuration

The frontend is already configured to use environment variables. Make sure your `staticwebapp.config.json` is in the root directory.

## Step 4: GitHub Actions Workflow

The workflow file `.github/workflows/azure-app-service.yml` is already created in the repository. It uses Azure Service Principal authentication instead of publish profiles for better security.

## Step 5: Configure CORS

The Flask app already has CORS enabled. However, you may need to update it for production:

In `backend/app.py`, ensure CORS is configured to allow your Static Web App domain:

```python
from flask_cors import CORS

# Allow specific origins in production
if os.environ.get('FLASK_ENV') == 'production':
    CORS(app, origins=[
        'https://your-app.azurestaticapps.net',
        'https://*.azurestaticapps.net'  # Allow all Static Web Apps
    ])
else:
    CORS(app)  # Allow all in development
```

## Step 6: Configure Azure AD (Microsoft SSO)

1. Go to [Azure Portal](https://portal.azure.com) → **Azure Active Directory** → **App registrations**

2. Find your app registration (or create a new one)

3. Go to **Authentication** and add:
   - **Platform**: Single-page application
   - **Redirect URIs**: 
     - `https://your-app.azurestaticapps.net`
     - `https://your-app.azurestaticapps.net/`
   - **Front-channel logout URL**: `https://your-app.azurestaticapps.net`

4. Update the App Service environment variables with:
   - `AZURE_TENANT_ID`: Your tenant ID
   - `AZURE_CLIENT_ID`: Your application (client) ID

5. Update the frontend `AuthContext.jsx` to use the correct client ID and authority.

## Step 7: Deploy

### Option A: Automatic Deployment (Recommended)

1. Push your code to the `main` branch
2. GitHub Actions will automatically:
   - Build and deploy the frontend to Static Web Apps
   - Deploy the backend to App Service

### Option B: Manual Deployment

#### Frontend (Static Web Apps)
```bash
# Build the frontend
cd frontend
npm install
npm run build

# Deploy using Azure Static Web Apps CLI
npm install -g @azure/static-web-apps-cli
swa deploy ./dist --deployment-token YOUR_DEPLOYMENT_TOKEN
```

#### Backend (App Service)
```bash
# Install Azure CLI
az login
az webapp up --name your-accounting-api --runtime "PYTHON:3.12" --sku F1
```

## Step 8: Verify Deployment

1. **Frontend**: Visit `https://your-app.azurestaticapps.net`
2. **Backend API**: Visit `https://your-api.azurewebsites.net/api/businesses` (should return 401 if auth is enabled)
3. **Check Logs**:
   - Static Web Apps: Go to **Monitoring** → **Log stream**
   - App Service: Go to **Monitoring** → **Log stream** or **Logs**

## Troubleshooting

### Frontend Issues

1. **404 errors on routes**: Check `staticwebapp.config.json` navigation fallback
2. **API calls failing**: Verify `VITE_API_BASE_URL` is set correctly
3. **CORS errors**: Check App Service CORS configuration

### Backend Issues

1. **Module not found**: Ensure `azure-app-service-requirements.txt` includes all dependencies
2. **Cosmos DB connection errors**: Verify environment variables in App Service Configuration
3. **Authentication errors**: Check Azure AD configuration and environment variables

### Common Issues

1. **Build failures**: Check GitHub Actions logs
2. **Environment variables not loading**: Restart App Service after adding variables
3. **Static files not serving**: Ensure `BUILD_FRONTEND=1` and `FLASK_ENV=production` are set

## Cost Estimation

- **Azure Static Web Apps**: Free tier available (100 GB bandwidth/month)
- **Azure App Service**: Free tier available (F1 - 1 GB storage, limited CPU)
- **Azure Cosmos DB**: Serverless tier available (first 1000 RU/s free)

For production workloads, consider:
- **App Service**: Basic tier ($13/month) or Standard tier ($73/month)
- **Cosmos DB**: Provisioned throughput (400 RU/s minimum = ~$24/month)

## Next Steps

1. Set up custom domains for both frontend and backend
2. Configure SSL certificates (automatic with Azure)
3. Set up monitoring and alerts
4. Configure backup strategies for Cosmos DB
5. Set up staging environments

## Additional Resources

- [Azure Static Web Apps Documentation](https://docs.microsoft.com/azure/static-web-apps/)
- [Azure App Service Documentation](https://docs.microsoft.com/azure/app-service/)
- [Azure Cosmos DB Documentation](https://docs.microsoft.com/azure/cosmos-db/)
- [Flask on Azure App Service](https://docs.microsoft.com/azure/app-service/quickstart-python)

