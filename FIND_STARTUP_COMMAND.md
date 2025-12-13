# How to Find Startup Command in Azure Portal

## Location 1: Configuration → General Settings (Most Common)

1. Go to **Azure Portal** → **App Service** (`igtacct-api`)
2. In the left sidebar, click **Configuration**
3. Click the **General settings** tab (not "Application settings")
4. Scroll down to find **Startup Command** field
5. Enter the command there

**Note**: If you don't see "General settings" tab, look for a **Settings** section or try Location 2 below.

## Location 2: Deployment Center

1. Go to **Azure Portal** → **App Service** (`igtacct-api`)
2. In the left sidebar, click **Deployment Center**
3. Look for **Settings** or **Configuration** tab
4. Find **Startup Command** field

## Location 3: Settings → General Settings

1. Go to **Azure Portal** → **App Service** (`igtacct-api`)
2. In the left sidebar, look for **Settings** → **General settings**
3. Find **Startup Command** field

## Location 4: Using Azure CLI (If Portal Doesn't Show It)

If you can't find it in the portal, you can set it via Azure CLI:

```bash
az webapp config set \
  --name igtacct-api \
  --resource-group YOUR_RESOURCE_GROUP \
  --startup-file "gunicorn --bind 0.0.0.0:8000 --timeout 120 --workers 4 --chdir backend app:app"
```

Or check if it's set:

```bash
az webapp config show \
  --name igtacct-api \
  --resource-group YOUR_RESOURCE_GROUP \
  --query linuxFxVersion
```

## If Startup Command Field Doesn't Exist

For Linux App Services, you might need to:

1. Go to **Configuration** → **General settings**
2. Make sure **Stack settings** shows:
   - **Stack**: Python
   - **Major version**: 3.12 (or your Python version)
3. The **Startup Command** field should appear below the stack settings

## Alternative: Use a Startup Script

If the startup command field isn't available, you can create a startup script:

1. Create a file called `startup.sh` in your repository root (already exists!)
2. Make it executable
3. Set the startup command to: `bash startup.sh`

The startup command would be:
```
bash startup.sh
```

## What to Enter

Once you find the field, enter:

```
gunicorn --bind 0.0.0.0:8000 --timeout 120 --workers 4 --chdir backend app:app
```

**Important**:
- Must include `--chdir backend` (changes to backend directory before starting)
- Must include `app:app` (the Flask app instance)
- Port must match PORT environment variable (default 8000)

## Quick Check via Azure CLI

To see current configuration:

```bash
az webapp config show \
  --name igtacct-api \
  --resource-group YOUR_RESOURCE_GROUP \
  --query "{linuxFxVersion:linuxFxVersion, appCommandLine:appCommandLine}" \
  -o json
```

This will show if a startup command is already set.

