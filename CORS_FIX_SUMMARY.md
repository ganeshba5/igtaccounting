# CORS Fix Summary

## Problem
CORS (Cross-Origin Resource Sharing) error when accessing the API from the custom domain `acc.infogloballink.com`:

```
Access to XMLHttpRequest at 'https://igtacct-api-azaghzb4chhagvc3.eastus-01.azurewebsites.net/api/businesses' 
from origin 'https://acc.infogloballink.com' has been blocked by CORS policy: 
No 'Access-Control-Allow-Origin' header is present on the requested resource.
```

## Root Cause
The backend CORS configuration:
1. Used wildcard pattern `https://*.azurestaticapps.net` which Flask-CORS doesn't support
2. Didn't include the custom domain `acc.infogloballink.com`

## Solution

### 1. Updated Backend Code
Modified `backend/app.py` to explicitly allow both domains:
- `https://thankful-rock-0bea0c80f.3.azurestaticapps.net`
- `https://acc.infogloballink.com`
- Plus localhost for testing

### 2. Set Environment Variable
Set `CORS_ORIGINS` environment variable in Azure App Service:
```
https://thankful-rock-0bea0c80f.3.azurestaticapps.net,https://acc.infogloballink.com,http://localhost:3000,http://localhost:5001
```

### 3. Restarted App Service
Restarted the backend to apply changes.

## What Changed

**Before:**
```python
CORS(app, origins=[
    'https://*.azurestaticapps.net',  # Wildcard doesn't work!
    'http://localhost:3000',
    'http://localhost:5001'
])
```

**After:**
```python
CORS(app, origins=[
    'https://thankful-rock-0bea0c80f.3.azurestaticapps.net',
    'https://acc.infogloballink.com',  # Added custom domain
    'http://localhost:3000',
    'http://localhost:5001'
])
```

## Verification

After the app restarts (~30 seconds), test:
1. Visit: `https://acc.infogloballink.com`
2. Sign in
3. Try to load businesses
4. Should work without CORS errors

## Notes

- Flask-CORS doesn't support wildcard patterns in origins
- Must explicitly list each allowed origin
- Environment variable `CORS_ORIGINS` can override the code fallback
- App Service restart is required for environment variable changes to take effect

