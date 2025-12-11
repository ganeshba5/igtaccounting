# Cosmos DB Provisioned Account - Setup Guide

If your Cosmos DB account was created as **Provisioned** (not Serverless), you need to manage throughput differently.

## Understanding Account Types

### Provisioned Account (Your Case)
- Requires allocating RU/s (Request Units per second) upfront
- Charged based on allocated throughput (even if not used)
- Has throughput limits at the account level (e.g., 1000 RU/s for free tier)
- **Cannot** use serverless mode

### Serverless Account
- Pay per request (no upfront allocation)
- Automatic scaling
- Different account type - must be created as serverless
- **Cannot** allocate provisioned throughput

## Solution for Provisioned Accounts

Since your account has a **1000 RU/s limit** and you need to create **8 containers**, you have these options:

### Option 1: Use Lower Throughput Per Container (Recommended)

Use 50-100 RU/s per container to stay under the limit:

```bash
# 8 containers × 50 RU/s = 400 RU/s total (well under 1000)
export COSMOS_THROUGHPUT=50
python migrate_to_cosmos.py
```

Or even lower:

```bash
# 8 containers × 25 RU/s = 200 RU/s total
export COSMOS_THROUGHPUT=25
python migrate_to_cosmos.py
```

**Pros:**
- Works immediately
- No Azure changes needed
- Low cost

**Cons:**
- Lower performance per container
- May need to increase later for production

### Option 2: Increase Account Throughput Limit

1. Go to Azure Portal
2. Navigate to your Cosmos DB account
3. Click **"Scale & Settings"** or **"Features"**
4. Look for **"Maximum Throughput"** or **"Limit"** settings
5. Request increase (may require support ticket for free tier)

**Pros:**
- More throughput available
- Better for production

**Cons:**
- May cost more
- Free tier has limits

### Option 3: Use Shared Throughput at Database Level

Instead of per-container throughput, allocate throughput at the database level and share it:

1. In Azure Portal, go to your database
2. Click **"Scale"**
3. Select **"Shared throughput"** (if available)
4. Allocate throughput at database level (e.g., 400 RU/s)
5. Containers will share this throughput

**Note:** The migration script would need to be modified to support this.

### Option 4: Create New Serverless Account (If Possible)

If you're still in testing/development, consider creating a new Cosmos DB account:

1. In Azure Portal, create new Cosmos DB account
2. Choose **"Serverless"** as the capacity mode
3. Use the new endpoint and key
4. Run migration with `COSMOS_SERVERLESS=true`

**Pros:**
- No throughput limits
- Pay only for what you use
- Great for development

**Cons:**
- Need to create new account
- Need to migrate data

## Recommended Approach

For your current situation with a 1000 RU/s limit:

```bash
# Start with 50 RU/s per container (400 RU/s total)
export COSMOS_THROUGHPUT=50
python migrate_to_cosmos.py
```

This will:
- ✅ Work with your current account limits
- ✅ Allow all 8 containers to be created
- ✅ Provide basic performance for testing
- ✅ Be cost-effective

You can always increase throughput later if needed.

## Monitoring Throughput

After migration, monitor your RU consumption:

1. Go to Azure Portal → Cosmos DB account
2. Click **"Metrics"**
3. View **"Request Units consumed"**

If you see throttling (429 errors), increase throughput.

## Adjusting Throughput Later

You can change throughput per container:

1. Azure Portal → Cosmos DB account → Data Explorer
2. Select container → Click **"Scale"**
3. Adjust RU/s as needed

Or use Azure CLI:

```bash
az cosmosdb sql container throughput update \
  --account-name your-account-name \
  --database-name accounting-db \
  --name container-name \
  --throughput 400
```

## Summary

For a **provisioned account with 1000 RU/s limit**:

1. ✅ Use `COSMOS_THROUGHPUT=50` (or lower)
2. ✅ Run migration: `python migrate_to_cosmos.py`
3. ✅ Monitor RU consumption
4. ✅ Increase throughput later if needed

The script will work - just use lower throughput values to stay under your account limit!

