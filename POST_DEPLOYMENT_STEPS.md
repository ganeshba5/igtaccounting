# Post-Deployment Steps

Your Azure Static Web App is being created! While you wait (usually 2-5 minutes), follow these steps:

## Step 1: Complete App Service Configuration

While the Static Web App is deploying, configure your Azure App Service (backend):

### 1.1 Set Environment Variables

Go to Azure Portal → Your App Service → Configuration → Application settings

Add these settings:

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
CORS_ORIGINS=https://your-app-name.azurestaticapps.net
```

**Important**: Replace `your-app-name` with your actual Static Web App name in the CORS_ORIGINS setting.

### 1.2 Configure Startup Command

Go to Configuration → General settings:

**Startup Command**:
```
gunicorn --bind 0.0.0.0:8000 --timeout 120 --workers 4 --chdir backend app:app
```

Click **Save** and restart the app.

## Step 2: Configure Static Web App Environment Variables

Once your Static Web App is ready:

1. Go to Azure Portal → Your Static Web App → Configuration → Application settings
2. Add:

```
VITE_API_BASE_URL=https://your-api-name.azurewebsites.net/api
```

Replace `your-api-name` with your actual App Service name.

## Step 3: Set Up GitHub Secrets

Go to GitHub → Your Repository → Settings → Secrets and variables → Actions

Add these secrets:

1. **AZURE_STATIC_WEB_APPS_API_TOKEN**
   - Get it from: Azure Portal → Static Web App → Manage deployment token
   - Copy the token value

2. **AZURE_WEBAPP_NAME**
   - Your App Service name (e.g., `your-accounting-api`)

3. **AZURE_CREDENTIALS**
   - Service Principal JSON (see below)

### Create Service Principal

Run this command (replace placeholders):

```bash
az login
az ad sp create-for-rbac --name "github-actions-accounting" \
  --role contributor \
  --scopes /subscriptions/YOUR_SUBSCRIPTION_ID/resourceGroups/YOUR_RESOURCE_GROUP \
  --sdk-auth
```

Copy the entire JSON output and paste it as the `AZURE_CREDENTIALS` secret value.

## Step 4: Verify Deployment URLs

Once your Static Web App is ready, you'll get URLs like:

- **Frontend**: `https://your-app-name.azurestaticapps.net`
- **Backend**: `https://your-api-name.azurewebsites.net`

### Update Azure AD Redirect URIs

1. Go to Azure Portal → Azure Active Directory → App registrations → Your app
2. Go to Authentication
3. Add these Redirect URIs:
   - `https://your-app-name.azurestaticapps.net`
   - `https://your-app-name.azurestaticapps.net/`

4. Update Front-channel logout URL:
   - `https://your-app-name.azurestaticapps.net`

5. Click **Save**

## Step 5: Test Deployment

Once both are deployed:

1. **Test Frontend**: Visit `https://your-app-name.azurestaticapps.net`
   - Should load the React app
   - May show authentication errors (expected if backend not ready)

2. **Test Backend API**: Visit `https://your-api-name.azurewebsites.net/api/businesses`
   - Should return 401 Unauthorized (expected - means API is running)
   - Should NOT return 404 or connection errors

3. **Test Full Flow**:
   - Sign in with Microsoft
   - Should redirect to your app
   - Should be able to access businesses

## Step 6: Check GitHub Actions

1. Go to GitHub → Your Repository → Actions
2. You should see workflows running:
   - `Azure Static Web Apps CI/CD` (for frontend)
   - `Azure App Service Deployment` (for backend)
3. Check for any errors or warnings

## Troubleshooting

### Frontend shows 404
- Check `staticwebapp.config.json` is in root directory
- Verify GitHub Actions workflow completed successfully
- Check Static Web App logs: Monitoring → Log stream

### API calls fail
- Verify `VITE_API_BASE_URL` is set correctly in Static Web App settings
- Check CORS_ORIGINS includes your Static Web App URL
- Verify App Service is running: Check App Service logs

### Authentication fails
- Verify Azure AD redirect URIs include your Static Web App URL
- Check `AZURE_TENANT_ID` and `AZURE_CLIENT_ID` in App Service settings
- Verify frontend has correct `VITE_AZURE_CLIENT_ID` if using env vars

### Backend deployment fails
- Check GitHub Actions logs
- Verify `AZURE_CREDENTIALS` secret is valid JSON
- Verify Service Principal has Contributor role on resource group
- Check App Service logs: Monitoring → Log stream

## Next Steps

Once everything is working:

1. ✅ Test all features (businesses, transactions, reports)
2. ✅ Set up custom domain (optional)
3. ✅ Configure monitoring and alerts
4. ✅ Set up staging environment (optional)
5. ✅ Review security settings
6. ✅ Document your deployment process

## Useful Links

- **Azure Portal**: https://portal.azure.com
- **GitHub Actions**: https://github.com/YOUR_USERNAME/YOUR_REPO/actions
- **Static Web App**: https://your-app-name.azurestaticapps.net
- **App Service**: https://your-api-name.azurewebsites.net

## Need Help?

- Check the full deployment guide: [AZURE_DEPLOYMENT.md](./AZURE_DEPLOYMENT.md)
- Service Principal setup: [AZURE_SERVICE_PRINCIPAL_SETUP.md](./AZURE_SERVICE_PRINCIPAL_SETUP.md)
- Deployment checklist: [DEPLOYMENT_CHECKLIST.md](./DEPLOYMENT_CHECKLIST.md)

