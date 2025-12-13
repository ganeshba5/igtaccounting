# Quick Fix: Add Redirect URI to Azure AD App Registration

## Problem
Azure AD is rejecting the redirect URI: `https://thankful-rock-0bea0c80f.3.azurestaticapps.net`

## Solution: Add Redirect URI via Azure Portal

### Step 1: Navigate to App Registration
1. Go to: https://portal.azure.com
2. Search for **"App registrations"** in the top search bar
3. Click **"App registrations"** from the results

### Step 2: Find Your App
- Search for or find the app with Client ID: **96f3225d-1b81-426d-b11a-e1c1cb8f6571**
- Click on it to open

### Step 3: Add Redirect URI
1. In the left menu, click **"Authentication"**
2. Scroll down to **"Single-page application"** section
3. Click **"+ Add URI"**
4. Enter: `https://thankful-rock-0bea0c80f.3.azurestaticapps.net`
5. Click **"Save"** at the top

### Step 4: Verify
- The URI should now appear in the "Single-page application" redirect URIs list
- Make sure it's listed under **"Single-page application"** (not "Web")

### Step 5: Test
1. Wait 1-2 minutes for changes to propagate
2. Clear browser cache/cookies
3. Visit: https://thankful-rock-0bea0c80f.3.azurestaticapps.net
4. Try signing in again

## Important Notes

✅ **Platform Type**: Must be **"Single-page application"** (SPA)
- MSAL.js requires SPA redirect URIs
- Do NOT add it under "Web" platform

✅ **Local Development**: You should also have `http://localhost:3000` (if not already)

✅ **Exact Match Required**: 
- No trailing slash
- Must match exactly (including https://)
- Case sensitive

## Expected Redirect URIs

After adding, you should have:
- `http://localhost:3000` (development)
- `https://thankful-rock-0bea0c80f.3.azurestaticapps.net` (production)

## Visual Guide

```
Azure Portal → App registrations → [Your App] → Authentication
                                                     ↓
                                          Single-page application
                                                     ↓
                                           [Add URI] button
                                                     ↓
                                    Enter: https://thankful-rock-0bea0c80f.3.azurestaticapps.net
                                                     ↓
                                                [Save]
```

## Troubleshooting

### Still not working?
1. **Wait 2-5 minutes** - Azure AD changes need time to propagate
2. **Hard refresh** - Clear browser cache (Ctrl+Shift+R or Cmd+Shift+R)
3. **Check browser console** - Look for redirect URI errors
4. **Verify exact URL** - No trailing slash, exact casing

### Can't find the app?
- Use the search in App registrations
- Or go directly: https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps/ApplicationMenuBlade/~/Authentication/appId/96f3225d-1b81-426d-b11a-e1c1cb8f6571

