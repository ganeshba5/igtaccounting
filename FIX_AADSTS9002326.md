# Fix: AADSTS9002326 - Cross-origin token redemption error

## Problem

You're seeing this error:
```
AADSTS9002326: Cross-origin token redemption is permitted only for the 'Single-Page Application' client-type.
```

## Root Cause

Your Azure AD app registration has the wrong platform type. It's configured as "Web" instead of "Single-page application" (SPA).

## Solution (Step-by-Step)

### 1. Go to Azure Portal

1. Navigate to https://portal.azure.com
2. Go to **Azure Active Directory** (or **Microsoft Entra ID**)
3. Click **App registrations**
4. Find and click on your app registration

### 2. Check Current Platform Configuration

1. Click **"Authentication"** in the left menu
2. Look at the **"Platform configurations"** section
3. Check if you see any entries with platform type **"Web"**

### 3. Remove "Web" Platform (if present)

1. If you see any **"Web"** platform entries, click the **trash icon** (🗑️) to delete them
2. Confirm deletion

### 4. Add "Single-page application" Platform

1. Click **"Add a platform"** button
2. Select **"Single-page application"** (NOT "Web")
3. Add your redirect URIs:
   - `http://localhost:3000` (for frontend dev server)
   - `http://localhost:5001` (for single-server mode)
   - `https://your-production-domain.com` (for production)
4. Click **"Configure"** after adding each URI
5. Click **"Save"** at the top

### 5. Verify Configuration

Your **"Platform configurations"** should show:
- ✅ **Single-page application** with your redirect URIs
- ❌ **NO "Web" platform entries**

### 6. Wait and Test

1. Wait 1-2 minutes for Azure AD changes to propagate
2. Clear your browser cache/cookies (optional but recommended)
3. Try logging in again

## Visual Guide

**Correct Configuration:**
```
Platform configurations:
┌─────────────────────────────────────┐
│ Single-page application             │
│ ✓ http://localhost:3000             │
│ ✓ http://localhost:5001             │
└─────────────────────────────────────┘
```

**Incorrect Configuration (causes error):**
```
Platform configurations:
┌─────────────────────────────────────┐
│ Web                                 │ ← DELETE THIS
│ ✓ http://localhost:3000             │
└─────────────────────────────────────┘
```

## Why This Happens

- MSAL.js (Microsoft Authentication Library for JavaScript) requires the app to be registered as a **Single-page application**
- "Web" platform is for server-side authentication flows (different from SPA)
- Azure AD enforces this to prevent security issues with cross-origin token redemption

## Still Having Issues?

1. **Double-check**: Make sure there are NO "Web" platform entries
2. **Wait longer**: Azure AD changes can take up to 5 minutes to propagate
3. **Clear browser data**: Clear cookies and cache for localhost
4. **Check redirect URI**: Ensure the redirect URI exactly matches your app URL (including port)
5. **Verify environment variables**: Make sure `VITE_AZURE_CLIENT_ID` and `VITE_AZURE_TENANT_ID` are set correctly

