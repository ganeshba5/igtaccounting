# SQLite vs Cosmos DB Query Comparison

This document shows how common queries translate from SQLite to Cosmos DB SQL API.

## Basic SELECT Queries

### Get All Businesses

**SQLite:**
```sql
SELECT * FROM businesses ORDER BY name
```

**Cosmos DB:**
```sql
SELECT c.business_id as id, c.name, c.created_at, c.updated_at 
FROM c 
WHERE c.type = "business" 
ORDER BY c.name
```

**Python (SQLite):**
```python
conn = get_db_connection()
businesses = conn.execute('SELECT * FROM businesses ORDER BY name').fetchall()
```

**Python (Cosmos DB):**
```python
from database_cosmos import query_items
businesses = query_items(
    'businesses',
    'SELECT c.business_id as id, c.name FROM c WHERE c.type = "business" ORDER BY c.name',
    partition_key=None  # Cross-partition query
)
```

---

## JOIN Queries

### Get Chart of Accounts with Account Types

**SQLite:**
```sql
SELECT coa.*, at.code as account_type_code, at.name as account_type_name
FROM chart_of_accounts coa
LEFT JOIN account_types at ON coa.account_type_id = at.id
WHERE coa.business_id = ?
```

**Cosmos DB:**
```sql
-- Account type is embedded, so no JOIN needed
SELECT 
    c.account_id as id,
    c.account_code,
    c.account_name,
    c.account_type.code as account_type_code,
    c.account_type.name as account_type_name
FROM c 
WHERE c.type = "chart_of_account" AND c.business_id = @business_id
```

**Note:** We denormalize account_type into chart_of_accounts documents to avoid JOINs.

---

## Aggregation Queries

### Count Transactions by Business

**SQLite:**
```sql
SELECT business_id, COUNT(*) as count
FROM transactions
GROUP BY business_id
```

**Cosmos DB:**
```sql
SELECT c.business_id, COUNT(1) as count
FROM c
WHERE c.type = "transaction"
GROUP BY c.business_id
```

**Python (Cosmos DB):**
```python
from database_cosmos import query_items
results = query_items(
    'transactions',
    'SELECT c.business_id, COUNT(1) as count FROM c WHERE c.type = "transaction" GROUP BY c.business_id',
    partition_key=None  # Cross-partition aggregation
)
```

---

## Date Range Queries

### Get Transactions in Date Range

**SQLite:**
```sql
SELECT * FROM transactions
WHERE business_id = ? 
  AND transaction_date >= ? 
  AND transaction_date <= ?
ORDER BY transaction_date DESC
```

**Cosmos DB:**
```sql
SELECT * FROM c
WHERE c.type = "transaction"
  AND c.business_id = @business_id
  AND c.transaction_date >= @start_date
  AND c.transaction_date <= @end_date
ORDER BY c.transaction_date DESC
```

**Python (Cosmos DB):**
```python
from database_cosmos import query_items
transactions = query_items(
    'transactions',
    '''
    SELECT * FROM c
    WHERE c.type = "transaction"
      AND c.business_id = @business_id
      AND c.transaction_date >= @start_date
      AND c.transaction_date <= @end_date
    ORDER BY c.transaction_date DESC
    ''',
    parameters=[
        {"name": "@business_id", "value": 1},
        {"name": "@start_date", "value": "2025-01-01"},
        {"name": "@end_date", "value": "2025-12-31"}
    ],
    partition_key="1"  # Single partition query (faster)
)
```

---

## Complex JOIN with Aggregation

### Profit & Loss Report (Revenue/Expense Accounts with Balances)

**SQLite:**
```sql
SELECT 
    coa.id as account_id,
    coa.account_code,
    coa.account_name,
    at.category,
    COALESCE(SUM(CASE WHEN at.category = 'REVENUE' 
                 THEN tl.credit_amount - tl.debit_amount 
                 ELSE tl.debit_amount - tl.credit_amount END), 0) as balance
FROM chart_of_accounts coa
JOIN account_types at ON coa.account_type_id = at.id
LEFT JOIN transaction_lines tl ON tl.chart_of_account_id = coa.id
LEFT JOIN transactions t ON tl.transaction_id = t.id 
    AND DATE(t.transaction_date) >= DATE(?)
    AND DATE(t.transaction_date) <= DATE(?)
WHERE at.category IN ('REVENUE', 'EXPENSE')
  AND coa.business_id = ?
  AND coa.is_active = 1
GROUP BY coa.id
HAVING ABS(balance) >= 0.01
```

**Cosmos DB Approach:**

Cosmos DB doesn't support complex multi-table JOINs like this. We need a different approach:

**Option 1: Query and Aggregate in Application Code**
```python
from database_cosmos import get_chart_of_accounts, get_transactions

# Get accounts
accounts = get_chart_of_accounts(business_id)
revenue_expense = [a for a in accounts 
                   if a.get('account_type', {}).get('category') in ('REVENUE', 'EXPENSE')]

# Get transactions
transactions = get_transactions(business_id, start_date, end_date)

# Aggregate in Python
account_balances = {}
for txn in transactions:
    for line in txn.get('lines', []):
        account_id = line.get('chart_of_account_id')
        if account_id:
            if account_id not in account_balances:
                account_balances[account_id] = {'debit': 0, 'credit': 0}
            account_balances[account_id]['debit'] += line.get('debit_amount', 0)
            account_balances[account_id]['credit'] += line.get('credit_amount', 0)

# Calculate balances
for acc in revenue_expense:
    account_id = acc['id']
    if account_id in account_balances:
        category = acc.get('account_type', {}).get('category')
        if category == 'REVENUE':
            acc['balance'] = account_balances[account_id]['credit'] - account_balances[account_id]['debit']
        else:
            acc['balance'] = account_balances[account_id]['debit'] - account_balances[account_id]['credit']
    else:
        acc['balance'] = 0

# Filter zeros
result = [a for a in revenue_expense if abs(a.get('balance', 0)) >= 0.01]
```

**Option 2: Pre-aggregate Balances (Materialized View Pattern)**
- Store account balances in chart_of_accounts documents
- Update balances when transactions are created/modified
- Query becomes simple: `SELECT * FROM c WHERE c.business_id = @business_id AND c.balance != 0`

---

## Subqueries

### Get Transactions with Account Names

**SQLite:**
```sql
SELECT t.*, 
       (SELECT account_name FROM chart_of_accounts WHERE id = t.chart_of_account_id) as account_name
FROM transactions t
```

**Cosmos DB:**
```sql
-- Not directly supported. Need to:
-- 1. Query transactions
-- 2. Query chart_of_accounts separately
-- 3. Join in application code

-- Or embed account_name in transaction document (denormalization)
SELECT * FROM c
WHERE c.type = "transaction"
```

---

## INSERT Queries

### Create a Business

**SQLite:**
```python
cursor.execute('INSERT INTO businesses (name) VALUES (?)', (name,))
business_id = cursor.lastrowid
conn.commit()
```

**Cosmos DB:**
```python
from database_cosmos import create_item
business_doc = {
    'id': f'business-{next_id}',
    'type': 'business',
    'business_id': next_id,
    'name': name,
    'created_at': datetime.utcnow().isoformat()
}
created = create_item('businesses', business_doc, partition_key=str(next_id))
```

---

## UPDATE Queries

### Update Business Name

**SQLite:**
```sql
UPDATE businesses SET name = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?
```

**Cosmos DB:**
```python
from database_cosmos import get_item, update_item

business = get_item('businesses', f'business-{business_id}', partition_key=str(business_id))
business['name'] = new_name
business['updated_at'] = datetime.utcnow().isoformat()
updated = update_item('businesses', business, partition_key=str(business_id))
```

---

## DELETE Queries

### Delete Business (with Cascading)

**SQLite:**
```sql
-- Cascading delete handled by foreign keys
DELETE FROM businesses WHERE id = ?
```

**Cosmos DB:**
```python
from database_cosmos import delete_item, query_items

# Delete business
delete_item('businesses', f'business-{business_id}', partition_key=str(business_id))

# Manually delete related data (no foreign key constraints)
# Delete chart of accounts
accounts = query_items('chart_of_accounts', 
    'SELECT c.id FROM c WHERE c.business_id = @business_id',
    [{"name": "@business_id", "value": business_id}],
    partition_key=str(business_id))
for acc in accounts:
    delete_item('chart_of_accounts', acc['id'], partition_key=str(business_id))

# Delete transactions
transactions = query_items('transactions',
    'SELECT c.id FROM c WHERE c.business_id = @business_id',
    [{"name": "@business_id", "value": business_id}],
    partition_key=str(business_id))
for txn in transactions:
    delete_item('transactions', txn['id'], partition_key=str(business_id))
```

---

## Key Differences Summary

| Feature | SQLite | Cosmos DB |
|---------|--------|-----------|
| **JOINs** | Full SQL JOIN support | Limited (self-joins, single-level) |
| **Foreign Keys** | Enforced by database | Must enforce in application |
| **Transactions** | ACID across all tables | Limited to single partition |
| **Aggregations** | Full GROUP BY, HAVING | Supported but limited |
| **Subqueries** | Full support | Limited support |
| **Partitioning** | N/A | Must use partition keys for performance |
| **Denormalization** | Optional | Often required for performance |
| **ID Generation** | AUTOINCREMENT | Must generate manually (UUIDs recommended) |

---

## Best Practices for Cosmos DB

1. **Always use partition keys** in queries when possible (faster, cheaper)
2. **Denormalize frequently joined data** (embed account_type in chart_of_accounts)
3. **Embed related data** that's always accessed together (transaction_lines in transactions)
4. **Pre-aggregate** complex calculations when possible
5. **Use application-level joins** for complex relationships
6. **Monitor RU consumption** and optimize queries
7. **Use composite indexes** for common query patterns
8. **Consider materialized views** for complex reports

