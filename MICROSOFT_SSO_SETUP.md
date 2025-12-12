# Microsoft SSO (Single Sign-On) Setup Guide

This guide will help you set up Microsoft Authentication (Azure AD) for the Accounting System.

## Prerequisites

- An Azure account with an active subscription
- Access to Azure Portal
- Admin rights to register applications in Azure AD

## Step 1: Register Application in Azure AD

1. **Go to Azure Portal**: https://portal.azure.com
2. **Navigate to Azure Active Directory** (or **Microsoft Entra ID**)
3. **Go to "App registrations"** in the left menu
4. **Click "New registration"**

### Application Registration Details

- **Name**: `Accounting System` (or your preferred name)
- **Supported account types**: 
  - Choose based on your needs:
    - **Accounts in this organizational directory only** (Single tenant)
    - **Accounts in any organizational directory** (Multi-tenant)
    - **Accounts in any organizational directory and personal Microsoft accounts** (Multi-tenant + personal)
- **Redirect URI**: 
  - **CRITICAL**: You MUST select **"Single-page application"** as the platform type
  - **DO NOT** select "Web" - this will cause authentication errors
  - **URIs to add** (add ALL that apply):
    - `http://localhost:3000` (for frontend dev server)
    - `http://localhost:5001` (for single-server mode)
    - `https://your-production-domain.com` (for production)
  - Click **Add** after each URI
  - **Important**: The redirect URI must exactly match where your app is running

5. **Click "Register"**

### ⚠️ IMPORTANT: Platform Type Must Be "Single-page application"

**If you see the error "AADSTS9002326: Cross-origin token redemption is permitted only for the 'Single-Page Application' client-type":**

1. Go to your app registration in Azure Portal
2. Click **"Authentication"** in the left menu
3. Under **"Platform configurations"**, check if you have any entries with platform type **"Web"**
4. **Delete any "Web" platform entries** (they conflict with SPA)
5. Make sure you only have **"Single-page application"** platform entries
6. If you don't have any SPA entries, click **"Add a platform"** → Select **"Single-page application"**
7. Add your redirect URIs under the SPA platform
8. **Save** your changes

## Step 2: Configure API Permissions

1. In your app registration, go to **"API permissions"**
2. **Click "Add a permission"**
3. Select **"Microsoft Graph"**
4. Select **"Delegated permissions"**
5. Add the following permissions:
   - `User.Read` (to read user profile)
6. **Click "Add permissions"**
7. **Click "Grant admin consent"** (if you're an admin) to consent for all users

## Step 3: Get Application Details

1. In your app registration, go to **"Overview"**
2. Copy the following values:
   - **Application (client) ID** → This is your `AZURE_CLIENT_ID`
   - **Directory (tenant) ID** → This is your `AZURE_TENANT_ID`

## Step 4: Configure Frontend Environment Variables

Create or update `.env` file in the `frontend` directory:

```bash
cd frontend
```

Create `.env` file:

```env
VITE_AZURE_CLIENT_ID=your-client-id-here
VITE_AZURE_TENANT_ID=your-tenant-id-here
VITE_AZURE_AUTHORITY=https://login.microsoftonline.com/your-tenant-id-here

# Optional: Override redirect URI if needed
# For single-server mode (Flask serves frontend on port 5001):
# VITE_AZURE_REDIRECT_URI=http://localhost:5001
# For frontend dev server (port 3000):
# VITE_AZURE_REDIRECT_URI=http://localhost:3000
# For production:
# VITE_AZURE_REDIRECT_URI=https://your-production-domain.com
```

**Note**: 
- Replace `your-client-id-here` and `your-tenant-id-here` with the values from Step 3.
- The redirect URI is automatically set to `window.location.origin` (current URL), but you can override it with `VITE_AZURE_REDIRECT_URI` if needed.
- **Make sure the redirect URI matches one of the URIs you added in Azure Portal (Step 1)**

## Step 5: Configure Backend Environment Variables

Set the following environment variables before starting the backend:

```bash
export AZURE_TENANT_ID=your-tenant-id-here
export AZURE_CLIENT_ID=your-client-id-here
export ENABLE_AUTH=1
```

Or add them to your startup script:

```bash
# In start_backend.sh or start_single_server.sh
export AZURE_TENANT_ID=your-tenant-id-here
export AZURE_CLIENT_ID=your-client-id-here
export ENABLE_AUTH=1
```

## Step 6: Install Dependencies

### Frontend

```bash
cd frontend
npm install @azure/msal-browser
```

### Backend

```bash
pip install -r requirements.txt
```

This will install:
- `PyJWT` - For token validation
- `cryptography` - For RSA key handling
- `requests` - For fetching Azure AD keys

## Step 7: Update Redirect URIs for Production

When deploying to production:

1. Go to your app registration in Azure Portal
2. Go to **"Authentication"**
3. Add your production redirect URI:
   - **Platform**: Single-page application (SPA)
   - **URI**: `https://your-production-domain.com`
4. **Save**

## Step 8: Test Authentication

1. **Start the backend**:
   ```bash
   ./start_backend.sh
   ```

2. **Start the frontend**:
   ```bash
   cd frontend
   npm run dev
   ```

3. **Open the application** in your browser
4. You should see a **"Sign in with Microsoft"** button
5. Click it and complete the Microsoft login
6. After successful login, you should be redirected back to the application

## Troubleshooting

### "Authentication not configured" Error

- Make sure `ENABLE_AUTH=1` is set in your environment
- Verify `AZURE_TENANT_ID` and `AZURE_CLIENT_ID` are set correctly

### "Invalid or expired token" Error

- Check that the redirect URI in Azure Portal matches your application URL
- Verify the client ID matches in both frontend and backend
- Ensure the token hasn't expired (tokens typically expire after 1 hour)

### "CORS Error" or "Redirect URI Mismatch" (AADSTS50011)

- **Most common issue**: The redirect URI in your request doesn't match what's configured in Azure Portal
- **Solution**: 
  1. Check what URL your app is actually running on (look at the browser address bar)
  2. Go to Azure Portal → Your App Registration → Authentication
  3. Make sure you've added the exact redirect URI (including port number):
     - `http://localhost:3000` (frontend dev server)
     - `http://localhost:5001` (single-server mode)
     - `https://your-domain.com` (production)
  4. The redirect URI must match **exactly** - no trailing slashes, correct protocol (http vs https), correct port
  5. If using single-server mode, you may need to set `VITE_AZURE_REDIRECT_URI=http://localhost:5001` in your `.env` file
- **Quick fix**: Add both `http://localhost:3000` and `http://localhost:5001` to Azure Portal redirect URIs

### "Cross-origin token redemption" Error (AADSTS9002326)

- **Error**: "Cross-origin token redemption is permitted only for the 'Single-Page Application' client-type"
- **Cause**: Your app registration has the wrong platform type (likely "Web" instead of "Single-page application")
- **Solution**:
  1. Go to Azure Portal → Your App Registration → **Authentication**
  2. Under **"Platform configurations"**, look for any entries with platform type **"Web"**
  3. **Delete all "Web" platform entries** (click the trash icon)
  4. Click **"Add a platform"** → Select **"Single-page application"**
  5. Add your redirect URIs:
     - `http://localhost:3000`
     - `http://localhost:5001`
     - `https://your-production-domain.com` (if applicable)
  6. Click **"Configure"** and **"Save"**
  7. **Important**: You should ONLY have "Single-page application" platform entries, no "Web" entries
  8. Wait a few minutes for changes to propagate, then try logging in again

### Development Mode (No Auth)

If you want to disable authentication for development:

1. **Backend**: Don't set `ENABLE_AUTH=1` (or set it to `0`)
2. **Frontend**: The app will still show login, but backend won't require it

## Security Notes

- **Never commit** `.env` files or environment variables to version control
- Use **environment variables** or **Azure Key Vault** for production secrets
- Regularly **rotate** application secrets if compromised
- Use **HTTPS** in production (required for Microsoft authentication)
- Consider implementing **token refresh** for long-running sessions

## Additional Resources

- [Microsoft Identity Platform Documentation](https://docs.microsoft.com/en-us/azure/active-directory/develop/)
- [MSAL.js Documentation](https://github.com/AzureAD/microsoft-authentication-library-for-js)
- [Azure AD App Registration Guide](https://docs.microsoft.com/en-us/azure/active-directory/develop/quickstart-register-app)

