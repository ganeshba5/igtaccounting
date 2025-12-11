# Azure Cosmos DB Migration Guide

## Current Architecture
- **Database**: SQLite (relational)
- **Key Features**:
  - Complex JOIN queries across multiple tables
  - Foreign key relationships
  - Transactional integrity (double-entry bookkeeping)
  - Aggregations and GROUP BY operations
  - Hierarchical data (parent/child accounts)
  - Date range filtering

## Recommended API: **SQL API (Core SQL)**

### Why SQL API is Best for This Application

1. **SQL-like Query Language**: Most similar to your current SQLite queries
2. **JOIN Support**: Supports JOINs (with some limitations) for relational queries
3. **Aggregations**: Supports SUM, COUNT, GROUP BY, HAVING
4. **Easier Migration Path**: Minimal code changes compared to other APIs
5. **Partitioning Strategy**: Can partition by `business_id` for multi-tenant scalability

### Limitations to Consider

1. **JOIN Limitations**:
   - Only supports self-joins and single-level joins (not multi-level)
   - JOINs can only be within the same partition
   - May need to restructure some queries

2. **No Foreign Key Constraints**: 
   - Referential integrity must be enforced in application code
   - Cascading deletes must be implemented manually

3. **Transaction Scope**:
   - Transactions limited to single partition
   - For double-entry bookkeeping, ensure transaction and lines are in same partition

4. **Data Modeling**:
   - Need to denormalize some data (embed related data in documents)
   - Use references for relationships that span partitions

## Alternative: Azure SQL Database

**Consider Azure SQL Database instead** if you need:
- Full relational database features
- Complex multi-table JOINs
- Foreign key constraints
- ACID transactions across multiple tables
- Easier migration path (minimal code changes)

Azure SQL Database might be a better fit for this accounting application due to its relational nature and transactional requirements.

## Data Modeling Strategy for Cosmos DB SQL API

### Container Design

**Option 1: Single Container (Recommended for Start)**
- **Container**: `accounting-data`
- **Partition Key**: `/business_id`
- **Document Types**: Use `type` field to distinguish document types
  - `business`
  - `account_type`
  - `chart_of_account`
  - `bank_account`
  - `credit_card_account`
  - `loan_account`
  - `transaction`
  - `transaction_line`
  - `transaction_type_mapping`

**Option 2: Multiple Containers (Better for Scale)**
- `businesses` (partition: `/id`)
- `account_types` (partition: `/id` - small, can be single partition)
- `chart_of_accounts` (partition: `/business_id`)
- `bank_accounts` (partition: `/business_id`)
- `credit_card_accounts` (partition: `/business_id`)
- `loan_accounts` (partition: `/business_id`)
- `transactions` (partition: `/business_id`)
- `transaction_lines` (partition: `/business_id`) - **CRITICAL**: Must be same partition as parent transaction
- `transaction_type_mappings` (partition: `/id`)

### Document Structure Examples

#### Transaction (with embedded lines)
```json
{
  "id": "transaction-123",
  "type": "transaction",
  "business_id": 1,
  "transaction_id": 123,
  "transaction_date": "2025-01-15",
  "description": "Payment received",
  "reference_number": "INV-001",
  "transaction_type": "PAYMENT_RECEIVED",
  "amount": 1000.00,
  "created_at": "2025-01-15T10:00:00Z",
  "lines": [
    {
      "id": "line-456",
      "chart_of_account_id": 10,
      "debit_amount": 0,
      "credit_amount": 1000.00,
      "account_code": "4100",
      "account_name": "Service Revenue"
    },
    {
      "id": "line-457",
      "chart_of_account_id": 5,
      "debit_amount": 1000.00,
      "credit_amount": 0,
      "account_code": "1000",
      "account_name": "Bank Account"
    }
  ]
}
```

#### Chart of Account
```json
{
  "id": "chart-10",
  "type": "chart_of_account",
  "business_id": 1,
  "account_id": 10,
  "account_type_id": 5,
  "account_code": "4100",
  "account_name": "Service Revenue",
  "description": "Revenue from services",
  "parent_account_id": 9,
  "is_active": true,
  "account_type": {
    "id": 5,
    "code": "REVENUE",
    "name": "Revenue",
    "category": "REVENUE",
    "normal_balance": "CREDIT"
  }
}
```

### Key Design Decisions

1. **Embed Transaction Lines**: Store `transaction_lines` as an array within `transactions` document to ensure atomicity and avoid cross-partition queries

2. **Denormalize Account Type**: Embed account type info in chart_of_accounts for faster queries (can still maintain reference)

3. **Reference vs Embed**:
   - **Embed**: Transaction lines (always accessed together)
   - **Reference**: Chart of accounts in transaction lines (use account_id, join when needed)

4. **Partition Strategy**: Always partition by `business_id` to ensure:
   - All business data is co-located
   - Queries are scoped to single partition
   - Transactions and lines stay together

## Migration Steps

### Phase 1: Setup
1. Create Cosmos DB account with SQL API
2. Create containers with appropriate partition keys
3. Set up connection string and SDK

### Phase 2: Data Migration
1. Export data from SQLite
2. Transform to Cosmos DB document format
3. Import into Cosmos DB containers

### Phase 3: Code Changes
1. Replace `sqlite3` with `azure-cosmos` SDK
2. Update `database.py` to use Cosmos DB client
3. Refactor queries:
   - Convert SQL JOINs to Cosmos DB queries
   - Handle cross-partition queries where needed
   - Implement application-level referential integrity

### Phase 4: Testing
1. Test all CRUD operations
2. Verify double-entry bookkeeping integrity
3. Test report generation queries
4. Performance testing

## Code Changes Required

### Database Connection (`database.py`)

**Before (SQLite):**
```python
import sqlite3

def get_db_connection():
    conn = sqlite3.connect('accounting.db')
    conn.row_factory = sqlite3.Row
    return conn
```

**After (Cosmos DB):**
```python
from azure.cosmos import CosmosClient, PartitionKey
import os

COSMOS_ENDPOINT = os.environ.get('COSMOS_ENDPOINT')
COSMOS_KEY = os.environ.get('COSMOS_KEY')
DATABASE_NAME = 'accounting-db'

client = CosmosClient(COSMOS_ENDPOINT, COSMOS_KEY)
database = client.get_database_client(DATABASE_NAME)

def get_container(container_name):
    return database.get_container_client(container_name)
```

### Query Examples

**Before (SQLite):**
```python
accounts = conn.execute('''
    SELECT coa.*, at.code as account_type_code, at.name as account_type_name
    FROM chart_of_accounts coa
    LEFT JOIN account_types at ON coa.account_type_id = at.id
    WHERE coa.business_id = ?
''', (business_id,)).fetchall()
```

**After (Cosmos DB):**
```python
container = get_container('chart_of_accounts')
query = "SELECT * FROM c WHERE c.business_id = @business_id"
parameters = [{"name": "@business_id", "value": business_id}]
accounts = list(container.query_items(query=query, parameters=parameters))
```

## Cost Considerations

- **Request Units (RUs)**: Cosmos DB charges per RU consumed
- **Provisioned Throughput**: Fixed cost, predictable performance
- **Serverless**: Pay per request, good for variable workloads
- **Estimated Cost**: ~$25-100/month for small to medium workloads

## Performance Optimization

1. **Indexing**: Create composite indexes for common query patterns
2. **Query Optimization**: Use parameterized queries, avoid SELECT *
3. **Caching**: Cache account_types and other lookup data
4. **Connection Pooling**: Reuse Cosmos DB client instances

## Recommendation

**For this accounting application, I recommend:**

1. **Short-term**: Consider **Azure SQL Database** instead of Cosmos DB
   - Better fit for relational data
   - Easier migration
   - Lower cost for this use case
   - Full SQL support

2. **If using Cosmos DB**: Use **SQL API** with:
   - Multiple containers (one per entity type)
   - Partition by `business_id`
   - Embed transaction lines in transactions
   - Denormalize frequently joined data

3. **Hybrid Approach**: 
   - Use Azure SQL Database for transactional data
   - Use Cosmos DB for analytics/reporting (if needed)

## Next Steps

1. Evaluate Azure SQL Database vs Cosmos DB for your specific needs
2. If proceeding with Cosmos DB:
   - Set up Cosmos DB account
   - Design container structure
   - Create migration script
   - Update application code incrementally

