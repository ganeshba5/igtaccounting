"""
Cosmos DB database adapter for the accounting application.

This is a proof-of-concept implementation showing how to use Azure Cosmos DB
(SQL API) instead of SQLite.

Usage:
    Set environment variables:
        COSMOS_ENDPOINT - Your Cosmos DB endpoint
        COSMOS_KEY - Your Cosmos DB primary key
        DATABASE_NAME - Database name (default: 'accounting-db')
        USE_COSMOS_DB=1 - Enable Cosmos DB mode

    Then in app.py:
        from database_cosmos import get_container, query_items, create_item, etc.
"""

import os
import base64
from typing import Dict, List, Any, Optional
from azure.cosmos import CosmosClient, PartitionKey, exceptions
from azure.cosmos.database import DatabaseProxy
from azure.cosmos.container import ContainerProxy

# Configuration
COSMOS_ENDPOINT = os.environ.get('COSMOS_ENDPOINT')
COSMOS_KEY = os.environ.get('COSMOS_KEY')
DATABASE_NAME = os.environ.get('DATABASE_NAME', 'accounting-db')

# Global client and database (initialized on first use)
_client: Optional[CosmosClient] = None
_database: Optional[DatabaseProxy] = None

def get_cosmos_client() -> CosmosClient:
    """Get or create Cosmos DB client."""
    global _client
    if _client is None:
        if not COSMOS_ENDPOINT or not COSMOS_KEY:
            raise ValueError(
                "COSMOS_ENDPOINT and COSMOS_KEY environment variables must be set. "
                "Get these from your Azure Cosmos DB account in Azure Portal."
            )
        
        # Clean up the endpoint and key (remove whitespace, quotes, etc.)
        endpoint = COSMOS_ENDPOINT.strip().strip('"').strip("'")
        key = COSMOS_KEY.strip().strip('"').strip("'")
        
        # Check for placeholder values
        placeholder_indicators = ['your-endpoint', 'your-account', 'your-key', 'your-primary-key', 'example']
        if any(indicator in endpoint.lower() for indicator in placeholder_indicators):
            raise ValueError(
                "COSMOS_ENDPOINT appears to be a placeholder value. "
                "Please set the actual endpoint from Azure Portal → Cosmos DB account → Keys → URI"
            )
        if any(indicator in key.lower() for indicator in placeholder_indicators):
            raise ValueError(
                "COSMOS_KEY appears to be a placeholder value. "
                "Please set the actual PRIMARY KEY from Azure Portal → Cosmos DB account → Keys"
            )
        
        # Validate and fix key format (should be base64 encoded)
        try:
            # Remove any newlines or extra spaces
            key_clean = key.replace('\n', '').replace('\r', '').replace(' ', '')
            
            # Skip validation if key is too short (likely a placeholder)
            if len(key_clean) < 20:
                raise ValueError("Key appears to be too short. Cosmos DB keys are typically 88+ characters.")
            
            # Add padding if needed (base64 strings should be multiple of 4)
            missing_padding = len(key_clean) % 4
            if missing_padding:
                key_clean += '=' * (4 - missing_padding)
            
            # Try to decode to validate it's proper base64
            base64.b64decode(key_clean, validate=True)
            key = key_clean
        except ValueError as e:
            # Re-raise our custom ValueError
            raise
        except Exception as e:
            raise ValueError(
                f"Invalid COSMOS_KEY format. The key must be a valid base64-encoded string.\n"
                f"Error: {str(e)}\n\n"
                f"To fix this:\n"
                f"1. Go to Azure Portal → Your Cosmos DB account\n"
                f"2. Click 'Keys' in the left menu\n"
                f"3. Click the copy icon next to PRIMARY KEY (don't manually select text)\n"
                f"4. Paste it directly: export COSMOS_KEY='<pasted-key>'\n"
                f"5. Make sure there are no extra spaces or line breaks"
            )
        
        _client = CosmosClient(endpoint, key)
    return _client

def get_database() -> DatabaseProxy:
    """Get or create database."""
    global _database
    if _database is None:
        client = get_cosmos_client()
        try:
            _database = client.create_database_if_not_exists(id=DATABASE_NAME)
        except exceptions.CosmosResourceExistsError:
            _database = client.get_database_client(DATABASE_NAME)
    return _database

def get_container(container_name: str) -> ContainerProxy:
    """Get a container by name."""
    database = get_database()
    return database.get_container_client(container_name)

# ========== QUERY HELPERS ==========

def query_items(
    container_name: str,
    query: str,
    parameters: Optional[List[Dict[str, Any]]] = None,
    partition_key: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Execute a SQL query on a container.
    
    Args:
        container_name: Name of the container
        query: SQL query string
        parameters: Optional query parameters (e.g., [{"name": "@id", "value": 1}])
        partition_key: Optional partition key for single-partition queries (None = cross-partition)
    
    Returns:
        List of documents (dictionaries)
    
    Example:
        items = query_items(
            'businesses',
            'SELECT * FROM c WHERE c.business_id = @business_id',
            [{"name": "@business_id", "value": 1}],
            partition_key=None  # Cross-partition query
        )
    """
    container = get_container(container_name)
    
    items = container.query_items(
        query=query,
        parameters=parameters or [],
        enable_cross_partition_query=(partition_key is None)
    )
    
    return list(items)

def get_item(container_name: str, item_id: str, partition_key: str) -> Optional[Dict[str, Any]]:
    """Get a single item by ID and partition key."""
    try:
        container = get_container(container_name)
        return container.read_item(item=item_id, partition_key=partition_key)
    except exceptions.CosmosResourceNotFoundError:
        return None

def create_item(container_name: str, item: Dict[str, Any], partition_key: Optional[str] = None) -> Dict[str, Any]:
    """Create a new item in a container."""
    container = get_container(container_name)
    
    # If partition key not provided, try to extract from item
    if partition_key is None:
        # Try common partition key fields
        if 'business_id' in item:
            partition_key = str(item['business_id'])
        elif 'id' in item:
            partition_key = str(item['id'])
        else:
            raise ValueError("partition_key must be provided or item must have 'business_id' or 'id'")
    
    return container.create_item(body=item)

def update_item(container_name: str, item: Dict[str, Any], partition_key: Optional[str] = None) -> Dict[str, Any]:
    """Update an existing item."""
    container = get_container(container_name)
    
    if partition_key is None:
        if 'business_id' in item:
            partition_key = str(item['business_id'])
        elif 'id' in item:
            partition_key = str(item['id'])
        else:
            raise ValueError("partition_key must be provided")
    
    # Azure Cosmos DB SDK: replace_item requires item ID
    # The partition key is extracted from the item body based on the container's partition key path
    # Read the item first to get the _etag for optimistic concurrency
    # Read existing item to get _etag for optimistic concurrency
    # BUT: We must NOT overwrite our updated data with the existing item's data
    try:
        existing_item = container.read_item(item=item['id'], partition_key=partition_key)
        # ONLY copy _etag and _ts - these are needed for optimistic concurrency
        # DO NOT copy any other fields - we want to save our updated item, not the old one
        if '_etag' in existing_item:
            item['_etag'] = existing_item['_etag']
        if '_ts' in existing_item:
            item['_ts'] = existing_item['_ts']
        # CRITICAL: The 'item' parameter contains our updated data - don't overwrite it!
        # We're only reading existing_item to get the _etag for the replace operation
    except exceptions.CosmosResourceNotFoundError as e:
        # If item not found by id, try to find it by querying (in case id format is wrong)
        # This is a fallback for migrated data that might have different id formats
        if container_name == 'transactions' and 'transaction_id' in item:
            # Try to find transaction by transaction_id
            query_result = list(container.query_items(
                query='SELECT * FROM c WHERE c.type = @type AND c.transaction_id = @transaction_id AND c.business_id = @business_id',
                parameters=[
                    {"name": "@type", "value": "transaction"},
                    {"name": "@transaction_id", "value": item['transaction_id']},
                    {"name": "@business_id", "value": int(partition_key)}
                ],
                enable_cross_partition_query=False
            ))
            if query_result:
                existing_item = query_result[0]
                # Update the item's id to match what was found
                item['id'] = existing_item['id']
                if '_etag' in existing_item:
                    item['_etag'] = existing_item['_etag']
                if '_ts' in existing_item:
                    item['_ts'] = existing_item['_ts']
            else:
                raise ValueError(
                    f"Item {item.get('id', 'unknown')} not found in container '{container_name}' "
                    f"with partition key '{partition_key}'. "
                    f"Tried to find by transaction_id={item.get('transaction_id')} but it doesn't exist."
                ) from e
        elif container_name == 'chart_of_accounts' and 'account_id' in item:
            # Try to find chart of account by account_id
            query_result = list(container.query_items(
                query='SELECT * FROM c WHERE c.type = @type AND c.account_id = @account_id AND c.business_id = @business_id',
                parameters=[
                    {"name": "@type", "value": "chart_of_account"},
                    {"name": "@account_id", "value": item['account_id']},
                    {"name": "@business_id", "value": int(partition_key)}
                ],
                enable_cross_partition_query=False
            ))
            if query_result:
                existing_item = query_result[0]
                # Update the item's id to match what was found
                item['id'] = existing_item['id']
                if '_etag' in existing_item:
                    item['_etag'] = existing_item['_etag']
                if '_ts' in existing_item:
                    item['_ts'] = existing_item['_ts']
                print(f"DEBUG update_item: Found chart of account by account_id={item['account_id']}, using id={item['id']}")
            else:
                raise ValueError(
                    f"Item {item.get('id', 'unknown')} not found in container '{container_name}' "
                    f"with partition key '{partition_key}'. "
                    f"Tried to find by account_id={item.get('account_id')} but it doesn't exist."
                ) from e
        elif container_name == 'businesses' and 'business_id' in item:
            # Try to find business by business_id (cross-partition query)
            query_result = list(container.query_items(
                query='SELECT * FROM c WHERE c.type = @type AND c.business_id = @business_id',
                parameters=[
                    {"name": "@type", "value": "business"},
                    {"name": "@business_id", "value": item['business_id']}
                ],
                enable_cross_partition_query=True  # Businesses use /id as partition key, need cross-partition
            ))
            if query_result:
                existing_item = query_result[0]
                # Update the item's id to match what was found
                item['id'] = existing_item['id']
                if '_etag' in existing_item:
                    item['_etag'] = existing_item['_etag']
                if '_ts' in existing_item:
                    item['_ts'] = existing_item['_ts']
                print(f"DEBUG update_item: Found business by business_id={item['business_id']}, using id={item['id']}")
            else:
                raise ValueError(
                    f"Item {item.get('id', 'unknown')} not found in container '{container_name}'. "
                    f"Tried to find by business_id={item.get('business_id')} but it doesn't exist."
                ) from e
        else:
            raise ValueError(
                f"Item {item.get('id', 'unknown')} not found in container '{container_name}' "
                f"with partition key '{partition_key}'. "
                f"Make sure the item exists and the partition key is correct."
            ) from e
    
    # Replace the item - partition key is determined from the item's partition key field
    # In Azure Cosmos DB SDK v4, replace_item doesn't accept partition_key as a keyword argument
    # Create a clean copy of the item to ensure we're not passing any unwanted system fields
    clean_item = dict(item)
    # Remove Cosmos DB system fields that shouldn't be in the body (except _etag and _ts which are needed)
    for key in list(clean_item.keys()):
        if key.startswith('_') and key not in ['_etag', '_ts']:
            del clean_item[key]
    
    # Debug: Log what we're about to save (for transactions)
    if container_name == 'transactions' and 'lines' in clean_item:
        lines_debug = [(l.get('chart_of_account_id'), l.get('debit_amount'), l.get('credit_amount')) for l in clean_item.get('lines', [])]
        print(f"DEBUG update_item: About to replace transaction {clean_item.get('id')} with lines: {lines_debug}")
    
    result = container.replace_item(item=item['id'], body=clean_item)
    
    # Debug: Log what was saved (for transactions)
    if container_name == 'transactions' and 'lines' in result:
        saved_lines_debug = [(l.get('chart_of_account_id'), l.get('debit_amount'), l.get('credit_amount')) for l in result.get('lines', [])]
        print(f"DEBUG update_item: Saved transaction {result.get('id')} with lines: {saved_lines_debug}")
    
    return result

def delete_item(container_name: str, item_id: str, partition_key: str):
    """Delete an item."""
    container = get_container(container_name)
    container.delete_item(item=item_id, partition_key=partition_key)

# ========== ACCOUNTING-SPECIFIC QUERIES ==========

def get_businesses() -> List[Dict[str, Any]]:
    """Get all businesses."""
    businesses = query_items(
        'businesses',
        'SELECT c.business_id as id, c.name, c.created_at, c.updated_at FROM c WHERE c.type = "business"',
        partition_key=None  # Cross-partition query for all businesses
    )
    # Sort in Python to avoid composite index requirement
    businesses.sort(key=lambda x: x.get('name', ''))
    return businesses

def get_business(business_id: int) -> Optional[Dict[str, Any]]:
    """Get a specific business."""
    # Businesses container uses /id as partition key, and id is "business-{business_id}"
    # Query across partitions to find by business_id
    items = query_items(
        'businesses',
        'SELECT * FROM c WHERE c.type = "business" AND c.business_id = @business_id',
        [{"name": "@business_id", "value": business_id}],
        partition_key=None  # Cross-partition query (required since we're querying by business_id, not id)
    )
    return items[0] if items else None

def get_chart_of_accounts(business_id: int) -> List[Dict[str, Any]]:
    """Get chart of accounts for a business."""
    accounts = query_items(
        'chart_of_accounts',
        '''
        SELECT 
            c.account_id as id,
            c.account_code,
            c.account_name,
            c.description,
            c.parent_account_id,
            c.is_active,
            c.account_type
        FROM c 
        WHERE c.type = "chart_of_account" AND c.business_id = @business_id
        ''',
        [{"name": "@business_id", "value": business_id}],
        partition_key=str(business_id)
    )
    # Sort in Python to avoid composite index requirement
    accounts.sort(key=lambda x: x.get('account_code', ''))
    return accounts

def get_transactions(
    business_id: int,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    account_id: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Get transactions for a business with optional filters.
    
    Note: Filtering by account_id requires checking embedded lines,
    which is less efficient. Consider denormalizing account_id to transaction level.
    """
    try:
        query = '''
            SELECT * FROM c 
            WHERE c.type = "transaction" AND c.business_id = @business_id
        '''
        parameters = [{"name": "@business_id", "value": business_id}]
        
        if start_date:
            query += ' AND c.transaction_date >= @start_date'
            parameters.append({"name": "@start_date", "value": start_date})
        
        if end_date:
            query += ' AND c.transaction_date <= @end_date'
            parameters.append({"name": "@end_date", "value": end_date})
        
        # Note: Removed ORDER BY to avoid composite index requirement
        # We'll sort in Python instead
        
        transactions = query_items(
            'transactions',
            query,
            parameters,
            partition_key=str(business_id)  # Transactions partitioned by business_id
        )
        
        # Sort in Python: by transaction_date DESC, then transaction_id DESC
        transactions.sort(key=lambda x: (
            x.get('transaction_date', ''),
            x.get('transaction_id', 0) or x.get('id', 0)
        ), reverse=True)
        
        # Filter by account_id if specified (requires checking embedded lines)
        if account_id:
            filtered = []
            for txn in transactions:
                for line in txn.get('lines', []):
                    if line.get('chart_of_account_id') == account_id:
                        filtered.append(txn)
                        break
            return filtered
        
        return transactions
    except Exception as e:
        print(f"Error in get_transactions: {e}")
        import traceback
        traceback.print_exc()
        raise

def get_profit_loss_accounts(
    business_id: int,
    start_date: str,
    end_date: str
) -> List[Dict[str, Any]]:
    """
    Get revenue and expense accounts with balances for P&L report.
    
    This is a simplified version. The full implementation would need to:
    1. Query transactions in date range
    2. Aggregate transaction lines by account
    3. Calculate balances
    
    Note: Cosmos DB doesn't support complex JOINs like SQLite, so this
    requires a different approach - either:
    - Pre-aggregate balances in the account documents
    - Query transactions and aggregate in application code
    - Use a materialized view/aggregation pattern
    """
    # Get accounts
    accounts = get_chart_of_accounts(business_id)
    
    # Filter to revenue/expense
    revenue_expense_accounts = [
        acc for acc in accounts
        if acc.get('account_type', {}).get('category') in ('REVENUE', 'EXPENSE')
    ]
    
    # Get transactions in date range
    transactions = get_transactions(business_id, start_date, end_date)
    
    # Aggregate balances from transaction lines
    account_balances = {}
    for txn in transactions:
        for line in txn.get('lines', []):
            account_id = line.get('chart_of_account_id')
            if account_id:
                if account_id not in account_balances:
                    account_balances[account_id] = {
                        'debit_total': 0.0,
                        'credit_total': 0.0
                    }
                account_balances[account_id]['debit_total'] += float(line.get('debit_amount', 0))
                account_balances[account_id]['credit_total'] += float(line.get('credit_amount', 0))
    
    # Calculate balances and attach to accounts
    for acc in revenue_expense_accounts:
        account_id = acc['id']
        if account_id in account_balances:
            category = acc.get('account_type', {}).get('category', '')
            debit_total = account_balances[account_id]['debit_total']
            credit_total = account_balances[account_id]['credit_total']
            
            if category == 'REVENUE':
                balance = credit_total - debit_total
            else:  # EXPENSE
                balance = debit_total - credit_total
            
            acc['balance'] = balance
        else:
            acc['balance'] = 0.0
    
    # Filter out zero balances
    return [acc for acc in revenue_expense_accounts if abs(acc.get('balance', 0)) >= 0.01]

# ========== HELPER FUNCTIONS FOR CRUD OPERATIONS ==========

def get_next_id(container_name: str, id_field: str, partition_key: Optional[str] = None) -> int:
    """Get the next available ID for a container by finding max ID and adding 1."""
    try:
        items = query_items(
            container_name,
            f'SELECT VALUE MAX(c.{id_field}) FROM c',
            partition_key=partition_key
        )
        max_id = items[0] if items and items[0] is not None else 0
        return max_id + 1
    except Exception:
        # If query fails, return 1 as default
        return 1

def get_chart_of_account(account_id: int, business_id: int) -> Optional[Dict[str, Any]]:
    """Get a specific chart of account by account_id."""
    accounts = query_items(
        'chart_of_accounts',
        'SELECT * FROM c WHERE c.type = "chart_of_account" AND c.account_id = @account_id AND c.business_id = @business_id',
        [
            {"name": "@account_id", "value": account_id},
            {"name": "@business_id", "value": business_id}
        ],
        partition_key=str(business_id)
    )
    return accounts[0] if accounts else None

def get_transaction(transaction_id: int, business_id: int) -> Optional[Dict[str, Any]]:
    """Get a specific transaction by transaction_id."""
    transactions = query_items(
        'transactions',
        'SELECT * FROM c WHERE c.type = "transaction" AND c.transaction_id = @transaction_id AND c.business_id = @business_id',
        [
            {"name": "@transaction_id", "value": transaction_id},
            {"name": "@business_id", "value": business_id}
        ],
        partition_key=str(business_id)
    )
    if transactions:
        transaction = transactions[0]
        # Ensure id field is present - Cosmos DB SELECT * should include it, but ensure it's correct
        if 'id' not in transaction:
            # If id is missing, construct it from transaction_id
            transaction['id'] = f"transaction-{transaction.get('transaction_id') or transaction_id}"
        return transaction
    return None

# ========== INITIALIZATION ==========

def init_database():
    """
    Initialize Cosmos DB database and containers.
    
    This creates the database and containers if they don't exist.
    For production, you may want to manage containers via Azure Portal or Infrastructure as Code.
    """
    from azure.cosmos import PartitionKey
    
    database = get_database()
    
    containers_config = {
        'businesses': PartitionKey(path='/id'),
        'account_types': PartitionKey(path='/id'),
        'chart_of_accounts': PartitionKey(path='/business_id'),
        'bank_accounts': PartitionKey(path='/business_id'),
        'credit_card_accounts': PartitionKey(path='/business_id'),
        'loan_accounts': PartitionKey(path='/business_id'),
        'transactions': PartitionKey(path='/business_id'),
        'transaction_type_mappings': PartitionKey(path='/id')
    }
    
    for container_name, partition_key in containers_config.items():
        try:
            database.create_container_if_not_exists(
                id=container_name,
                partition_key=partition_key,
                offer_throughput=400  # 400 RUs per container
            )
        except Exception as e:
            print(f"Warning: Could not create container {container_name}: {e}")

if __name__ == '__main__':
    # Test connection
    print("Testing Cosmos DB connection...")
    try:
        init_database()
        businesses = get_businesses()
        print(f"✓ Connection successful! Found {len(businesses)} businesses.")
    except Exception as e:
        print(f"✗ Connection failed: {e}")

