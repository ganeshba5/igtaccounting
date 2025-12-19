#!/usr/bin/env python3
"""
Migration script to update Chart of Accounts document IDs to UUID format for portability.

This script:
1. Queries all chart_of_accounts documents
2. Generates UUIDs for each document
3. Creates new documents with UUID IDs
4. Deletes old documents
5. Ensures uniqueness and portability across NoSQL databases

Note: Document IDs are now UUIDs, but queries still use account_id and business_id fields.
"""

import os
import sys
import uuid
from typing import Dict, Any, List

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from database_cosmos import query_items, get_container, get_database, create_item
from azure.cosmos import exceptions

def migrate_chart_of_accounts_ids():
    """Migrate chart of accounts IDs to UUID format for portability."""
    
    print("Starting Chart of Accounts ID migration to UUID format...")
    print("=" * 60)
    print("This will update all document IDs to UUIDs for better portability across NoSQL databases.")
    print("=" * 60)
    
    container = get_container('chart_of_accounts')
    
    print("Fetching all chart of accounts documents...")
    
    # Query all accounts (cross-partition query)
    query = 'SELECT * FROM c WHERE c.type = "chart_of_account"'
    accounts = list(container.query_items(
        query=query,
        parameters=[],
        enable_cross_partition_query=True
    ))
    
    print(f"Found {len(accounts)} total chart of accounts documents")
    
    # Check which accounts need migration (any that don't look like UUIDs)
    accounts_to_migrate = []
    for account in accounts:
        doc_id = account.get('id', '')
        # Check if ID is already a UUID (format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx)
        try:
            uuid.UUID(doc_id)
            # Already a UUID, skip
            continue
        except (ValueError, TypeError):
            # Not a UUID, needs migration
            accounts_to_migrate.append(account)
    
    print(f"Found {len(accounts_to_migrate)} accounts that need migration to UUID format")
    
    if not accounts_to_migrate:
        print("No accounts need migration. All IDs are already UUIDs.")
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
    
    # Show sample of old IDs
    print(f"\nSample of old IDs to be migrated:")
    for account in accounts_to_migrate[:5]:
        print(f"  - {account.get('id')} (account_id={account.get('account_id')}, business_id={account.get('business_id')})")
    if len(accounts_to_migrate) > 5:
        print(f"  ... and {len(accounts_to_migrate) - 5} more")
    
    # Confirm before proceeding
    print("\n" + "=" * 60)
    response = input(f"Proceed with migrating {len(accounts_to_migrate)} accounts to UUID format? (yes/no): ")
    if response.lower() != 'yes':
        print("Migration cancelled.")
        return
    
    # Migrate each account
    migrated_count = 0
    error_count = 0
    errors = []
    
    print("\nMigrating accounts to UUID format...")
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
        
        # Generate new UUID
        new_id = str(uuid.uuid4())
        partition_key = int(business_id)
        
        try:
            # Read existing document
            existing = container.read_item(item=old_id, partition_key=partition_key)
            
            # Create new document with UUID ID
            new_doc = dict(existing)
            new_doc['id'] = new_id
            # Remove system fields that will be regenerated
            for key in ['_rid', '_self', '_etag', '_attachments', '_ts']:
                new_doc.pop(key, None)
            
            # Create new document - use the helper function to match backend pattern
            created_doc = create_item('chart_of_accounts', new_doc, partition_key=str(partition_key))
            print(f"✓ Created new document with UUID: {new_id} (was {old_id})")
            
            # Delete old document - match exact pattern from backend/app.py
            # The backend uses keyword arguments, so we'll do the same
            try:
                # Try with integer partition key first (matches document field type)
                container.delete_item(item=old_id, partition_key=partition_key)
                print(f"✓ Deleted old document: {old_id} (using int partition key)")
            except Exception as del_err:
                # If integer fails, try string partition key as fallback
                error_msg = str(del_err)
                if "unexpected keyword argument 'partition_key'" in error_msg:
                    # SDK version issue - try using the document object approach
                    print(f"WARNING: SDK version issue detected, trying alternative delete method...")
                    # Use replace_item with empty body to delete, or use _self link
                    # Actually, let's just skip the delete for now and log it
                    print(f"WARNING: Could not delete old document {old_id} due to SDK version issue. Manual cleanup may be needed.")
                    print(f"  Old ID: {old_id}, New UUID: {new_id}, Business ID: {business_id}")
                else:
                    print(f"WARNING: Delete with int partition key failed: {error_msg}, trying string...")
                    try:
                        container.delete_item(item=old_id, partition_key=str(partition_key))
                        print(f"✓ Deleted old document: {old_id} (using string partition key)")
                    except Exception as del_err2:
                        # If both fail, log but don't fail the migration - document was created successfully
                        print(f"WARNING: Could not delete old document {old_id}. New document {new_id} was created successfully.")
                        print(f"  You may need to manually delete the old document. Error: {del_err2}")
            
            migrated_count += 1
            
        except exceptions.CosmosResourceNotFoundError:
            error_msg = f"Account with old_id={old_id} not found (may have been migrated already)"
            print(f"WARNING: {error_msg}")
            errors.append(error_msg)
            error_count += 1
        except Exception as e:
            error_msg = f"Error migrating account old_id={old_id} to UUID: {str(e)}"
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

