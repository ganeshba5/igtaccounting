# Quick Fix: 403 Site Disabled After Starting

## Most Likely Cause: No Code Deployed Yet

The App Service is running, but there's no code deployed to it yet. This happens when:
- You just created the App Service
- GitHub Actions workflow hasn't run yet
- No deployment has been triggered

## Solution: Deploy Your Code

### Option 1: Trigger GitHub Actions Deployment (Recommended)

1. **Push code to GitHub** (if you haven't already):
   ```bash
   git add .
   git commit -m "Initial deployment"
   git push origin main
   ```

2. **Check GitHub Actions**:
   - Go to: GitHub → Your Repo → Actions
   - Look for "Azure App Service Deployment" workflow
   - Wait for it to complete (usually 2-5 minutes)

3. **After deployment completes**, test again:
   ```bash
   curl -I https://igtacct-api-azaghzb4chhagvc3.eastus-01.azurewebsites.net/api/businesses
   ```

### Option 2: Manual Deployment via Azure CLI

If you want to deploy manually:

```bash
# Install Azure CLI extension for web apps (if not already installed)
az extension add --name webapp

# Deploy from current directory
az webapp up --name igtacct-api --resource-group YOUR_RESOURCE_GROUP --runtime "PYTHON:3.12"
```

### Option 3: Check if Deployment Already Exists

Check if code has been deployed:

```bash
az webapp deployment list --name igtacct-api --resource-group YOUR_RESOURCE_GROUP --query '[0]' -o json
```

If this returns `null` or empty, no code has been deployed.

## Verify Deployment

After deployment, you should see:

1. **In Azure Portal** → **Deployment Center**:
   - Recent deployments listed
   - Status: Active

2. **In App Service** → **Log stream**:
   - Messages like "Starting Gunicorn"
   - Flask app loading messages
   - No Python errors

3. **Test API**:
   ```bash
   curl -I https://igtacct-api-azaghzb4chhagvc3.eastus-01.azurewebsites.net/api/businesses
   ```
   
   Should return: **401 Unauthorized** (means API is running!)

## If Still Getting 403 After Deployment

### Check Startup Command

In Azure Portal → **Configuration** → **General settings**:

**Startup Command** should be:
```
gunicorn --bind 0.0.0.0:8000 --timeout 120 --workers 4 --chdir backend app:app
```

Click **Save** and **Restart** the app.

### Check Logs

1. Go to **Log stream** in Azure Portal
2. Look for errors
3. Common issues:
   - Module not found → Check requirements.txt
   - Wrong path → Check startup command
   - Port conflicts → Check PORT environment variable

## Quick Checklist

- [ ] Code pushed to GitHub main branch
- [ ] GitHub Actions workflow ran successfully
- [ ] Deployment shows as "Active" in Deployment Center
- [ ] Startup command is configured correctly
- [ ] Environment variables are set
- [ ] App Service is in "Running" state
- [ ] Tested API endpoint after deployment

## Expected Timeline

- **App Service creation**: Instant
- **Starting App Service**: 30-60 seconds
- **GitHub Actions deployment**: 2-5 minutes
- **App startup after deployment**: 30-60 seconds

**Total**: Usually 3-7 minutes from push to working API

