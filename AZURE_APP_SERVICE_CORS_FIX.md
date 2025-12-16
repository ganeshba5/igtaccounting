# Azure App Service CORS Configuration

## Critical Discovery

**Azure App Service has its own CORS settings that OVERRIDE application-level CORS configurations!**

This means even if you configure CORS correctly in Flask/flask-cors, Azure App Service's CORS middleware intercepts the request first and can block it.

## Solution: Configure CORS in Azure Portal/CLI

### Option 1: Azure CLI (Done)

```bash
az webapp cors update \
  --name igtacct-api \
  --resource-group IgtAcct \
  --allowed-origins \
    "https://thankful-rock-0bea0c80f.3.azurestaticapps.net" \
    "https://acc.infogloballink.com" \
    "http://localhost:3000" \
    "http://localhost:5001" \
  --support-credentials true
```

### Option 2: Azure Portal

1. Go to: https://portal.azure.com
2. Navigate to: **App Services** → **igtacct-api**
3. In the left menu: **API** → **CORS**
4. Add allowed origins:
   - `https://thankful-rock-0bea0c80f.3.azurestaticapps.net`
   - `https://acc.infogloballink.com`
   - `http://localhost:3000` (for local testing)
   - `http://localhost:5001` (for local testing)
5. **Enable** "Allow Access-Control-Allow-Credentials"
6. Click **Save**

## Current Configuration

✅ Allowed Origins:
- `https://thankful-rock-0bea0c80f.3.azurestaticapps.net`
- `https://acc.infogloballink.com`
- `http://localhost:3000`
- `http://localhost:5001`

✅ Support Credentials: `true` (needed for Authorization headers)

## Important Notes

1. **Azure CORS Overrides Flask CORS**: If Azure App Service CORS is configured, it takes precedence
2. **Credentials Required**: Since we use Authorization headers, `support-credentials` must be `true`
3. **Exact Match**: Origins must match exactly (including protocol, domain, and port)
4. **No Wildcards in Production**: Don't use `*` for production security

## Verification

After configuring, test:
```bash
curl -v -X OPTIONS \
  -H "Origin: https://acc.infogloballink.com" \
  -H "Access-Control-Request-Method: GET" \
  -H "Access-Control-Request-Headers: authorization" \
  https://igtacct-api-azaghzb4chhagvc3.eastus-01.azurewebsites.net/api/businesses
```

Should return:
- `Access-Control-Allow-Origin: https://acc.infogloballink.com`
- `Access-Control-Allow-Credentials: true`
- `Access-Control-Allow-Methods: GET,POST,PUT,DELETE,OPTIONS`
- `Access-Control-Allow-Headers: Content-Type,Authorization`

## References

- [Azure App Service CORS Documentation](https://learn.microsoft.com/en-us/azure/app-service/app-service-web-tutorial-rest-api)
- [Flask-CORS vs Azure CORS](https://medium.com/@agbajeafolabimuhammed/cors-hell-when-azure-app-service-settings-override-your-code-e48ab9e997a3)

