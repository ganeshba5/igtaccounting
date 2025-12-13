# Understanding Free Tier Quota Consumption

## Why Was Quota Exceeded Without Deployment?

The Free tier (F1) has a **daily CPU time limit of 60 minutes** that is shared across **ALL apps** in the same App Service Plan. Here's how quota can be consumed even without a successful deployment:

### 1. **App Service Creation and Idle Time**

When you create an App Service, Azure:
- **Starts the container/process immediately** (even if no code is deployed)
- The app runs a default "Hello World" or error page
- **Idle apps still consume CPU time** (though minimal)
- The app stays running until explicitly stopped

### 2. **Failed Deployment Attempts**

If GitHub Actions tried to deploy:
- The deployment process itself consumes CPU time
- Failed deployments may leave the app in a running state
- Each deployment attempt uses resources

### 3. **Auto-Start Behavior**

Azure App Service on Free tier:
- **Auto-starts apps** when they're created
- Apps may restart automatically after being stopped
- Health checks and monitoring consume minimal CPU

### 4. **Shared Quota Across Apps**

If you have **multiple apps** in the same App Service Plan:
- All apps share the same 60-minute daily quota
- One app consuming quota affects all apps
- You can check with: `az webapp list --query "[?appServicePlanId=='YOUR_PLAN_ID']"`

### 5. **Previous Day's Activity**

The quota resets daily (usually at midnight UTC):
- If the app was running yesterday, it consumed quota
- The quota might have been exhausted before today's deployment attempt

## How to Check What Happened

### Check App Service Plan Usage

```bash
# List all apps in the plan
az webapp list --query "[?appServicePlanId=='YOUR_PLAN_ID'].{name:name, state:state}" -o table

# Check app state history (if available)
az webapp show --name igtacct-api --resource-group IgtAcct --query usageState
```

### Check GitHub Actions Deployment History

1. Go to your GitHub repository
2. Click **Actions** tab
3. Look for **Azure App Service Deployment** workflow runs
4. Check if any deployments were attempted (even if they failed)

### Check Azure Portal Metrics

1. Go to **Azure Portal** → **App Service Plan** (`ASP-IgtAcct-a862`)
2. Click **Metrics**
3. Select **CPU Time** metric
4. Check the last 7 days to see when quota was consumed

## Why This Happens

**Free tier is designed for development/testing**, not production:
- Quota limits prevent abuse
- Apps can be stopped if quota is exceeded
- No SLA guarantees
- Shared resources mean unpredictable performance

## Solutions

### ✅ **Upgrade to Basic Tier (B1)** - Recommended

- **$13/month** (or less with reserved instances)
- **No quota limits**
- Always-on capability
- Predictable performance
- Suitable for production

### ⚠️ **Stay on Free Tier** - Not Recommended for Production

If you must stay on Free tier:
1. **Stop the app when not in use**:
   ```bash
   az webapp stop --name igtacct-api --resource-group IgtAcct
   ```

2. **Monitor quota usage**:
   - Check Azure Portal metrics daily
   - Stop apps before quota is exhausted

3. **Use only one app per plan**:
   - Each additional app shares the same quota
   - Reduces available time for your main app

4. **Wait for quota reset**:
   - Quota resets at midnight UTC
   - Plan deployments around quota availability

## Current Status

✅ **You've already upgraded to Basic B1 tier**, so:
- No more quota limits
- App can run 24/7
- No need to worry about quota consumption
- Ready for production use

## Prevention for Future

If you create new apps:
1. **Use Basic tier or higher** for production
2. **Stop Free tier apps** when not actively developing
3. **Monitor quota** if you must use Free tier
4. **Use separate App Service Plans** for different environments

