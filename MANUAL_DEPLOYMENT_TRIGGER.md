# Manual Deployment Trigger - Step by Step

## How to Manually Trigger App Service Deployment

### Step 1: Open GitHub Actions
Go to: **https://github.com/ganeshba5/igtaccounting/actions**

### Step 2: Select the Workflow
Click on **"Azure App Service Deployment"** in the workflow list

### Step 3: Run Workflow
1. Click the **"Run workflow"** dropdown button (top right, next to "Filter workflows")
2. Select branch: **`main`** (should be selected by default)
3. Click the green **"Run workflow"** button

### Step 4: Monitor Deployment
1. You'll see a new workflow run appear at the top of the list
2. Click on it to see the progress
3. Watch for the deployment to complete (should take 2-5 minutes)

### Step 5: Verify CORS is Fixed
After deployment completes, test:
```bash
curl -v -X OPTIONS -H "Origin: https://acc.infogloballink.com" -H "Access-Control-Request-Method: GET" https://igtacct-api-azaghzb4chhagvc3.eastus-01.azurewebsites.net/api/businesses
```

You should see:
- `Access-Control-Allow-Origin: https://acc.infogloballink.com`
- `HTTP/1.1 200 OK` (or appropriate status)

## What This Will Deploy

This will deploy the latest code including:
- ✅ Fixed CORS configuration that properly parses `CORS_ORIGINS` environment variable
- ✅ Fallback CORS origins including `https://acc.infogloballink.com`
- ✅ All previous backend fixes

## Troubleshooting

If you see another 409 Conflict:
- Wait 2-3 minutes and try again
- Or wait for any in-progress deployment to complete first

If deployment succeeds but CORS still fails:
- Wait 1-2 minutes for the app to fully restart
- Clear browser cache
- Check logs: `az webapp log tail --name igtacct-api --resource-group IgtAcct`

