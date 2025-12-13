# Fix: API Base URL Configuration

## Problem
The frontend is trying to call `/api/businesses` which is being routed to Static Web Apps, resulting in a 404 error. The frontend needs to call the backend API at the App Service URL.

## Solution
Set the `VITE_API_BASE_URL` environment variable in Azure Static Web Apps to point to the backend API.

## Configuration

### Backend API URL
```
https://igtacct-api-azaghzb4chhagvc3.eastus-01.azurewebsites.net/api
```

### How It Works

1. **Development**: Vite proxy handles `/api` → `http://localhost:5001`
2. **Production**: `VITE_API_BASE_URL` environment variable points to the backend
3. **Fallback**: If not set, defaults to `/api` (which fails in Static Web Apps)

## Set Environment Variable

### Option 1: Azure CLI (Done)

```bash
az staticwebapp appsettings set \
  --name igtacc \
  --resource-group IgtAcct \
  --setting-names "VITE_API_BASE_URL=https://igtacct-api-azaghzb4chhagvc3.eastus-01.azurewebsites.net/api"
```

### Option 2: Azure Portal

1. Go to: https://portal.azure.com
2. Navigate to: **Static Web Apps** → **igtacc**
3. Click **"Configuration"** in the left menu
4. Under **"Application settings"**, click **"+ Add"**
5. Add:
   - **Name**: `VITE_API_BASE_URL`
   - **Value**: `https://igtacct-api-azaghzb4chhagvc3.eastus-01.azurewebsites.net/api`
6. Click **"Save"**

### Option 3: Update Workflow (For Future Deployments)

You can also set it in the GitHub Actions workflow, but note that Vite environment variables need to be available at **build time**, not runtime. So this won't work for Static Web Apps unless you rebuild.

## Important Notes

⚠️ **Vite Environment Variables**: 
- `VITE_*` variables are embedded at **build time**
- Setting them in Azure Portal **won't work** for already-built apps
- You need to **rebuild the frontend** after setting the variable

⚠️ **Current Issue**:
- The frontend is already built and deployed
- Setting the environment variable now won't affect the current deployment
- You have two options:
  1. **Redeploy** (will rebuild with the variable)
  2. **Use a different approach** (see below)

## Alternative Solution: Update Frontend Code

If environment variables don't work well with Static Web Apps, we can update the code to detect the environment:

```javascript
// In frontend/src/api.js
const API_BASE_URL = 
  window.location.hostname === 'thankful-rock-0bea0c80f.3.azurestaticapps.net'
    ? 'https://igtacct-api-azaghzb4chhagvc3.eastus-01.azurewebsites.net/api'
    : (import.meta.env.VITE_API_BASE_URL || '/api')
```

But this is less flexible. The environment variable approach is better if we can get it to work.

## Next Steps

1. ✅ Set the environment variable (done above)
2. **Trigger a new deployment** to rebuild with the variable:
   ```bash
   git commit --allow-empty -m "Rebuild frontend with API base URL"
   git push origin main
   ```
3. **Or** update the frontend code to use environment detection (see alternative solution)

## Verification

After redeploying, check browser console:
- Should see API calls going to: `https://igtacct-api-azaghzb4chhagvc3.eastus-01.azurewebsites.net/api/businesses`
- Should NOT see 404 errors from Static Web Apps

