# Fix: QuotaExceeded Error on Free Tier App Service

## The Issue

Your App Service shows `"state": "QuotaExceeded"` which means you've hit limits on the Free tier (F1).

## Free Tier Limitations

The Free tier has these limits:
- **60 minutes CPU time per day** (shared across all apps in the plan)
- **1 GB storage**
- **1 app per plan**
- Apps can be stopped if quota is exceeded
- Apps can't always run (may be stopped after inactivity)

## Solutions

### Option 1: Upgrade to Basic Tier (Recommended)

The Basic tier (B1) is about $13/month and removes most limitations:

```bash
# Create a new Basic plan (or use existing)
az appservice plan create \
  --name igtacct-api-plan-basic \
  --resource-group IgtAcct \
  --sku B1 \
  --is-linux

# Move your app to the new plan
az webapp update \
  --name igtacct-api \
  --resource-group IgtAcct \
  --app-service-plan igtacct-api-plan-basic
```

### Option 2: Wait for Quota Reset

Free tier quotas reset daily. You can:
1. Wait until the quota resets (usually at midnight UTC)
2. Then restart the app

### Option 3: Check What's Using the Quota

```bash
# List all apps in the same plan
az webapp list --query "[?appServicePlanId=='YOUR_PLAN_ID'].{name:name, state:state}" -o table

# Stop other apps if not needed
az webapp stop --name OTHER_APP_NAME --resource-group IgtAcct
```

### Option 4: Scale Up the Free Plan (Limited)

Free tier can't be scaled, but you can:
- Delete unused apps from the plan
- Wait for quota reset

## Quick Fix: Upgrade to Basic Tier

1. Go to **Azure Portal** → **App Service Plan** (`ASP-IgtAcct-a862`)
2. Click **Scale up (App Service plan)**
3. Select **Basic B1** tier
4. Click **Apply**
5. Wait for scaling to complete (2-3 minutes)
6. Restart your App Service

Or use Azure CLI:

```bash
# Get the plan name
PLAN_NAME=$(az webapp show --name igtacct-api --resource-group IgtAcct --query appServicePlanId -o tsv | cut -d'/' -f9)

# Scale up to Basic
az appservice plan update \
  --name $PLAN_NAME \
  --resource-group IgtAcct \
  --sku B1
```

## After Upgrading

1. **Restart the App Service**:
   ```bash
   az webapp restart --name igtacct-api --resource-group IgtAcct
   ```

2. **Check status**:
   ```bash
   az webapp show --name igtacct-api --resource-group IgtAcct --query state -o tsv
   ```
   Should show: `Running` (not `QuotaExceeded`)

3. **Test API**:
   ```bash
   curl -I https://igtacct-api-azaghzb4chhagvc3.eastus-01.azurewebsites.net/api/businesses
   ```
   Should return: `401 Unauthorized` (API is running!)

## Cost Comparison

- **Free (F1)**: $0/month - Limited, quota restrictions
- **Basic (B1)**: ~$13/month - Always on, no quota limits
- **Standard (S1)**: ~$73/month - More features, staging slots

For production, **Basic B1 is recommended** to avoid quota issues.



