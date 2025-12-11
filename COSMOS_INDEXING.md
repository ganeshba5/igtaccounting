# Cosmos DB Indexing Notes

## Issue: ORDER BY Requires Composite Index

Cosmos DB requires composite indexes for ORDER BY queries with multiple fields.

### Error Message
```
The order by query does not have a corresponding composite index that it can be served from.
```

### Solution Applied

We've removed ORDER BY clauses from Cosmos DB queries and sort in Python instead:

**Before:**
```sql
SELECT * FROM c ORDER BY c.transaction_date DESC, c.transaction_id DESC
```

**After:**
```python
transactions = query_items(...)  # No ORDER BY
transactions.sort(key=lambda x: (x.get('transaction_date'), x.get('transaction_id')), reverse=True)
```

### Routes Updated

1. ✅ `get_businesses()` - Sort by name in Python
2. ✅ `get_chart_of_accounts()` - Sort by account_code in Python  
3. ✅ `get_transactions()` - Sort by transaction_date, transaction_id in Python

### Alternative: Create Composite Indexes

If you want to use ORDER BY in queries (for better performance), you can create composite indexes in Azure Portal:

1. Go to Azure Portal → Cosmos DB account
2. Data Explorer → Select database → Select container
3. Click "Scale & Settings"
4. Under "Indexing Policy", add composite indexes:

**For transactions:**
```json
{
  "compositeIndexes": [
    [
      { "path": "/transaction_date", "order": "descending" },
      { "path": "/transaction_id", "order": "descending" }
    ]
  ]
}
```

**For chart_of_accounts:**
```json
{
  "compositeIndexes": [
    [
      { "path": "/account_code", "order": "ascending" }
    ]
  ]
}
```

**For businesses:**
```json
{
  "compositeIndexes": [
    [
      { "path": "/name", "order": "ascending" }
    ]
  ]
}
```

### Performance Note

- **Python sorting**: Works immediately, no setup needed, but slower for large datasets
- **Composite indexes**: Better performance, but requires index creation and uses more storage

For most use cases with small to medium datasets, Python sorting is sufficient.

