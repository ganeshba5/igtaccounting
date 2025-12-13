# Startup Error Diagnosis

## Problem
Container exits with exit code 1, but no Python error messages visible in logs.

## Likely Causes

1. **Dependencies not installed**: Azure App Service may not be automatically installing from `requirements.txt`
2. **Missing environment variables**: The app might be failing due to missing Azure AD or Cosmos DB config
3. **Import errors**: Python modules not found
4. **Path issues**: `--chdir backend` might not be working as expected

## Fixes Applied

1. ✅ Enabled `SCM_DO_BUILD_DURING_DEPLOYMENT=true` - Forces Azure to install dependencies during deployment
2. ✅ Enabled `ENABLE_ORYX_BUILD=true` - Enables Oryx build system to detect and build Python app
3. ✅ Updated startup command to include `--error-logfile -` to see errors in stdout
4. ✅ Copied `azure-app-service-requirements.txt` to root `requirements.txt` (Azure looks for this at root)

## Next Steps

1. **Commit and push** these changes to trigger a new deployment:
   ```bash
   git add requirements.txt
   git commit -m "Fix: Add root requirements.txt for Azure App Service dependency installation"
   git push origin main
   ```

2. **Or manually redeploy** using Azure CLI:
   ```bash
   az webapp restart --name igtacct-api --resource-group IgtAcct
   ```

3. **Monitor logs** after deployment:
   ```bash
   az webapp log tail --name igtacct-api --resource-group IgtAcct
   ```

4. **Check for specific errors**:
   - Import errors (ModuleNotFoundError)
   - Missing environment variables
   - Database connection failures
   - Path/working directory issues

## Expected Behavior After Fix

- Azure should automatically detect `requirements.txt` at root
- Oryx build system should install all dependencies
- Gunicorn should start successfully
- Errors (if any) should appear in logs with `--error-logfile -`

## If Still Failing

Check application logs for specific Python errors:
```bash
az webapp log download --name igtacct-api --resource-group IgtAcct --log-file logs.zip
unzip logs.zip
grep -r "Error\|Exception\|Traceback" LogFiles/
```

