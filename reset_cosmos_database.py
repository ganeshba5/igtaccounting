#!/usr/bin/env python3
"""
Delete the entire Cosmos DB database to start fresh.
This will delete ALL data in the database!

Use this when you need to recreate with different throughput settings.
"""

import os
import sys
from azure.cosmos import CosmosClient, exceptions

COSMOS_ENDPOINT = os.environ.get('COSMOS_ENDPOINT')
COSMOS_KEY = os.environ.get('COSMOS_KEY')
DATABASE_NAME = os.environ.get('DATABASE_NAME', 'accounting-db')

def main():
    if not COSMOS_ENDPOINT or not COSMOS_KEY:
        print("❌ Error: COSMOS_ENDPOINT and COSMOS_KEY must be set")
        return
    
    print("⚠️  WARNING: This will DELETE the entire database and ALL its data!")
    print(f"   Database to delete: {DATABASE_NAME}")
    response = input("\nType 'DELETE DATABASE' to confirm: ")
    
    if response != 'DELETE DATABASE':
        print("❌ Cancelled")
        return
    
    client = CosmosClient(COSMOS_ENDPOINT, COSMOS_KEY)
    
    try:
        database = client.get_database_client(DATABASE_NAME)
        
        # List containers first
        print(f"\n📋 Containers in database '{DATABASE_NAME}':")
        try:
            containers = list(database.list_containers())
            if containers:
                for container in containers:
                    print(f"   - {container['id']}")
            else:
                print("   (none)")
        except Exception as e:
            print(f"   Error listing containers: {e}")
        
        # Delete database (this will delete all containers and data)
        print(f"\n🗑️  Deleting database '{DATABASE_NAME}'...")
        try:
            client.delete_database(database_name=DATABASE_NAME)
            print(f"✅ Database '{DATABASE_NAME}' deleted successfully!")
            print(f"\n💡 You can now run migration with fresh settings:")
            print(f"   export COSMOS_SHARED_THROUGHPUT=true")
            print(f"   export COSMOS_SHARED_THROUGHPUT_VALUE=400")
            print(f"   python migrate_to_cosmos.py")
        except exceptions.CosmosResourceNotFoundError:
            print(f"⚠️  Database '{DATABASE_NAME}' doesn't exist")
        except Exception as e:
            print(f"❌ Error deleting database: {e}")
            print(f"\n💡 Try deleting from Azure Portal manually:")
            print(f"   1. Go to Azure Portal → Cosmos DB account")
            print(f"   2. Data Explorer → Select database → Delete")
        
    except exceptions.CosmosResourceNotFoundError:
        print(f"⚠️  Database '{DATABASE_NAME}' doesn't exist")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == '__main__':
    main()

