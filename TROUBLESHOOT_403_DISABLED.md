# Troubleshooting 403 Site Disabled

## The Issue

Even after starting the App Service, you're still getting:
```
HTTP/1.1 403 Site Disabled
```

## Possible Causes

1. **App Service still starting** (takes 1-2 minutes after Start command)
2. **No code deployed yet** (App Service exists but nothing is running)
3. **Startup command issue** (wrong path or command)
4. **Deployment slot issue** (wrong slot is running)

## Step-by-Step Troubleshooting

### Step 1: Check App Service Status

```bash
az webapp show --name igtacct-api --resource-group YOUR_RESOURCE_GROUP --query state -o tsv
```

Should return: `Running`

### Step 2: Check if Code is Deployed

In Azure Portal:
1. Go to **App Service** → **Deployment Center**
2. Check if there's a deployment listed
3. If empty, the app hasn't been deployed yet

### Step 3: Check Application Logs

In Azure Portal:
1. Go to **App Service** → **Log stream**
2. Or go to **Monitoring** → **Log stream**
3. Check for errors or startup messages

You should see:
- Gunicorn starting
- Flask app loading
- Any Python errors

### Step 4: Verify Startup Command

Go to **Configuration** → **General settings** → **Startup Command**

Should be:
```
gunicorn --bind 0.0.0.0:8000 --timeout 120 --workers 4 --chdir backend app:app
```

Make sure:
- ✅ Command is correct
- ✅ Path to backend folder is correct
- ✅ Clicked **Save**

### Step 5: Check if Default App is Running

Test the root URL:

```bash
curl https://igtacct-api-azaghzb4chhagvc3.eastus-01.azurewebsites.net/
```

If you get a default Azure welcome page or HTML, the app is running but maybe not your code.

### Step 6: Force a Restart

In Azure Portal:
1. Go to **App Service** → **Overview**
2. Click **Restart**
3. Wait 1-2 minutes
4. Test again

### Step 7: Check if Deployment Happened

The App Service might be running but empty if:
- GitHub Actions workflow hasn't run yet
- Deployment failed
- No code has been pushed to trigger deployment

**Check GitHub Actions**:
1. Go to GitHub → Your repo → Actions
2. Look for "Azure App Service Deployment" workflow
3. Check if it ran and succeeded

## Quick Fix: Manual Deployment Test

If no deployment has happened, you can test with a simple file:

1. Go to **App Service** → **Development Tools** → **SSH** or **Advanced Tools** → **Go**
2. Or use **Deployment Center** to trigger a deployment

## Most Likely Issue

If you just created the App Service and haven't pushed code yet, there's nothing deployed to run!

**Solution**: Push your code to GitHub to trigger the deployment workflow, or deploy manually.

## Verify Deployment Status

Check if there's any code deployed:

```bash
az webapp deployment list --name igtacct-api --resource-group YOUR_RESOURCE_GROUP
```

If empty, you need to deploy code first.

## Next Steps

1. **If no deployment**: Push code to GitHub or deploy manually
2. **If deployment exists**: Check logs for errors
3. **If logs show errors**: Fix the startup command or code issues
4. **Wait a bit**: Sometimes takes 2-3 minutes after restart to fully start

