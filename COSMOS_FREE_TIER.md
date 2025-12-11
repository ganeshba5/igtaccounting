# Cosmos DB Free Tier Setup Guide

## The Problem with Free Tier

Azure Cosmos DB **free tier** has a **1000 RU/s account limit**. However:

- **Minimum throughput per container**: 400 RU/s
- **Number of containers needed**: 8
- **Per-container approach**: 8 × 400 = **3,200 RU/s** ❌ (exceeds limit!)

## Solution: Shared Throughput at Database Level

For free tier with multiple containers, you **must use shared throughput** at the database level. This allows all containers to share a single throughput pool.

### How Shared Throughput Works

- Allocate throughput at the **database level** (e.g., 400 RU/s)
- All containers in that database **share** this throughput
- You can have unlimited containers (they all share the 400 RU/s)
- Perfect for free tier! ✅

## Setup Instructions

### Step 1: Set Environment Variables

```bash
export COSMOS_ENDPOINT="https://your-account.documents.azure.com:443/"
export COSMOS_KEY="your-primary-key"
export DATABASE_NAME="accounting-db"

# Enable shared throughput
export COSMOS_SHARED_THROUGHPUT=true
export COSMOS_SHARED_THROUGHPUT_VALUE=400
```

### Step 2: Run Migration

```bash
python migrate_to_cosmos.py
```

This will:
- Create database with 400 RU/s shared throughput
- Create all 8 containers (they share the 400 RU/s)
- Stay within your 1000 RU/s account limit ✅

## Why 400 RU/s?

- **Minimum allowed**: 400 RU/s (Cosmos DB requirement)
- **Well under limit**: 400 RU/s < 1000 RU/s limit ✅
- **Sufficient for testing**: Good for development and low-traffic scenarios

## Performance Considerations

### Shared Throughput Limitations

- All containers **compete** for the same 400 RU/s pool
- If one container is busy, others may be slower
- For production with high traffic, consider:
  - Upgrading to higher account tier
  - Using dedicated throughput per container (requires more RU/s)

### When Shared Throughput is Fine

- ✅ Development/Testing
- ✅ Low-traffic applications
- ✅ Free tier accounts
- ✅ Applications where not all containers are active simultaneously

### When You Need More

If you need better performance:

1. **Upgrade Account Tier**: Increase account RU/s limit
2. **Use Per-Container Throughput**: After upgrade, you can allocate dedicated throughput
3. **Use Serverless**: Create a new serverless account (different account type)

## Example: Setting Up for Free Tier

```bash
# 1. Set connection details
export COSMOS_ENDPOINT="https://accounting-cosmos-db.documents.azure.com:443/"
export COSMOS_KEY="your-key-here"
export DATABASE_NAME="accounting-db"

# 2. Enable shared throughput (400 RU/s for all containers)
export COSMOS_SHARED_THROUGHPUT=true
export COSMOS_SHARED_THROUGHPUT_VALUE=400

# 3. Run migration
python migrate_to_cosmos.py
```

## Verifying Setup

After migration, check in Azure Portal:

1. Go to Cosmos DB account → **Data Explorer**
2. Select your database (`accounting-db`)
3. Click **Scale** tab
4. You should see: **"Shared throughput: 400 RU/s"**
5. All containers under this database share this throughput

## Troubleshooting

### Error: "Throughput limit exceeded"

- **Solution**: Make sure `COSMOS_SHARED_THROUGHPUT=true` is set
- Check that `COSMOS_SHARED_THROUGHPUT_VALUE=400` (minimum)

### Error: "Database already exists with different throughput"

- **Solution**: Delete the existing database in Azure Portal, then rerun migration
- Or use a different database name: `export DATABASE_NAME="accounting-db-v2"`

### Need to Change Shared Throughput Later

1. Azure Portal → Cosmos DB account → Data Explorer
2. Select database → **Scale**
3. Adjust RU/s (minimum 400)
4. Click **Save**

## Summary

**For Free Tier with Multiple Containers:**

```bash
export COSMOS_SHARED_THROUGHPUT=true
export COSMOS_SHARED_THROUGHPUT_VALUE=400
python migrate_to_cosmos.py
```

This is the **only way** to use free tier (1000 RU/s limit) with 8 containers, since each container requires minimum 400 RU/s when using per-container throughput.

✅ **Shared throughput = Solution for free tier!**

