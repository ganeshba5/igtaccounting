# Azure Cosmos DB Setup Guide

This guide walks you through setting up Azure Cosmos DB for the accounting application.

## Prerequisites

1. **Azure Account**: You need an active Azure subscription
2. **Azure CLI** (optional but recommended): For easier setup
3. **Python 3.8+**: For running migration scripts

## Step 1: Create Cosmos DB Account

### Option A: Using Azure Portal

1. Go to [Azure Portal](https://portal.azure.com)
2. Click "Create a resource"
3. Search for "Azure Cosmos DB"
4. Click "Create"
5. Fill in:
   - **Subscription**: Your subscription
   - **Resource Group**: Create new or use existing
   - **Account Name**: `accounting-cosmos-db` (must be globally unique)
   - **API**: Select **Core (SQL)**
   - **Location**: Choose closest to you
   - **Capacity mode**: Start with **Provisioned throughput** (400 RU/s minimum)
6. Click "Review + create", then "Create"
7. Wait for deployment (2-5 minutes)

### Option B: Using Azure CLI

```bash
# Login to Azure
az login

# Create resource group
az group create --name accounting-rg --location eastus

# Create Cosmos DB account
az cosmosdb create \
  --name accounting-cosmos-db \
  --resource-group accounting-rg \
  --default-consistency-level Session \
  --locations regionName=eastus failoverPriority=0
```

## Step 2: Get Connection Details

### From Azure Portal:

1. Go to your Cosmos DB account
2. Click "Keys" in the left menu
3. Copy:
   - **URI** (this is your `COSMOS_ENDPOINT`)
   - **PRIMARY KEY** (this is your `COSMOS_KEY`)

### From Azure CLI:

```bash
# Get endpoint
az cosmosdb show --name accounting-cosmos-db --resource-group accounting-rg --query documentEndpoint

# Get primary key
az cosmosdb keys list --name accounting-cosmos-db --resource-group accounting-rg --query primaryMasterKey
```

## Step 3: Install Python Dependencies

```bash
# Activate your virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install Cosmos DB SDK
pip install azure-cosmos

# Or install from requirements file
pip install -r requirements_cosmos.txt
```

## Step 4: Set Environment Variables

Create a `.env` file or export environment variables:

```bash
export COSMOS_ENDPOINT="https://accounting-cosmos-db.documents.azure.com:443/"
export COSMOS_KEY="your-primary-key-here"
export DATABASE_NAME="accounting-db"

# Optional: Use serverless mode (recommended for testing)
export COSMOS_SERVERLESS=true

# Or use provisioned throughput (default: 100 RU/s per container)
# export COSMOS_THROUGHPUT=100
```

Or create a `.env` file:

```env
COSMOS_ENDPOINT=https://accounting-cosmos-db.documents.azure.com:443/
COSMOS_KEY=your-primary-key-here
DATABASE_NAME=accounting-db
COSMOS_SERVERLESS=true
```

**Security Note**: Never commit `.env` files or keys to version control!

**Throughput Options:**
- **Serverless Mode** (`COSMOS_SERVERLESS=true`): Pay per request, no RU/s limits. Recommended for testing and low-traffic scenarios.
- **Provisioned Mode**: Set `COSMOS_THROUGHPUT` (default: 100 RU/s per container). Use if you need guaranteed performance.

## Step 5: Run Migration

```bash
# Make sure your SQLite database exists and has data
python migrate_to_cosmos.py
```

The migration script will:
1. Connect to your SQLite database
2. Connect to Cosmos DB
3. Create database and containers if they don't exist
4. Migrate all data
5. Show progress and any errors

## Step 6: Verify Migration

### Option A: Using Azure Portal

1. Go to your Cosmos DB account
2. Click "Data Explorer"
3. Expand your database and containers
4. Click on a container to view documents
5. Verify data looks correct

### Option B: Using Python

```bash
python -c "from backend.database_cosmos import get_businesses; print(get_businesses())"
```

## Step 7: Update Application (Optional)

To use Cosmos DB instead of SQLite, you can:

1. **Set environment variable**:
   ```bash
   export USE_COSMOS_DB=1
   ```

2. **Update `app.py`** to conditionally use Cosmos DB:
   ```python
   import os
   if os.environ.get('USE_COSMOS_DB') == '1':
       from database_cosmos import get_businesses, get_business, ...
   else:
       from database import get_db_connection, ...
   ```

## Cost Estimation

### Provisioned Throughput (Recommended for Production)

- **Minimum**: 400 RU/s per container × 8 containers = 3,200 RU/s
- **Cost**: ~$0.008 per 100 RU/s per hour
- **Monthly**: ~$184/month (3,200 RU/s × 24 hours × 30 days × $0.008)

### Serverless (Good for Development/Testing)

- **Cost**: $0.25 per million RU consumed
- **Estimated**: $5-20/month for light usage

### Tips to Reduce Costs

1. Start with **Serverless** mode for development
2. Use **Provisioned** mode for production with auto-scale
3. Monitor RU consumption in Azure Portal
4. Optimize queries (use partition keys, avoid cross-partition queries)
5. Consider consolidating containers if possible

## Troubleshooting

### Error: "COSMOS_ENDPOINT and COSMOS_KEY must be set"

- Make sure environment variables are exported
- Check that `.env` file is being loaded (if using python-dotenv)

### Error: "Resource with specified id, name, or unique index already exists"

- Container already exists, this is normal
- The script will use existing containers

### Error: "Your account is currently configured with a total throughput limit of X RU/s"

- **Solution 1** (Recommended): Use serverless mode:
  ```bash
  export COSMOS_SERVERLESS=true
  python migrate_to_cosmos.py
  ```
- **Solution 2**: Reduce throughput per container:
  ```bash
  export COSMOS_THROUGHPUT=100  # Lower RU/s per container
  python migrate_to_cosmos.py
  ```
- **Solution 3**: Increase your Cosmos DB account throughput limit in Azure Portal

### Error: "Request rate is large"

- Your RU/s is too low for the workload
- Increase throughput in Azure Portal or use Serverless mode

### Slow Queries

- Make sure you're using partition keys in queries
- Avoid cross-partition queries when possible
- Check RU consumption - may need more throughput

## Next Steps

1. Review the migrated data
2. Test application queries
3. Optimize partition keys if needed
4. Set up monitoring and alerts
5. Consider backup and disaster recovery

## Additional Resources

- [Azure Cosmos DB Documentation](https://docs.microsoft.com/azure/cosmos-db/)
- [Python SDK Documentation](https://docs.microsoft.com/python/api/overview/azure/cosmos-readme)
- [SQL API Query Reference](https://docs.microsoft.com/azure/cosmos-db/sql-query-getting-started)
- [Partitioning Best Practices](https://docs.microsoft.com/azure/cosmos-db/partitioning-overview)

