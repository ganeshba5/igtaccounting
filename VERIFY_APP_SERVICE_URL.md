# Verifying Your App Service URL

## The Issue

You configured:
```
VITE_API_BASE_URL=https://igtacct-api.azurewebsites.net/api
```

But Azure Portal shows:
```
igtacct-api-azaghzb4chhagvc3.eastus-01.azurewebsites.net
```

## Solution

The URL format you're seeing might be a regional endpoint or a different view. Let's verify the correct URL:

### Method 1: Check App Service Overview

1. Go to Azure Portal → Your App Service (`igtacct-api`)
2. Go to **Overview** section
3. Look for **URL** or **Default domain** field
4. It should show: `https://igtacct-api.azurewebsites.net`

### Method 2: Use Azure CLI

```bash
az webapp show --name igtacct-api --resource-group YOUR_RESOURCE_GROUP --query defaultHostName -o tsv
```

This will output the correct default hostname.

### Method 3: Test the URL

Try accessing these URLs directly in your browser:

1. **Standard format**: `https://igtacct-api.azurewebsites.net`
2. **Regional format** (if shown): `https://igtacct-api-azaghzb4chhagvc3.eastus-01.azurewebsites.net`

Both should work, but you should use the **standard format** (`igtacct-api.azurewebsites.net`) for your configuration.

## Update Configuration

### Static Web App Environment Variable

Update your Static Web App → Configuration → Application settings:

```
VITE_API_BASE_URL=https://igtacct-api.azurewebsites.net/api
```

**Important**: Make sure to include:
- `https://` protocol
- `/api` at the end (if your API routes are under `/api`)

### CORS Configuration in App Service

Also update your App Service → Configuration → Application settings:

```
CORS_ORIGINS=https://your-static-web-app.azurestaticapps.net
```

Replace `your-static-web-app` with your actual Static Web App name.

## Testing

After updating, test if the API is accessible:

1. **Test API directly**:
   ```
   https://igtacct-api.azurewebsites.net/api/businesses
   ```
   - Should return 401 (Unauthorized) if auth is enabled ✓
   - Should NOT return 404 or connection errors

2. **Test from browser console** (on your Static Web App):
   ```javascript
   fetch('https://igtacct-api.azurewebsites.net/api/businesses')
     .then(r => console.log('Status:', r.status))
     .catch(e => console.error('Error:', e))
   ```

## If the Regional URL is the Correct One

If `igtacct-api-azaghzb4chhagvc3.eastus-01.azurewebsites.net` is actually the correct URL (unusual but possible), then use:

```
VITE_API_BASE_URL=https://igtacct-api-azaghzb4chhagvc3.eastus-01.azurewebsites.net/api
```

However, this is very unusual. The standard format should be `{app-name}.azurewebsites.net`.

## Common Issues

### 404 Errors
- Check if the `/api` path is correct
- Verify App Service is running (check logs)
- Verify startup command is configured correctly

### CORS Errors
- Make sure `CORS_ORIGINS` includes your Static Web App URL
- Check browser console for specific CORS error messages
- Verify backend CORS configuration allows your frontend domain

### Connection Errors
- Verify App Service is running and not stopped
- Check if there are any firewall rules blocking access
- Verify the URL format matches exactly (including `https://`)

