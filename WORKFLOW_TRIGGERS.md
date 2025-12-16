# GitHub Actions Workflow Triggers

## App Service (Backend) Workflow

**File**: `.github/workflows/azure-app-service.yml`

**Triggers when**:
- Files in `backend/**` change
- `requirements.txt` changes
- `azure-app-service-requirements.txt` changes
- `.github/workflows/azure-app-service.yml` changes
- **Manual trigger** via "workflow_dispatch" button in GitHub Actions UI

**Does NOT trigger when**:
- Frontend files change
- Documentation files change
- `.gitignore` changes
- Other non-backend files change

This is **by design** - the backend only needs to redeploy when backend code or dependencies change.

## Static Web Apps (Frontend) Workflow

**File**: `.github/workflows/azure-static-web-apps-thankful-rock-0bea0c80f.yml`

**Triggers when**:
- Any file changes (no path restrictions)
- Manual trigger via workflow_dispatch

## Manual Trigger

If you need to manually trigger the App Service deployment:

1. Go to: https://github.com/ganeshba5/igtaccounting/actions
2. Click on "Azure App Service Deployment"
3. Click "Run workflow" button (top right)
4. Select branch: `main`
5. Click "Run workflow"

This is useful when:
- You want to redeploy without changing code
- Configuration changes were made in Azure Portal
- Troubleshooting deployment issues

