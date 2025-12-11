#!/usr/bin/env python3
"""
Proof-of-Concept: Migrate SQLite data to Azure Cosmos DB (SQL API)

This script:
1. Reads data from SQLite database
2. Transforms data to Cosmos DB document format
3. Creates containers if they don't exist
4. Imports data into Cosmos DB

Prerequisites:
    pip install azure-cosmos sqlite3

Environment Variables Required:
    COSMOS_ENDPOINT - Your Cosmos DB endpoint URL
    COSMOS_KEY - Your Cosmos DB primary key
    DATABASE_NAME - Name of the Cosmos DB database (default: 'accounting-db')
"""

import os
import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from azure.cosmos import CosmosClient, PartitionKey, exceptions
from azure.cosmos.database import DatabaseProxy
from azure.cosmos.container import ContainerProxy

# Configuration
COSMOS_ENDPOINT = os.environ.get('COSMOS_ENDPOINT')
COSMOS_KEY = os.environ.get('COSMOS_KEY')
DATABASE_NAME = os.environ.get('DATABASE_NAME', 'accounting-db')
SQLITE_DB_PATH = os.path.join(os.path.dirname(__file__), 'accounting.db')

# Container names and partition keys
CONTAINERS = {
    'businesses': '/id',
    'account_types': '/id',  # Small lookup table, single partition
    'chart_of_accounts': '/business_id',
    'bank_accounts': '/business_id',
    'credit_card_accounts': '/business_id',
    'loan_accounts': '/business_id',
    'transactions': '/business_id',  # Will embed transaction_lines
    'transaction_type_mappings': '/id'
}

def get_sqlite_connection():
    """Get SQLite database connection."""
    if not os.path.exists(SQLITE_DB_PATH):
        raise FileNotFoundError(f"SQLite database not found at {SQLITE_DB_PATH}")
    conn = sqlite3.connect(SQLITE_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_cosmos_client() -> CosmosClient:
    """Get Cosmos DB client."""
    if not COSMOS_ENDPOINT or not COSMOS_KEY:
        raise ValueError("COSMOS_ENDPOINT and COSMOS_KEY environment variables must be set")
    return CosmosClient(COSMOS_ENDPOINT, COSMOS_KEY)

def create_database_and_containers(client: CosmosClient, database_name: str) -> DatabaseProxy:
    """Create database and containers if they don't exist."""
    # Check if using shared throughput at database level (for free tier)
    use_shared_throughput = os.environ.get('COSMOS_SHARED_THROUGHPUT', 'false').lower() == 'true'
    shared_throughput = int(os.environ.get('COSMOS_SHARED_THROUGHPUT_VALUE', '400'))  # Default 400 RU/s
    
    # Create database with or without shared throughput
    try:
        if use_shared_throughput:
            database = client.create_database_if_not_exists(
                id=database_name,
                offer_throughput=shared_throughput
            )
            print(f"✓ Database '{database_name}' ready with SHARED throughput: {shared_throughput} RU/s")
            print(f"   All containers will share this throughput pool")
        else:
            database = client.create_database_if_not_exists(id=database_name)
            print(f"✓ Database '{database_name}' ready")
    except exceptions.CosmosResourceExistsError:
        database = client.get_database_client(database_name)
        print(f"✓ Database '{database_name}' already exists")
    
    # Check if using serverless mode (from environment variable)
    use_serverless = os.environ.get('COSMOS_SERVERLESS', 'false').lower() == 'true'
    
    # For per-container throughput (not shared)
    throughput_per_container = int(os.environ.get('COSMOS_THROUGHPUT', '400'))  # Default 400 RU/s (minimum)
    
    if use_shared_throughput:
        print(f"\n💡 Using SHARED throughput at database level: {shared_throughput} RU/s")
        print(f"   All {len(CONTAINERS)} containers will share this throughput")
        print(f"   This is required for free tier with multiple containers!")
    elif not use_serverless:
        total_throughput_needed = len(CONTAINERS) * throughput_per_container
        print(f"\n💡 Provisioned account detected. Using {throughput_per_container} RU/s per container")
        print(f"   Total throughput needed: {total_throughput_needed} RU/s")
        if total_throughput_needed > 1000:
            print(f"   ⚠ WARNING: This exceeds free tier limit (1000 RU/s)")
            print(f"   💡 SOLUTION: Use shared throughput instead:")
            print(f"      export COSMOS_SHARED_THROUGHPUT=true")
            print(f"      export COSMOS_SHARED_THROUGHPUT_VALUE=400")
            print(f"      python migrate_to_cosmos.py")
    
    # Create containers
    for container_name, partition_key in CONTAINERS.items():
        try:
            container_config = {
                'id': container_name,
                'partition_key': PartitionKey(path=partition_key)
            }
            
            # Only specify throughput if:
            # 1. Not using serverless mode
            # 2. Not using shared throughput (shared is at database level)
            if not use_serverless and not use_shared_throughput:
                container_config['offer_throughput'] = throughput_per_container
            
            container = database.create_container_if_not_exists(**container_config)
            
            if use_shared_throughput:
                mode = f"Shared ({shared_throughput} RU/s)"
            elif use_serverless:
                mode = "serverless"
            else:
                mode = f"{throughput_per_container} RU/s"
            
            print(f"✓ Container '{container_name}' ready (partition: {partition_key}, mode: {mode})")
        except exceptions.CosmosResourceExistsError:
            print(f"✓ Container '{container_name}' already exists")
        except exceptions.CosmosAccessConditionFailedError as e:
            print(f"✓ Container '{container_name}' already exists (may need configuration update)")
        except Exception as e:
            # Handle throughput errors
            if "throughput" in str(e).lower() or "RU/s" in str(e) or "BadRequest" in str(e):
                error_msg = str(e)
                if "minimum throughput" in error_msg.lower() or "400" in error_msg:
                    print(f"\n❌ Throughput error for '{container_name}':")
                    print(f"   Error: Minimum 400 RU/s required per container")
                    print(f"\n💡 SOLUTION for FREE TIER:")
                    print(f"   Use SHARED throughput at database level:")
                    print(f"   ")
                    print(f"   export COSMOS_SHARED_THROUGHPUT=true")
                    print(f"   export COSMOS_SHARED_THROUGHPUT_VALUE=400")
                    print(f"   python migrate_to_cosmos.py")
                    print(f"   ")
                    print(f"   This allows all containers to share 400 RU/s total!")
                else:
                    print(f"\n❌ Throughput limit error for '{container_name}':")
                    print(f"   Error: {str(e)[:200]}")
                raise
            else:
                print(f"❌ Error creating container '{container_name}': {e}")
                raise
    
    return database

def transform_business(row: sqlite3.Row) -> Dict[str, Any]:
    """Transform business row to Cosmos DB document."""
    row_dict = dict(row)  # Convert Row to dict to use .get()
    return {
        'id': f"business-{row_dict['id']}",
        'type': 'business',
        'business_id': row_dict['id'],
        'name': row_dict['name'],
        'created_at': row_dict.get('created_at'),
        'updated_at': row_dict.get('updated_at', row_dict.get('created_at'))
    }

def transform_account_type(row: sqlite3.Row) -> Dict[str, Any]:
    """Transform account_type row to Cosmos DB document."""
    row_dict = dict(row)  # Convert Row to dict to use .get()
    return {
        'id': f"account-type-{row_dict['id']}",
        'type': 'account_type',
        'account_type_id': row_dict['id'],
        'code': row_dict['code'],
        'name': row_dict['name'],
        'category': row_dict['category'],
        'normal_balance': row_dict['normal_balance'],
        'created_at': row_dict.get('created_at')
    }

def transform_chart_of_account(row: sqlite3.Row, account_type: Optional[Dict] = None) -> Dict[str, Any]:
    """Transform chart_of_accounts row to Cosmos DB document."""
    row_dict = dict(row)  # Convert Row to dict to use .get()
    doc = {
        'id': f"chart-{row_dict['id']}",
        'type': 'chart_of_account',
        'account_id': row_dict['id'],
        'business_id': row_dict['business_id'],
        'account_code': row_dict['account_code'],
        'account_name': row_dict['account_name'],
        'description': row_dict.get('description'),
        'parent_account_id': row_dict.get('parent_account_id'),
        'is_active': bool(row_dict.get('is_active', 1))
    }
    
    # Embed account type info for faster queries (denormalization)
    if account_type:
        doc['account_type'] = {
            'id': account_type['account_type_id'],
            'code': account_type['code'],
            'name': account_type['name'],
            'category': account_type['category'],
            'normal_balance': account_type['normal_balance']
        }
    else:
        doc['account_type_id'] = row_dict.get('account_type_id')
    
    return doc

def transform_bank_account(row: sqlite3.Row) -> Dict[str, Any]:
    """Transform bank_accounts row to Cosmos DB document."""
    row_dict = dict(row)  # Convert Row to dict to use .get()
    return {
        'id': f"bank-{row_dict['id']}",
        'type': 'bank_account',
        'bank_account_id': row_dict['id'],
        'business_id': row_dict['business_id'],
        'account_name': row_dict['account_name'],
        'account_number': row_dict.get('account_number'),
        'bank_name': row_dict.get('bank_name'),
        'routing_number': row_dict.get('routing_number'),
        'opening_balance': float(row_dict.get('opening_balance', 0) or 0),
        'current_balance': float(row_dict.get('current_balance', 0) or 0),
        'account_code': row_dict.get('account_code'),
        'is_active': bool(row_dict.get('is_active', 1)),
        'created_at': row_dict.get('created_at')
    }

def transform_credit_card_account(row: sqlite3.Row) -> Dict[str, Any]:
    """Transform credit_card_accounts row to Cosmos DB document."""
    row_dict = dict(row)  # Convert Row to dict to use .get()
    return {
        'id': f"credit-card-{row_dict['id']}",
        'type': 'credit_card_account',
        'credit_card_account_id': row_dict['id'],
        'business_id': row_dict['business_id'],
        'account_name': row_dict['account_name'],
        'card_number_last4': row_dict.get('card_number_last4'),
        'issuer': row_dict.get('issuer'),
        'credit_limit': float(row_dict.get('credit_limit', 0) or 0),
        'current_balance': float(row_dict.get('current_balance', 0) or 0),
        'account_code': row_dict.get('account_code'),
        'is_active': bool(row_dict.get('is_active', 1)),
        'created_at': row_dict.get('created_at')
    }

def transform_loan_account(row: sqlite3.Row) -> Dict[str, Any]:
    """Transform loan_accounts row to Cosmos DB document."""
    row_dict = dict(row)  # Convert Row to dict to use .get()
    return {
        'id': f"loan-{row_dict['id']}",
        'type': 'loan_account',
        'loan_account_id': row_dict['id'],
        'business_id': row_dict['business_id'],
        'account_name': row_dict['account_name'],
        'lender_name': row_dict.get('lender_name'),
        'loan_number': row_dict.get('loan_number'),
        'principal_amount': float(row_dict.get('principal_amount', 0) or 0),
        'current_balance': float(row_dict.get('current_balance', 0) or 0),
        'interest_rate': float(row_dict.get('interest_rate', 0) or 0),
        'account_code': row_dict.get('account_code'),
        'is_active': bool(row_dict.get('is_active', 1)),
        'created_at': row_dict.get('created_at')
    }

def transform_transaction(row: sqlite3.Row, lines: List[Dict]) -> Dict[str, Any]:
    """Transform transaction row to Cosmos DB document with embedded lines."""
    row_dict = dict(row)  # Convert Row to dict to use .get()
    
    # Embed transaction lines for atomicity
    transformed_lines = []
    for line in lines:
        line_dict = dict(line) if not isinstance(line, dict) else line
        transformed_lines.append({
            'id': f"line-{line_dict['id']}",
            'transaction_line_id': line_dict['id'],
            'chart_of_account_id': line_dict['chart_of_account_id'],
            'debit_amount': float(line_dict.get('debit_amount', 0) or 0),
            'credit_amount': float(line_dict.get('credit_amount', 0) or 0),
            'account_code': line_dict.get('account_code'),
            'account_name': line_dict.get('account_name')
        })
    
    return {
        'id': f"transaction-{row_dict['id']}",
        'type': 'transaction',
        'transaction_id': row_dict['id'],
        'business_id': row_dict['business_id'],
        'transaction_date': row_dict['transaction_date'],
        'description': row_dict.get('description'),
        'reference_number': row_dict.get('reference_number'),
        'transaction_type': row_dict.get('transaction_type'),
        'amount': float(row_dict.get('amount', 0) or 0),
        'account_id': row_dict.get('account_id'),
        'account_type': row_dict.get('account_type'),
        'chart_of_account_id': row_dict.get('chart_of_account_id'),
        'created_at': row_dict.get('created_at'),
        'lines': transformed_lines  # Embedded transaction lines
    }

def transform_transaction_type_mapping(row: sqlite3.Row) -> Dict[str, Any]:
    """Transform transaction_type_mappings row to Cosmos DB document."""
    row_dict = dict(row)  # Convert Row to dict to use .get()
    return {
        'id': f"mapping-{row_dict['id']}",
        'type': 'transaction_type_mapping',
        'mapping_id': row_dict['id'],
        'csv_type': row_dict['csv_type'],
        'internal_type': row_dict['internal_type'],
        'direction': row_dict['direction'],
        'description': row_dict.get('description'),
        'created_at': row_dict.get('created_at')
    }

def migrate_table(
    sqlite_conn: sqlite3.Connection,
    cosmos_container: ContainerProxy,
    table_name: str,
    transform_func,
    batch_size: int = 100
):
    """Migrate a table from SQLite to Cosmos DB."""
    print(f"\n📦 Migrating {table_name}...")
    
    # Get all rows
    cursor = sqlite_conn.cursor()
    cursor.execute(f'SELECT * FROM {table_name}')
    rows = cursor.fetchall()
    
    if not rows:
        print(f"  ⚠ No data in {table_name}")
        return
    
    # For chart_of_accounts, we need to join with account_types
    if table_name == 'chart_of_accounts':
        # Get account types for denormalization
        account_types = {}
        cursor.execute('SELECT * FROM account_types')
        for at_row in cursor.fetchall():
            at_dict = dict(at_row)  # Convert Row to dict
            account_types[at_dict['id']] = {
                'account_type_id': at_dict['id'],
                'code': at_dict['code'],
                'name': at_dict['name'],
                'category': at_dict['category'],
                'normal_balance': at_dict['normal_balance']
            }
        
        # Transform with account type info
        documents = []
        for row in rows:
            row_dict = dict(row)  # Convert Row to dict
            account_type = account_types.get(row_dict.get('account_type_id')) if row_dict.get('account_type_id') else None
            doc = transform_func(row, account_type)
            documents.append(doc)
    elif table_name == 'transactions':
        # For transactions, we need to embed transaction_lines
        documents = []
        for row in rows:
            row_dict = dict(row)  # Convert Row to dict
            # Get transaction lines for this transaction
            cursor.execute('''
                SELECT tl.*, coa.account_code, coa.account_name
                FROM transaction_lines tl
                LEFT JOIN chart_of_accounts coa ON tl.chart_of_account_id = coa.id
                WHERE tl.transaction_id = ?
            ''', (row_dict['id'],))
            lines = [dict(line) for line in cursor.fetchall()]
            doc = transform_func(row, lines)
            documents.append(doc)
    else:
        documents = [transform_func(row) for row in rows]
    
    # Insert in batches
    total = len(documents)
    inserted = 0
    errors = 0
    
    for i in range(0, total, batch_size):
        batch = documents[i:i + batch_size]
        for doc in batch:
            try:
                cosmos_container.create_item(body=doc)
                inserted += 1
            except exceptions.CosmosResourceExistsError:
                # Document already exists, update it
                try:
                    cosmos_container.replace_item(item=doc['id'], body=doc)
                    inserted += 1
                except Exception as e:
                    print(f"  ✗ Error updating {doc['id']}: {e}")
                    errors += 1
            except Exception as e:
                print(f"  ✗ Error inserting {doc['id']}: {e}")
                errors += 1
        
        if (i + batch_size) % (batch_size * 10) == 0:
            print(f"  Progress: {inserted}/{total} documents")
    
    print(f"  ✓ Migrated {inserted} documents ({errors} errors)")

def main():
    """Main migration function."""
    print("=" * 60)
    print("Azure Cosmos DB Migration - Proof of Concept")
    print("=" * 60)
    
    # Validate environment
    if not COSMOS_ENDPOINT or not COSMOS_KEY:
        print("\n❌ Error: COSMOS_ENDPOINT and COSMOS_KEY must be set")
        print("\nExample:")
        print("  export COSMOS_ENDPOINT='https://your-account.documents.azure.com:443/'")
        print("  export COSMOS_KEY='your-primary-key'")
        return
    
    # Check throughput configuration
    use_serverless = os.environ.get('COSMOS_SERVERLESS', 'false').lower() == 'true'
    use_shared = os.environ.get('COSMOS_SHARED_THROUGHPUT', 'false').lower() == 'true'
    throughput = os.environ.get('COSMOS_THROUGHPUT', '400')
    shared_throughput = os.environ.get('COSMOS_SHARED_THROUGHPUT_VALUE', '400')
    
    if use_serverless:
        print("\n💡 Using SERVERLESS mode (pay per request)")
        print("   ⚠ Note: This only works if your Cosmos DB account is configured as serverless")
        print("   If you get errors, your account is likely provisioned (not serverless)")
    elif use_shared:
        print(f"\n💡 Using SHARED throughput: {shared_throughput} RU/s at database level")
        print(f"   All {len(CONTAINERS)} containers will share this throughput")
        print(f"   ✅ This is the recommended approach for FREE TIER with multiple containers!")
    else:
        print(f"\n💡 Using PROVISIONED throughput: {throughput} RU/s per container")
        print(f"   With {len(CONTAINERS)} containers, total: {len(CONTAINERS) * int(throughput)} RU/s")
        print("\n   ⚠ WARNING: Minimum 400 RU/s per container required")
        print(f"   With {len(CONTAINERS)} containers × 400 RU/s = {len(CONTAINERS) * 400} RU/s needed")
        print("\n   💡 For FREE TIER (1000 RU/s limit), use SHARED throughput instead:")
        print("      export COSMOS_SHARED_THROUGHPUT=true")
        print("      export COSMOS_SHARED_THROUGHPUT_VALUE=400")
        print("      python migrate_to_cosmos.py")
    
    # Connect to SQLite
    print("\n📂 Connecting to SQLite...")
    try:
        sqlite_conn = get_sqlite_connection()
        print("✓ SQLite connection established")
    except Exception as e:
        print(f"❌ Error connecting to SQLite: {e}")
        return
    
    # Connect to Cosmos DB
    print("\n☁️  Connecting to Cosmos DB...")
    try:
        cosmos_client = get_cosmos_client()
        database = create_database_and_containers(cosmos_client, DATABASE_NAME)
        print("✓ Cosmos DB connection established")
    except Exception as e:
        print(f"❌ Error connecting to Cosmos DB: {e}")
        sqlite_conn.close()
        return
    
    # Migration order matters due to dependencies
    migration_order = [
        ('businesses', transform_business),
        ('account_types', transform_account_type),
        ('chart_of_accounts', transform_chart_of_account),
        ('bank_accounts', transform_bank_account),
        ('credit_card_accounts', transform_credit_card_account),
        ('loan_accounts', transform_loan_account),
        ('transaction_type_mappings', transform_transaction_type_mapping),
        ('transactions', transform_transaction),  # Last, depends on chart_of_accounts
    ]
    
    # Perform migration
    print("\n🚀 Starting migration...")
    for table_name, transform_func in migration_order:
        try:
            container = database.get_container_client(table_name)
            migrate_table(sqlite_conn, container, table_name, transform_func)
        except Exception as e:
            print(f"❌ Error migrating {table_name}: {e}")
    
    # Close connections
    sqlite_conn.close()
    
    print("\n" + "=" * 60)
    print("✅ Migration complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Review the migrated data in Azure Portal")
    print("2. Update your application to use database_cosmos.py")
    print("3. Test queries and verify data integrity")

if __name__ == '__main__':
    main()

