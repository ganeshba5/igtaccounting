# API URL Fix Summary

## Problem
Frontend was calling `/api/businesses` which was being routed to Static Web Apps, resulting in 404 errors. The frontend needs to call the backend API at the App Service URL.

## Solution
Updated `frontend/src/api.js` to automatically detect the production environment (Static Web Apps) and use the correct backend API URL.

## What Changed

### Before
```javascript
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api'
```

### After
```javascript
const getApiBaseUrl = () => {
  // If environment variable is set (build time), use it
  if (import.meta.env.VITE_API_BASE_URL) {
    return import.meta.env.VITE_API_BASE_URL
  }
  
  // Detect production Static Web Apps environment
  const hostname = window.location.hostname
  if (hostname.includes('azurestaticapps.net')) {
    // Production: point to backend API
    return 'https://igtacct-api-azaghzb4chhagvc3.eastus-01.azurewebsites.net/api'
  }
  
  // Development: use relative path (proxied by Vite)
  return '/api'
}

const API_BASE_URL = getApiBaseUrl()
```

## How It Works

1. **Development** (`localhost:3000`):
   - Uses `/api` (relative path)
   - Vite proxy forwards to `http://localhost:5001`

2. **Production** (`*.azurestaticapps.net`):
   - Detects Static Web Apps hostname
   - Uses: `https://igtacct-api-azaghzb4chhagvc3.eastus-01.azurewebsites.net/api`

3. **Environment Variable Override**:
   - If `VITE_API_BASE_URL` is set at build time, it takes precedence

## Benefits

✅ **Automatic detection** - No manual configuration needed
✅ **Works in all environments** - Development and production
✅ **Runtime detection** - No need to rebuild for different environments
✅ **Fallback support** - Still respects environment variables if set

## Deployment

✅ Code updated and committed
✅ Build completed successfully
✅ Pushed to trigger deployment

After deployment completes (~5 minutes), the frontend should correctly call the backend API.

## Verification

After deployment, check:
1. Browser console should show API calls to:
   `https://igtacct-api-azaghzb4chhagvc3.eastus-01.azurewebsites.net/api/businesses`
2. Should NOT see 404 errors from Static Web Apps
3. Businesses should load successfully

