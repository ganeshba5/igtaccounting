#!/usr/bin/env python3
"""
Delete existing Cosmos DB containers to allow recreation with lower throughput.
Use with caution - this will delete all data in the containers!
"""

import os
import sys
from azure.cosmos import CosmosClient, exceptions

COSMOS_ENDPOINT = os.environ.get('COSMOS_ENDPOINT')
COSMOS_KEY = os.environ.get('COSMOS_KEY')
DATABASE_NAME = os.environ.get('DATABASE_NAME', 'accounting-db')

# Containers to delete (same as in migrate_to_cosmos.py)
CONTAINERS = [
    'businesses',
    'account_types',
    'chart_of_accounts',
    'bank_accounts',
    'credit_card_accounts',
    'loan_accounts',
    'transactions',
    'transaction_type_mappings'
]

def main():
    if not COSMOS_ENDPOINT or not COSMOS_KEY:
        print("❌ Error: COSMOS_ENDPOINT and COSMOS_KEY must be set")
        return
    
    print("⚠️  WARNING: This will DELETE all containers and their data!")
    print(f"   Containers to delete: {', '.join(CONTAINERS)}")
    response = input("\nType 'DELETE' to confirm: ")
    
    if response != 'DELETE':
        print("❌ Cancelled")
        return
    
    client = CosmosClient(COSMOS_ENDPOINT, COSMOS_KEY)
    
    try:
        database = client.get_database_client(DATABASE_NAME)
        print(f"\n🗑️  Deleting containers from database: {DATABASE_NAME}\n")
        
        deleted = []
        not_found = []
        errors = []
        
        for container_name in CONTAINERS:
            try:
                container = database.get_container_client(container_name)
                database.delete_container(container_name)
                deleted.append(container_name)
                print(f"✓ Deleted: {container_name}")
            except exceptions.CosmosResourceNotFoundError:
                not_found.append(container_name)
                print(f"⚠ Not found (already deleted): {container_name}")
            except Exception as e:
                errors.append((container_name, str(e)))
                print(f"❌ Error deleting {container_name}: {e}")
        
        print(f"\n📊 Summary:")
        print(f"   Deleted: {len(deleted)}")
        print(f"   Not found: {len(not_found)}")
        print(f"   Errors: {len(errors)}")
        
        if deleted:
            print(f"\n✅ Containers deleted. You can now run migration with lower throughput:")
            print(f"   export COSMOS_THROUGHPUT=50")
            print(f"   python migrate_to_cosmos.py")
        
    except exceptions.CosmosResourceNotFoundError:
        print(f"❌ Database '{DATABASE_NAME}' not found")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == '__main__':
    main()

