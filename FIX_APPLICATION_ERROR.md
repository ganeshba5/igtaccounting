# Fix: Application Error on App Service

## The Issue

When accessing `https://igtacct-api-azaghzb4chhagvc3.eastus-01.azurewebsites.net/api/businesses`, you get an Application Error page.

This means the Flask app is crashing during startup.

## Step 1: Check Application Logs

### Option A: Via Azure Portal

1. Go to **Azure Portal** → **App Service** (`igtacct-api`)
2. Go to **Monitoring** → **Log stream**
3. Look for Python errors, import errors, or startup failures

### Option B: Via Azure CLI

```bash
az webapp log tail --name igtacct-api --resource-group YOUR_RESOURCE_GROUP
```

### Option C: Download Recent Logs

```bash
az webapp log download --name igtacct-api --resource-group YOUR_RESOURCE_GROUP --log-file app-logs.zip
```

## Step 2: Common Issues and Fixes

### Issue 1: Missing Dependencies

**Symptoms**: Import errors in logs (e.g., "No module named 'flask'")

**Fix**: Ensure `azure-app-service-requirements.txt` includes all dependencies:
- Flask
- flask-cors
- azure-cosmos
- PyJWT
- gunicorn
- All other required packages

### Issue 2: Startup Command Incorrect

**Symptoms**: "Command not found" or "Module not found" for app

**Fix**: Check startup command in **Configuration** → **General settings**:

```
gunicorn --bind 0.0.0.0:8000 --timeout 120 --workers 4 --chdir backend app:app
```

Make sure:
- ✅ `--chdir backend` is included (changes to backend directory)
- ✅ `app:app` points to the Flask app instance
- ✅ Port is 8000 (or matches PORT env var)

### Issue 3: Environment Variables Missing

**Symptoms**: KeyError or None values for environment variables

**Fix**: Verify all required environment variables are set in **Configuration** → **Application settings**:

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

### Issue 4: Python Path Issues

**Symptoms**: "No module named 'backend'" or import errors

**Fix**: Ensure the startup command uses `--chdir backend` or adjust PYTHONPATH

### Issue 5: Gunicorn Not Installed

**Symptoms**: "gunicorn: command not found"

**Fix**: Ensure `gunicorn` is in `azure-app-service-requirements.txt`:
```
gunicorn==21.2.0
```

## Step 3: Quick Diagnostic

Run these commands to check:

```bash
# Check if app is running
az webapp show --name igtacct-api --query state -o tsv

# Check startup command
az webapp config show --name igtacct-api --query linuxFxVersion

# Check environment variables (redacted)
az webapp config appsettings list --name igtacct-api --query '[].{Name:name}' -o table
```

## Step 4: Test Locally First

Before deploying, test that the app runs locally with production settings:

```bash
# Set environment variables
export USE_COSMOS_DB=1
export COSMOS_ENDPOINT=your-endpoint
export COSMOS_KEY=your-key
# ... etc

# Install dependencies
pip install -r azure-app-service-requirements.txt

# Test startup command
cd backend
gunicorn --bind 0.0.0.0:8000 --timeout 120 --workers 4 app:app
```

If it fails locally, fix the issue before deploying.

## Step 5: Enable Detailed Error Pages

For debugging, temporarily enable detailed error pages:

1. Go to **Configuration** → **General settings**
2. Set **Stack trace**: On (for debugging only!)
3. Click **Save** and **Restart**

**Note**: Disable this in production after fixing the issue.

## Step 6: Check Deployment Status

Verify the code was actually deployed:

1. Go to **Deployment Center**
2. Check if deployment shows as "Active"
3. Check deployment logs for errors

## Most Common Fixes

1. **Missing dependencies**: Add to `azure-app-service-requirements.txt`
2. **Wrong startup command**: Use `--chdir backend app:app`
3. **Missing environment variables**: Set all required vars
4. **Port mismatch**: Use port 8000 or match PORT env var
5. **Python version**: Ensure App Service uses Python 3.12

## Next Steps

1. Check the logs (most important!)
2. Share the error messages from logs
3. Fix the specific issue
4. Restart the App Service
5. Test again

The logs will tell you exactly what's wrong!

