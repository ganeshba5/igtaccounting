# Cosmos DB Migration - Next Steps

## ✅ Migration Complete!

Your data has been successfully migrated from SQLite to Azure Cosmos DB.

## Step 1: Verify Migration

### Option A: Using Verification Script

```bash
python3 verify_cosmos_migration.py
```

This will:
- Count documents in each container
- Show sample documents
- Verify data structure

### Option B: Azure Portal

1. Go to [Azure Portal](https://portal.azure.com)
2. Navigate to your Cosmos DB account
3. Click **Data Explorer**
4. Expand your database (`accounting-db`)
5. Click on each container to view documents
6. Verify data looks correct

## Step 2: Test Cosmos DB Queries

Before switching your application, test that queries work:

```python
# Test script
from backend.database_cosmos import get_businesses, get_chart_of_accounts, get_transactions

# Test getting businesses
businesses = get_businesses()
print(f"Found {len(businesses)} businesses")

# Test getting chart of accounts for business 1
if businesses:
    business_id = businesses[0]['id']
    accounts = get_chart_of_accounts(business_id)
    print(f"Found {len(accounts)} accounts for business {business_id}")

# Test getting transactions
transactions = get_transactions(business_id=1, start_date='2025-01-01', end_date='2025-12-31')
print(f"Found {len(transactions)} transactions")
```

## Step 3: Update Application (Optional)

### Option A: Keep SQLite (Default)

Your application continues to use SQLite by default. No changes needed.

### Option B: Switch to Cosmos DB

To use Cosmos DB instead of SQLite:

1. **Set environment variable:**
   ```bash
   export USE_COSMOS_DB=1
   ```

2. **Modify `app.py`** to conditionally use Cosmos DB:
   
   Add near the top:
   ```python
   import os
   USE_COSMOS_DB = os.environ.get('USE_COSMOS_DB') == '1'
   
   if USE_COSMOS_DB:
       from database_cosmos import (
           get_businesses, get_business, 
           get_chart_of_accounts, get_transactions,
           create_item, update_item, delete_item
       )
   else:
       from database import get_db_connection, init_database
   ```

3. **Update routes** to use Cosmos DB functions when `USE_COSMOS_DB=True`

   See `backend/app_cosmos_example.py` for examples.

## Step 4: Performance Testing

Test query performance with Cosmos DB:

```bash
# Test query performance
python3 -c "
from backend.database_cosmos import get_transactions
import time

start = time.time()
transactions = get_transactions(business_id=1, start_date='2025-01-01', end_date='2025-12-31')
elapsed = time.time() - start
print(f'Query returned {len(transactions)} transactions in {elapsed:.2f} seconds')
"
```

## Step 5: Monitor Costs

### Check RU Consumption

1. Azure Portal → Cosmos DB account
2. Click **Metrics**
3. View **"Request Units consumed"**

### Cost Optimization Tips

- **Shared throughput** (current setup): 400 RU/s = ~$29/month
- Monitor throttling (429 errors) - may need to increase
- Use partition keys in queries (already configured)
- Consider caching frequently accessed data

## Important Notes

### Differences from SQLite

1. **No Foreign Key Constraints**: Validate relationships in application code
2. **Query Limitations**: Some complex JOINs need to be done in application code
3. **Transaction Scope**: Transactions limited to single partition (business_id)
4. **Partition Keys**: Always use partition keys in queries for best performance

### Data Structure

- **Transaction Lines**: Embedded in transactions (for atomicity)
- **Account Types**: Embedded in chart_of_accounts (denormalization)
- **All data**: Partitioned by `business_id` for scalability

## Troubleshooting

### Issue: Slow Queries

- **Solution**: Ensure queries use partition keys
- Check RU consumption - may need more throughput

### Issue: Throttling (429 errors)

- **Solution**: Increase shared throughput in Azure Portal
- Or optimize queries to use fewer RUs

### Issue: Missing Data

- **Solution**: Check migration logs
- Verify data in Azure Portal Data Explorer
- Re-run migration if needed (delete database first)

## Resources

- **Cosmos DB Documentation**: https://docs.microsoft.com/azure/cosmos-db/
- **Python SDK**: https://docs.microsoft.com/python/api/overview/azure/cosmos-readme
- **Query Reference**: See `QUERY_COMPARISON.md`

## Summary

✅ **Migration Complete** - All data migrated successfully  
✅ **Containers Created** - All 8 containers ready  
✅ **Shared Throughput** - 400 RU/s shared across all containers  
✅ **Free Tier Compatible** - Stays within 1000 RU/s limit  

Your application can now optionally use Cosmos DB by setting `USE_COSMOS_DB=1`, or continue using SQLite as default.

