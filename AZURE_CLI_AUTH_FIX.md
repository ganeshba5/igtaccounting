# Fix: Azure CLI Authentication Error

## The Issue

```
Audience https://appservice.azure.com is not a supported MSI token audience.
```

This happens when Azure CLI (especially in Cloud Shell) doesn't have the right permissions/scope.

## Solution

### Step 1: Logout

```bash
az logout
```

### Step 2: Login with Required Scope

```bash
az login --scope "https://appservice.azure.com/.default"
```

This will open a browser window for authentication.

### Alternative: Login Interactively

If the scope login doesn't work, try:

```bash
az login
```

Then select your account and subscription.

### Step 3: Set Your Subscription (if needed)

```bash
# List subscriptions
az account list --output table

# Set the active subscription
az account set --subscription "YOUR_SUBSCRIPTION_ID_OR_NAME"
```

### Step 4: Verify You're Logged In

```bash
az account show
```

Should show your current subscription details.

## Now You Can Run Commands

After authenticating, you can set the startup command:

```bash
az webapp config set \
  --name igtacct-api \
  --resource-group YOUR_RESOURCE_GROUP \
  --startup-file "gunicorn --bind 0.0.0.0:8000 --timeout 120 --workers 4 --chdir backend app:app"
```

## If Using Cloud Shell

If you're in Azure Cloud Shell and still having issues:

1. Try opening a new Cloud Shell session
2. Or use Azure Portal → Cloud Shell → PowerShell (instead of Bash)
3. Or authenticate from your local machine

## Alternative: Use Azure Portal Directly

If Azure CLI continues to have issues, you can also:
1. Use Azure Portal → App Service → Configuration → General settings
2. Or use Azure Portal → App Service → SSH to access the container directly

