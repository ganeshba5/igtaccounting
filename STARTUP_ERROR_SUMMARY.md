# Startup Error Summary

## Problem
Container exits with **exit code 1** immediately after starting (~10-30 seconds), but **no Python error output** is visible in logs.

## Root Cause Analysis

### Likely Issue: **Dependencies Not Installed**

The container is trying to run:
```bash
gunicorn --bind 0.0.0.0:8000 --timeout 120 --workers 2 --chdir backend --access-logfile - --error-logfile - --log-level debug app:app
```

But `gunicorn` (and possibly other dependencies) are likely **not installed** because:
1. `SCM_DO_BUILD_DURING_DEPLOYMENT` was only just enabled
2. The current deployment was made **before** this setting was enabled
3. Azure App Service needs a **new deployment** to trigger Oryx build system

### Current Status

✅ **Environment Variables Set:**
- `SCM_DO_BUILD_DURING_DEPLOYMENT=true` (enabled)
- `ENABLE_ORYX_BUILD=true` (enabled)
- `USE_COSMOS_DB=1`
- All Azure AD and Cosmos DB credentials present

✅ **Files Ready:**
- `requirements.txt` exists at root with all dependencies
- Startup command configured correctly

❌ **Missing:**
- **New deployment needed** to trigger dependency installation

## Solution

### Option 1: Trigger New Deployment (Recommended)

1. **Commit the requirements.txt file** (if not already committed):
   ```bash
   git add requirements.txt
   git commit -m "Fix: Add root requirements.txt for Azure App Service"
   git push origin main
   ```

2. **Or manually redeploy** via Azure CLI:
   ```bash
   # Package and deploy
   zip -r deploy.zip . -x "*.git*" -x "*venv*" -x "*__pycache__*" -x "*.db"
   az webapp deployment source config-zip \
     --resource-group IgtAcct \
     --name igtacct-api \
     --src deploy.zip
   ```

3. **Monitor the deployment**:
   ```bash
   az webapp deployment list --name igtacct-api --resource-group IgtAcct
   az webapp log tail --name igtacct-api --resource-group IgtAcct
   ```

### Option 2: Use SSH to Install Dependencies Manually (Temporary Fix)

```bash
az webapp ssh --name igtacct-api --resource-group IgtAcct
cd /home/site/wwwroot
pip install -r requirements.txt
exit
az webapp restart --name igtacct-api --resource-group IgtAcct
```

### Option 3: Simplify Startup Command (For Testing)

Temporarily use a simpler command to see actual errors:
```bash
az webapp config set --name igtacct-api --resource-group IgtAcct \
  --startup-file "cd backend && python -c 'import app; print(\"App imported successfully\")' 2>&1 || python -c 'import sys; sys.path.insert(0, \"backend\"); import app' 2>&1"
```

## Expected Behavior After Fix

1. **During deployment**, Oryx should:
   - Detect `requirements.txt`
   - Install all dependencies
   - Show build logs with "Installing dependencies..."

2. **During startup**, gunicorn should:
   - Start successfully
   - Bind to port 8000
   - Load the Flask app
   - Accept HTTP requests

3. **Application logs** should show:
   - Gunicorn startup messages
   - Flask app initialization
   - Any import/configuration errors (if any)

## Next Steps

1. ✅ Fixed PORT setting (was "80-00", now "8000")
2. ✅ Enabled build during deployment
3. ✅ Created root requirements.txt
4. ⏳ **Need to trigger new deployment** to install dependencies
5. ⏳ Monitor logs after deployment
6. ⏳ Test API endpoint: `curl https://igtacct-api-azaghzb4chhagvc3.eastus-01.azurewebsites.net/api/businesses`

## Verification Commands

After deployment, verify:

```bash
# Check app is running
az webapp show --name igtacct-api --resource-group IgtAcct --query state

# Check logs for Python/gunicorn output
az webapp log tail --name igtacct-api --resource-group IgtAcct | grep -i "gunicorn\|python\|started"

# Test API (should get 401, not 503 or Application Error)
curl -I https://igtacct-api-azaghzb4chhagvc3.eastus-01.azurewebsites.net/api/businesses
```

