#!/usr/bin/env python3
"""
Check existing Cosmos DB containers and their throughput settings.
"""

import os
from azure.cosmos import CosmosClient, exceptions

COSMOS_ENDPOINT = os.environ.get('COSMOS_ENDPOINT')
COSMOS_KEY = os.environ.get('COSMOS_KEY')
DATABASE_NAME = os.environ.get('DATABASE_NAME', 'accounting-db')

def main():
    if not COSMOS_ENDPOINT or not COSMOS_KEY:
        print("❌ Error: COSMOS_ENDPOINT and COSMOS_KEY must be set")
        return
    
    client = CosmosClient(COSMOS_ENDPOINT, COSMOS_KEY)
    
    try:
        database = client.get_database_client(DATABASE_NAME)
        print(f"\n📊 Checking database: {DATABASE_NAME}\n")
        
        containers = list(database.list_containers())
        
        if not containers:
            print("✓ No containers exist yet")
            return
        
        total_throughput = 0
        print(f"{'Container Name':<30} {'Throughput':<15} {'Status'}")
        print("-" * 70)
        
        for container_props in containers:
            container_name = container_props['id']
            container = database.get_container_client(container_name)
            
            try:
                throughput = container.read_throughput()
                if throughput:
                    ru = throughput.get('content', {}).get('throughput', 'Unknown')
                    total_throughput += int(ru) if isinstance(ru, (int, str)) and str(ru).isdigit() else 0
                    status = f"{ru} RU/s" if ru else "Unknown"
                else:
                    status = "Serverless or Shared"
            except exceptions.CosmosHttpResponseError as e:
                if e.status_code == 400:
                    status = "Serverless or Shared"
                else:
                    status = f"Error: {e.status_code}"
            except Exception as e:
                status = f"Error: {str(e)[:30]}"
            
            print(f"{container_name:<30} {status:<15}")
        
        print("-" * 70)
        print(f"\n📈 Total Provisioned Throughput: {total_throughput} RU/s")
        print(f"📊 Account Limit: 1000 RU/s")
        print(f"💾 Remaining Capacity: {1000 - total_throughput} RU/s\n")
        
        if total_throughput > 1000:
            print("⚠️  WARNING: Total throughput exceeds account limit!")
            print("   You may need to delete some containers or reduce their throughput.")
        
    except exceptions.CosmosResourceNotFoundError:
        print(f"❌ Database '{DATABASE_NAME}' not found")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == '__main__':
    main()

