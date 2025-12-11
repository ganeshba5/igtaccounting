#!/usr/bin/env python3
"""
Verify the Cosmos DB migration by counting documents and showing sample data.
"""

import os
from azure.cosmos import CosmosClient

COSMOS_ENDPOINT = os.environ.get('COSMOS_ENDPOINT')
COSMOS_KEY = os.environ.get('COSMOS_KEY')
DATABASE_NAME = os.environ.get('DATABASE_NAME', 'accounting-db')

def main():
    if not COSMOS_ENDPOINT or not COSMOS_KEY:
        print("❌ Error: COSMOS_ENDPOINT and COSMOS_KEY must be set")
        return
    
    client = CosmosClient(COSMOS_ENDPOINT, COSMOS_KEY)
    database = client.get_database_client(DATABASE_NAME)
    
    containers = {
        'businesses': '/id',
        'account_types': '/id',
        'chart_of_accounts': '/business_id',
        'bank_accounts': '/business_id',
        'credit_card_accounts': '/business_id',
        'loan_accounts': '/business_id',
        'transactions': '/business_id',
        'transaction_type_mappings': '/id'
    }
    
    print("=" * 60)
    print("Cosmos DB Migration Verification")
    print("=" * 60)
    print()
    
    total_documents = 0
    for container_name, partition_key in containers.items():
        try:
            container = database.get_container_client(container_name)
            
            # Count documents
            query = "SELECT VALUE COUNT(1) FROM c"
            count_result = list(container.query_items(query=query, enable_cross_partition_query=True))
            count = count_result[0] if count_result else 0
            
            # Get sample document
            sample_query = "SELECT TOP 1 * FROM c"
            samples = list(container.query_items(query=sample_query, enable_cross_partition_query=True))
            sample = samples[0] if samples else None
            
            print(f"📦 {container_name:<30} Count: {count:>5}")
            if sample:
                doc_type = sample.get('type', 'unknown')
                print(f"   Sample document type: {doc_type}")
                if 'business_id' in sample:
                    print(f"   Business ID: {sample.get('business_id')}")
                elif 'business_id' in sample.get('business_id', ''):
                    pass
            
            total_documents += count
        except Exception as e:
            print(f"❌ Error checking {container_name}: {e}")
    
    print()
    print("=" * 60)
    print(f"Total documents migrated: {total_documents}")
    print("=" * 60)
    print()
    print("✅ Verification complete!")
    print()
    print("Next steps:")
    print("1. Review data in Azure Portal → Data Explorer")
    print("2. Test queries using database_cosmos.py functions")
    print("3. Update app.py to use Cosmos DB when ready")

if __name__ == '__main__':
    main()

