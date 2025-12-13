# Fix: App Service URL and Site Disabled

## The Problem

1. `igtacct-api.azurewebsites.net` - DNS not found
2. `igtacct-api-azaghzb4chhagvc3.eastus-01.azurewebsites.net` - 403 Site Disabled

## Solution

### Step 1: Start Your App Service

The "Site Disabled" error means your App Service is **stopped**. You need to start it:

1. Go to **Azure Portal** → Your App Service (`igtacct-api`)
2. Click **Start** button in the top toolbar
3. Wait for it to start (usually 30-60 seconds)

### Step 2: Verify the Correct URL

After starting, verify which URL works:

```bash
# Test the regional URL (this one exists)
curl -I https://igtacct-api-azaghzb4chhagvc3.eastus-01.azurewebsites.net/api/businesses

# After starting, it should return 401 (Unauthorized) instead of 403
```

### Step 3: Use the Regional URL Format

Since the standard format doesn't resolve, you need to use the regional URL format:

**Update Static Web App Configuration**:
```
VITE_API_BASE_URL=https://igtacct-api-azaghzb4chhagvc3.eastus-01.azurewebsites.net/api
```

### Step 4: Update CORS Configuration

In your App Service → Configuration → Application settings, update:

```
CORS_ORIGINS=https://your-static-web-app.azurestaticapps.net
```

Replace `your-static-web-app` with your actual Static Web App name.

## Alternative: Fix DNS/Standard URL

If you want to use the standard URL format, you might need to:

1. **Check the actual App Service name**:
   - Go to Azure Portal → App Services
   - Find your app and check the exact name
   - It might be `igtacct-api` but the DNS hasn't propagated

2. **Wait for DNS propagation** (can take a few minutes to hours)

3. **Or use a custom domain** if needed

## Testing After Starting the App Service

Once the App Service is started, test:

```bash
curl -I https://igtacct-api-azaghzb4chhagvc3.eastus-01.azurewebsites.net/api/businesses
```

Expected results:
- ✅ **401 Unauthorized** = API is running, auth is working
- ❌ **403 Site Disabled** = App Service is stopped
- ❌ **404 Not Found** = Route doesn't exist
- ❌ **500 Internal Server Error** = App is running but has errors

## Why Regional URL Format?

Azure App Services sometimes use regional URL formats like:
- `{app-name}-{random-id}.{region}.azurewebsites.net`

This is normal and happens when:
- The app was created in a specific region
- Using certain Azure configurations
- DNS hasn't fully propagated for the standard format

## Permanent Solution

If you want to use the standard format, you can:

1. **Wait for DNS** (can take time)
2. **Check App Service name** in Portal → Overview → Name
3. **Use Custom Domain** (optional, requires domain configuration)

For now, **use the regional URL format** - it works just as well!

