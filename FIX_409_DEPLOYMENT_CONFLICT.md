# Fix: 409 Deployment Conflict Error

## Problem
Getting `409 Conflict` error when deploying to App Service:
```
Error: Deployment Failed, Error: Failed to deploy web package to App Service.
Conflict (CODE: 409)
```

## Root Cause
This error occurs when:
1. **Another deployment is already in progress**
2. The App Service is in a transitional state (starting/stopping)
3. Multiple deployments were triggered simultaneously

## Solutions

### Option 1: Wait and Retry (Recommended)
1. Wait 2-5 minutes for the current deployment to complete
2. Check GitHub Actions to see if deployment is still running
3. The workflow will automatically retry on the next push

### Option 2: Check Active Deployments
```bash
az webapp deployment list \
  --name igtacct-api \
  --resource-group IgtAcct \
  --query "[0].{status:status, active:active}"
```

### Option 3: Restart App Service
```bash
az webapp restart \
  --name igtacct-api \
  --resource-group IgtAcct
```

Then wait 1 minute and trigger deployment again.

### Option 4: Manual Deploy via Azure CLI
If GitHub Actions keeps failing, you can deploy manually:

```bash
# Package the code
zip -r deploy.zip . -x "*.git*" -x "*venv*" -x "*__pycache__*" -x "*.db" -x "*node_modules*" -x "LogFiles/*" -x "deployments/*" -x "*.zip"

# Deploy
az webapp deployment source config-zip \
  --resource-group IgtAcct \
  --name igtacct-api \
  --src deploy.zip
```

## Prevention

- **Avoid multiple simultaneous deployments** - Wait for one to complete
- **Check deployment status** before triggering a new one
- **Use workflow_dispatch** for manual triggers instead of rapid pushes

## Current Status

The deployment might still be processing from a previous push. Wait a few minutes and check:
- GitHub Actions: https://github.com/ganeshba5/igtaccounting/actions
- Azure Portal: App Service → Deployment Center

