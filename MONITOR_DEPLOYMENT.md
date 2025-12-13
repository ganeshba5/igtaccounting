# Monitor Deployment

## Deployment Status

✅ **Committed and pushed** `requirements.txt` to trigger new deployment.

## Monitor Deployment Progress

### 1. Check GitHub Actions (Recommended)
Visit: https://github.com/ganeshba5/igtaccounting/actions

Look for workflow: **"Azure App Service Deployment"**
- Should show "In progress" or "Queued"
- Click on it to see detailed logs
- Look for "Install dependencies" step
- Look for "Deploy to Azure Web App" step

### 2. Monitor Azure Deployment Logs

```bash
# List recent deployments
az webapp deployment list --name igtacct-api --resource-group IgtAcct --query "[].{id:id, status:status, message:message, active:active, startTime:startTime}" -o table

# Stream live logs
az webapp log tail --name igtacct-api --resource-group IgtAcct
```

### 3. What to Look For

**During Deployment:**
- ✅ "Installing dependencies..." messages
- ✅ "Collecting gunicorn..." messages
- ✅ "Successfully installed..." messages
- ✅ Deployment status: "Success"

**During Startup (after deployment):**
- ✅ "Starting gunicorn..." or gunicorn startup messages
- ✅ "Listening at: http://0.0.0.0:8000"
- ✅ Flask app initialization messages
- ❌ **NO MORE** "Container has finished running with exit code: 1"

### 4. Test the API

After deployment completes and app starts:

```bash
# Should return 401 (Unauthorized) - means app is running!
# NOT 503 (Service Unavailable) or Application Error
curl -I https://igtacct-api-azaghzb4chhagvc3.eastus-01.azurewebsites.net/api/businesses
```

Expected: `HTTP/1.1 401 Unauthorized` ✅

### 5. If Deployment Succeeds But App Still Fails

Check application logs for specific Python errors:

```bash
az webapp log download --name igtacct-api --resource-group IgtAcct --log-file logs.zip
unzip logs.zip
grep -r "Error\|Exception\|Traceback\|ModuleNotFound\|ImportError" LogFiles/
```

### 6. Quick Status Check

```bash
# Check app state
az webapp show --name igtacct-api --resource-group IgtAcct --query "{state:state, defaultHostName:defaultHostName}" -o json

# Check if it's responding
curl -I https://igtacct-api-azaghzb4chhagvc3.eastus-01.azurewebsites.net/api/businesses 2>&1 | head -3
```

## Expected Timeline

- **0-2 minutes**: GitHub Actions workflow runs
- **2-5 minutes**: Deployment to Azure completes
- **5-10 minutes**: App starts (first startup may take longer)
- **Total**: ~10 minutes for complete deployment

## Troubleshooting

If deployment fails or app still doesn't start:

1. Check GitHub Actions logs for build errors
2. Check Azure deployment logs for deployment errors
3. Check application logs for runtime errors
4. Verify environment variables are set correctly
5. Check if `requirements.txt` was deployed correctly

See `STARTUP_ERROR_SUMMARY.md` for detailed troubleshooting steps.

