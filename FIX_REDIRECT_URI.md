# Fix: Azure AD Redirect URI Mismatch

## Problem
```
AADSTS50011: The redirect URI 'https://thankful-rock-0bea0c80f.3.azurestaticapps.net' 
specified in the request does not match the redirect URIs configured for the application 
'96f3225d-1b81-426d-b11a-e1c1cb8f6571'.
```

## Solution
Add the Static Web Apps URL as a redirect URI in Azure AD App Registration.

## Step-by-Step Fix

### Option 1: Azure Portal (Recommended)

1. **Go to Azure Portal**: https://portal.azure.com

2. **Navigate to App Registrations**:
   - Search for "App registrations" in the top search bar
   - Click on your app: **96f3225d-1b81-426d-b11a-e1c1cb8f6571**

3. **Add Redirect URI**:
   - Click on **"Authentication"** in the left menu
   - Under **"Single-page application"** section, click **"Add URI"**
   - Enter: `https://thankful-rock-0bea0c80f.3.azurestaticapps.net`
   - Click **"Save"**

4. **Verify**:
   - The redirect URI should now appear in the list
   - Make sure it's under the **"Single-page application"** platform type

### Option 2: Azure CLI

```bash
# Get current redirect URIs
az ad app show --id 96f3225d-1b81-426d-b11a-e1c1cb8f6571 --query "spa.redirectUris" -o json

# Add the new redirect URI
az ad app update --id 96f3225d-1b81-426d-b11a-e1c1cb8f6571 \
  --set spa.redirectUris="[\"http://localhost:3000\",\"https://thankful-rock-0bea0c80f.3.azurestaticapps.net\"]"
```

**Note**: Replace the array with all redirect URIs you want to keep (don't remove existing ones like `http://localhost:3000`).

### Option 3: Using Microsoft Graph API

If you have the necessary permissions:

```bash
# Requires Microsoft Graph CLI or REST API
# This is more complex, so use Portal or Azure CLI instead
```

## Verify the Fix

1. **Wait 1-2 minutes** for changes to propagate
2. **Clear browser cache/cookies** for the Static Web Apps domain
3. **Try signing in again** at: https://thankful-rock-0bea0c80f.3.azurestaticapps.net

## Common Redirect URIs to Include

For a complete setup, you might want these redirect URIs:

- ✅ `http://localhost:3000` (local development)
- ✅ `https://thankful-rock-0bea0c80f.3.azurestaticapps.net` (production)
- (Optional) Custom domain if you set one up later

## Troubleshooting

### Still Getting the Error?

1. **Wait 2-5 minutes** - Azure AD changes can take time to propagate
2. **Clear browser cache** - Old redirect URI might be cached
3. **Check the exact URL** - Make sure there's no trailing slash or path
4. **Verify platform type** - Should be "Single-page application" (SPA), not "Web"

### Check Current Configuration

```bash
az ad app show --id 96f3225d-1b81-426d-b11a-e1c1cb8f6571 \
  --query "{spa:spa.redirectUris, web:web.redirectUris}" -o json
```

## Notes

- **SPA vs Web**: MSAL.js (used in React) requires "Single-page application" redirect URIs
- **HTTPS Required**: Production URIs must use HTTPS
- **No Wildcards**: You cannot use wildcards in redirect URIs
- **Case Sensitive**: URIs are case-sensitive

