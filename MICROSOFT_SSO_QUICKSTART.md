# Microsoft SSO Quick Start

## Quick Setup (5 minutes)

### 1. Install Dependencies

**Frontend:**
```bash
cd frontend
npm install
```

**Backend:**
```bash
pip install -r requirements.txt
```

### 2. Register App in Azure Portal

1. Go to https://portal.azure.com → **Azure Active Directory** → **App registrations**
2. Click **"New registration"**
3. Name: `Accounting System`
4. Redirect URI: `http://localhost:3000` (Platform: Single-page application)
5. Click **Register**
6. Copy **Application (client) ID** and **Directory (tenant) ID**

### 3. Configure Environment Variables

**Frontend** (`frontend/.env`):
```env
VITE_AZURE_CLIENT_ID=your-client-id
VITE_AZURE_TENANT_ID=your-tenant-id
```

**Backend** (export or add to startup script):
```bash
export AZURE_TENANT_ID=your-tenant-id
export AZURE_CLIENT_ID=your-client-id
export ENABLE_AUTH=1
```

### 4. Start the Application

```bash
# Terminal 1 - Backend
./start_backend.sh

# Terminal 2 - Frontend
cd frontend && npm run dev
```

### 5. Test Login

1. Open http://localhost:3000
2. Click **"Sign in with Microsoft"**
3. Complete Microsoft login
4. You're in! 🎉

## Disable Authentication (Development)

To disable auth temporarily:

**Backend**: Don't set `ENABLE_AUTH=1` (or set to `0`)

The frontend will still show login, but backend won't require authentication.

## Production Deployment

1. Update redirect URI in Azure Portal to your production URL
2. Use HTTPS (required for Microsoft auth)
3. Set environment variables securely (use Azure Key Vault or similar)

For detailed setup instructions, see [MICROSOFT_SSO_SETUP.md](./MICROSOFT_SSO_SETUP.md)

