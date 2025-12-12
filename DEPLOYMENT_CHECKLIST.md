# Azure Deployment Checklist

Use this checklist to ensure all steps are completed before deploying to Azure.

## Pre-Deployment

### Azure Resources
- [ ] Azure Cosmos DB account created
- [ ] Cosmos DB endpoint and key copied
- [ ] Azure App Service created (Python 3.12, Linux)
- [ ] Azure Static Web App created
- [ ] All resource names are globally unique

### Configuration
- [ ] Azure AD app registration created
- [ ] Redirect URIs configured in Azure AD:
  - [ ] Development: `http://localhost:3000`
  - [ ] Production: `https://your-app.azurestaticapps.net`
- [ ] Azure AD tenant ID and client ID copied

### Code Preparation
- [ ] All environment variables documented in `.env.example`
- [ ] Frontend API URL configured for production
- [ ] CORS configuration updated for production
- [ ] Build scripts tested locally
- [ ] All dependencies listed in `azure-app-service-requirements.txt`

## GitHub Configuration

### Secrets
- [ ] `AZURE_STATIC_WEB_APPS_API_TOKEN` added to GitHub Secrets
- [ ] `AZURE_WEBAPP_NAME` added to GitHub Secrets
- [ ] `AZURE_CREDENTIALS` added to GitHub Secrets (Service Principal JSON)
- [ ] Service Principal created with Contributor role on resource group

### Workflows
- [ ] `.github/workflows/azure-static-web-apps.yml` created
- [ ] `.github/workflows/azure-app-service.yml` created
- [ ] Workflows tested (push to main branch)

## App Service Configuration

### Application Settings
- [ ] `USE_COSMOS_DB=1`
- [ ] `COSMOS_ENDPOINT` set
- [ ] `COSMOS_KEY` set
- [ ] `DATABASE_NAME=accounting-db`
- [ ] `ENABLE_AUTH=1`
- [ ] `AZURE_TENANT_ID` set
- [ ] `AZURE_CLIENT_ID` set
- [ ] `FLASK_ENV=production`
- [ ] `BUILD_FRONTEND=1`
- [ ] `PORT=8000`
- [ ] `CORS_ORIGINS` set (if needed)

### Deployment
- [ ] Deployment Center configured
- [ ] GitHub repository connected
- [ ] Branch set to `main`
- [ ] Build provider: GitHub Actions

## Static Web App Configuration

### Application Settings
- [ ] `VITE_API_BASE_URL` set to App Service URL
- [ ] `VITE_AZURE_CLIENT_ID` set (if using environment variables)
- [ ] `VITE_AZURE_TENANT_ID` set (if using environment variables)

### Deployment
- [ ] Repository connected
- [ ] Branch set to `main`
- [ ] App location: `/frontend`
- [ ] Output location: `dist`
- [ ] API location: (empty)

## Post-Deployment Verification

### Frontend
- [ ] Static Web App URL accessible
- [ ] All routes work (no 404 errors)
- [ ] API calls succeed
- [ ] Authentication flow works
- [ ] Microsoft SSO login works

### Backend
- [ ] App Service URL accessible
- [ ] Health check endpoint responds
- [ ] API endpoints return expected responses
- [ ] Cosmos DB connection successful
- [ ] Authentication validation works

### Integration
- [ ] Frontend can call backend API
- [ ] CORS headers present in responses
- [ ] Authentication tokens passed correctly
- [ ] All features functional

## Monitoring

- [ ] Application Insights configured (optional)
- [ ] Log streaming enabled
- [ ] Error alerts configured (optional)
- [ ] Performance monitoring set up (optional)

## Security

- [ ] HTTPS enforced (automatic with Azure)
- [ ] Environment variables secured (not in code)
- [ ] CORS origins restricted
- [ ] Authentication required for API endpoints
- [ ] Cosmos DB keys secured

## Documentation

- [ ] Deployment guide reviewed
- [ ] Team members have access to Azure resources
- [ ] Environment variables documented
- [ ] Troubleshooting guide available

## Rollback Plan

- [ ] Previous deployment tagged in Git
- [ ] Rollback procedure documented
- [ ] Database backup strategy in place

## Next Steps After Deployment

- [ ] Custom domain configured (optional)
- [ ] SSL certificate verified (automatic)
- [ ] Performance testing completed
- [ ] User acceptance testing completed
- [ ] Production monitoring active

