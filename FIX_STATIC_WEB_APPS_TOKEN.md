# Fix: Static Web Apps "Invalid API key" Error

## Problem
The Static Web Apps deployment is failing with:
```
Deployment Failure Reason: Invalid API key.
```

## Root Cause
The GitHub secret `AZURE_STATIC_WEB_APPS_API_TOKEN` is either:
- Not set in GitHub repository secrets
- Set with an incorrect/invalid value
- Expired or revoked

## Solution

### Step 1: Get the Deployment Token

Run this command to get the deployment token:

```bash
az staticwebapp secrets list \
  --name igtacc \
  --resource-group IgtAcct \
  --query "properties.apiKey" \
  -o tsv
```

### Step 2: Update GitHub Secret

1. Go to your GitHub repository: https://github.com/ganeshba5/igtaccounting
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Find `AZURE_STATIC_WEB_APPS_API_TOKEN`
4. Click **Update** and paste the token from Step 1
5. Click **Update secret**

### Step 3: Retry Deployment

After updating the secret:
1. Go to **Actions** tab in GitHub
2. Find the failed workflow run
3. Click **Re-run all jobs**

Or simply push a new commit:
```bash
git commit --allow-empty -m "Retry Static Web Apps deployment"
git push origin main
```

## Alternative: Use the Auto-Generated Workflow

I notice there's also an auto-generated workflow file:
- `.github/workflows/azure-static-web-apps-thankful-rock-0bea0c80f.yml`

This one uses a different secret name: `AZURE_STATIC_WEB_APPS_API_TOKEN_THANKFUL_ROCK_0BEA0C80F`

You might want to:
1. **Delete** `.github/workflows/azure-static-web-apps.yml` (manual one)
2. **Use** the auto-generated one instead (it should have the correct token)

Or update the manual workflow to use the correct secret name.

## Verify Deployment Token

To verify the token is correct:

```bash
# Get the token
TOKEN=$(az staticwebapp secrets list \
  --name igtacc \
  --resource-group IgtAcct \
  --query "properties.apiKey" \
  -o tsv)

echo "Deployment token: $TOKEN"
```

Then use this token in the GitHub secret.

