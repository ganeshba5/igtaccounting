# Starting Server with Azure Cosmos DB

## Quick Start

### Step 1: Set Environment Variables

```bash
export COSMOS_ENDPOINT="https://your-account.documents.azure.com:443/"
export COSMOS_KEY="your-primary-key"
export DATABASE_NAME="accounting-db"  # Optional, defaults to 'accounting-db'
export USE_COSMOS_DB=1
```

### Step 2: Start the Server

**Option A: Use the convenience script (recommended)**
```bash
./start_backend_cosmos.sh
```

**Option B: Manual start**
```bash
export USE_COSMOS_DB=1
cd backend
python3 app.py
```

**Option C: Single server mode (with frontend)**
```bash
export USE_COSMOS_DB=1
export COSMOS_ENDPOINT="https://your-account.documents.azure.com:443/"
export COSMOS_KEY="your-primary-key"
./start_single_server.sh
```

## Important Note

⚠️ **Current Status**: The application has been updated to **initialize** Cosmos DB, but **most API routes still use SQLite**. 

To fully enable Cosmos DB:
1. The routes need to be updated to use Cosmos DB functions (see `backend/app_cosmos_example.py` for examples)
2. OR continue using SQLite for now and migrate routes incrementally

## What's Currently Working

✅ Database initialization detects Cosmos DB mode  
✅ Environment variable setup  
✅ Startup scripts created  

## What Needs Work

⚠️ API routes need to be updated to use Cosmos DB functions  
⚠️ Some routes may still use SQLite queries  

## Testing Cosmos DB Connection

You can test if Cosmos DB is accessible:

```bash
python3 -c "
import os
os.environ['USE_COSMOS_DB'] = '1'
os.environ['COSMOS_ENDPOINT'] = 'your-endpoint'
os.environ['COSMOS_KEY'] = 'your-key'
from backend.database_cosmos import get_businesses
businesses = get_businesses()
print(f'Found {len(businesses)} businesses in Cosmos DB')
"
```

## Switching Back to SQLite

To use SQLite again, simply don't set `USE_COSMOS_DB`:

```bash
./start_backend.sh  # Uses SQLite by default
```

Or explicitly unset it:

```bash
unset USE_COSMOS_DB
./start_backend.sh
```

## Next Steps for Full Cosmos DB Support

1. **Incremental Migration**: Update routes one at a time
   - Start with simple GET routes (businesses, account types)
   - Then move to more complex routes (transactions, reports)

2. **Use Example Code**: See `backend/app_cosmos_example.py` for reference implementations

3. **Test Thoroughly**: Verify each route works correctly with Cosmos DB

4. **Update Reports**: P&L and Balance Sheet reports need significant refactoring for Cosmos DB

## Troubleshooting

### Error: "COSMOS_ENDPOINT and COSMOS_KEY must be set"

**Solution**: Make sure environment variables are exported before starting:
```bash
export COSMOS_ENDPOINT="your-endpoint"
export COSMOS_KEY="your-key"
export USE_COSMOS_DB=1
./start_backend_cosmos.sh
```

### Error: "ModuleNotFoundError: No module named 'azure'"

**Solution**: Install the Cosmos DB SDK:
```bash
pip install azure-cosmos
```

### Routes Still Using SQLite

**This is expected** - routes need to be updated. The app will initialize Cosmos DB but routes may still query SQLite until they're migrated.

