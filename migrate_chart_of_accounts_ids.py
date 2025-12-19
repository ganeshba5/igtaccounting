#!/usr/bin/env python3
"""
Migration script to update Chart of Accounts document IDs from old format (chart-{id}) 
to new format (account-{business_id}-{id}) for uniqueness across businesses.

This script:
1. Queries all chart_of_accounts documents
2. Finds documents with old ID format (chart-{id})
3. Updates them to new format (account-{business_id}-{id})
4. Uses replace_item to update the document ID
"""

import os
import sys
from typing import Dict, Any, List

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from database_cosmos import query_items, get_container, get_database
from azure.cosmos import exceptions

def migrate_chart_of_accounts_ids():
    """Migrate chart of accounts IDs from chart-{id} to account-{business_id}-{id} format."""
    
    print("Starting Chart of Accounts ID migration...")
    print("=" * 60)
    
    # Get all chart of accounts documents (cross-partition query)
    # We need to query all businesses to find documents with old format
    container = get_container('chart_of_accounts')
    
    all_accounts = []
    print("Fetching all chart of accounts documents...")
    
    # Query all businesses (we'll need to iterate through known business IDs)
    # For now, let's query cross-partition to find all accounts
    query = 'SELECT * FROM c WHERE c.type = "chart_of_account"'
    accounts = list(container.query_items(
        query=query,
        parameters=[],
        enable_cross_partition_query=True
    ))
    
    print(f"Found {len(accounts)} total chart of accounts documents")
    
    # Filter accounts with old format (chart-{id})
    accounts_to_migrate = []
    for account in accounts:
        doc_id = account.get('id', '')
        if doc_id.startswith('chart-'):
            accounts_to_migrate.append(account)
    
    print(f"Found {len(accounts_to_migrate)} accounts with old ID format (chart-*)")
    
    if not accounts_to_migrate:
        print("No accounts need migration. All IDs are already in the correct format.")
        return
    
    # Group by business_id for reporting
    by_business = {}
    for account in accounts_to_migrate:
        business_id = account.get('business_id')
        if business_id not in by_business:
            by_business[business_id] = []
        by_business[business_id].append(account)
    
    print(f"\nAccounts to migrate by business:")
    for business_id, accounts in by_business.items():
        print(f"  Business {business_id}: {len(accounts)} accounts")
    
    # Confirm before proceeding
    print("\n" + "=" * 60)
    response = input(f"Proceed with migrating {len(accounts_to_migrate)} accounts? (yes/no): ")
    if response.lower() != 'yes':
        print("Migration cancelled.")
        return
    
    # Migrate each account
    migrated_count = 0
    error_count = 0
    errors = []
    
    print("\nMigrating accounts...")
    print("=" * 60)
    
    for account in accounts_to_migrate:
        old_id = account.get('id')
        account_id = account.get('account_id')
        business_id = account.get('business_id')
        
        if not account_id or not business_id:
            error_msg = f"Skipping account with old_id={old_id}: missing account_id or business_id"
            print(f"ERROR: {error_msg}")
            errors.append(error_msg)
            error_count += 1
            continue
        
        new_id = f'account-{business_id}-{account_id}'
        
        try:
            # Update the account document with new ID
            account['id'] = new_id
            partition_key = int(business_id)
            
            # Use replace_item - but first we need to read the existing document to get _etag
            # Then create with new ID and delete old one
            # Actually, in Cosmos DB we can't change the ID of a document directly
            # We need to create a new document with the new ID and delete the old one
            
            # Read existing document
            existing = container.read_item(item=old_id, partition_key=partition_key)
            
            # Create new document with new ID
            new_doc = dict(existing)
            new_doc['id'] = new_id
            # Remove system fields that will be regenerated
            for key in ['_rid', '_self', '_etag', '_attachments', '_ts']:
                new_doc.pop(key, None)
            
            # Create new document
            container.create_item(body=new_doc, partition_key=partition_key)
            print(f"✓ Created new document: {new_id} (was {old_id})")
            
            # Delete old document
            container.delete_item(item=old_id, partition_key=partition_key)
            print(f"✓ Deleted old document: {old_id}")
            
            migrated_count += 1
            
        except exceptions.CosmosResourceNotFoundError:
            error_msg = f"Account with old_id={old_id} not found (may have been migrated already)"
            print(f"WARNING: {error_msg}")
            errors.append(error_msg)
            error_count += 1
        except Exception as e:
            error_msg = f"Error migrating account old_id={old_id} to new_id={new_id}: {str(e)}"
            print(f"ERROR: {error_msg}")
            errors.append(error_msg)
            error_count += 1
    
    # Summary
    print("\n" + "=" * 60)
    print("Migration Summary:")
    print(f"  Total accounts processed: {len(accounts_to_migrate)}")
    print(f"  Successfully migrated: {migrated_count}")
    print(f"  Errors: {error_count}")
    
    if errors:
        print("\nErrors encountered:")
        for error in errors[:10]:  # Show first 10 errors
            print(f"  - {error}")
        if len(errors) > 10:
            print(f"  ... and {len(errors) - 10} more errors")
    
    print("\nMigration completed!")

if __name__ == '__main__':
    # Check if Cosmos DB is configured
    if not os.environ.get('COSMOS_ENDPOINT') or not os.environ.get('COSMOS_KEY'):
        print("ERROR: COSMOS_ENDPOINT and COSMOS_KEY environment variables must be set")
        sys.exit(1)
    
    try:
        migrate_chart_of_accounts_ids()
    except Exception as e:
        print(f"\nFATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

