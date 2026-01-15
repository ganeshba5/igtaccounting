#!/usr/bin/env python3
"""
Migration script to update transaction line chart_of_account_id values to UUID format.

This script:
1. Queries all transactions
2. For each transaction line, looks up the account by current chart_of_account_id
3. Updates chart_of_account_id to the account's UUID document ID
4. Updates the transaction document with the corrected lines

This fixes filtering issues by ensuring all transaction lines reference accounts using UUIDs.
"""

import os
import sys
import uuid
from typing import Dict, Any, List, Optional

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from database_cosmos import query_items, get_container, get_database, get_chart_of_account, update_item
from azure.cosmos import exceptions

def normalize_account_id_to_uuid(account_id: Any, business_id: int) -> Optional[str]:
    """
    Normalize an account ID (UUID, integer, or old format string) to UUID document ID.
    
    Returns the UUID document ID if found, None otherwise.
    """
    if not account_id:
        return None
    
    # Try to look up the account - get_chart_of_account handles all formats
    account = get_chart_of_account(account_id, business_id)
    if account:
        return account.get('id')  # Return UUID document ID
    return None

def migrate_transaction_lines_to_uuid():
    """Migrate transaction line chart_of_account_id values to UUID format."""
    
    print("Starting Transaction Lines chart_of_account_id migration to UUID format...")
    print("=" * 60)
    print("This will update all transaction line chart_of_account_id values to use")
    print("account UUID document IDs for consistent filtering and matching.")
    print("=" * 60)
    
    container = get_container('transactions')
    
    print("\nFetching all transactions...")
    
    # Query all transactions (cross-partition query)
    query = 'SELECT * FROM c WHERE c.type = "transaction"'
    transactions = list(container.query_items(
        query=query,
        parameters=[],
        enable_cross_partition_query=True
    ))
    
    print(f"Found {len(transactions)} total transactions")
    
    # Analyze which transactions need migration
    transactions_to_migrate = []
    total_lines_to_migrate = 0
    
    for txn in transactions:
        lines = txn.get('lines', [])
        if not lines:
            continue
        
        needs_migration = False
        lines_needing_update = []
        
        for line_idx, line in enumerate(lines):
            chart_of_account_id = line.get('chart_of_account_id')
            if not chart_of_account_id:
                continue
            
            # Check if it's already a UUID (36 chars with dashes)
            is_uuid = isinstance(chart_of_account_id, str) and len(chart_of_account_id) == 36 and chart_of_account_id.count('-') == 4
            try:
                if is_uuid:
                    uuid.UUID(chart_of_account_id)
                    # Already a UUID, skip this line
                    continue
            except (ValueError, TypeError):
                pass
            
            # Not a UUID, needs migration
            needs_migration = True
            lines_needing_update.append((line_idx, chart_of_account_id))
        
        if needs_migration:
            transactions_to_migrate.append({
                'transaction': txn,
                'lines_to_update': lines_needing_update
            })
            total_lines_to_migrate += len(lines_needing_update)
    
    print(f"\nFound {len(transactions_to_migrate)} transactions with {total_lines_to_migrate} lines needing migration")
    
    if not transactions_to_migrate:
        print("No transaction lines need migration. All chart_of_account_id values are already UUIDs.")
        return
    
    # Group by business_id for reporting
    by_business = {}
    for item in transactions_to_migrate:
        txn = item['transaction']
        business_id = txn.get('business_id')
        if business_id not in by_business:
            by_business[business_id] = []
        by_business[business_id].append(item)
    
    print(f"\nTransactions to migrate by business:")
    for business_id, items in by_business.items():
        line_count = sum(len(item['lines_to_update']) for item in items)
        print(f"  Business {business_id}: {len(items)} transactions, {line_count} lines")
    
    # Show sample of what will be migrated
    print(f"\nSample of lines to be migrated:")
    sample_count = 0
    for item in transactions_to_migrate[:5]:
        txn = item['transaction']
        txn_id = txn.get('transaction_id') or txn.get('id')
        for line_idx, old_id in item['lines_to_update'][:2]:
            print(f"  Transaction {txn_id}, Line {line_idx}: {old_id} -> (will look up UUID)")
            sample_count += 1
            if sample_count >= 5:
                break
        if sample_count >= 5:
            break
    
    # Confirm before proceeding
    print("\n" + "=" * 60)
    response = input(f"Proceed with migrating {total_lines_to_migrate} transaction lines in {len(transactions_to_migrate)} transactions? (yes/no): ")
    if response.lower() != 'yes':
        print("Migration cancelled.")
        return
    
    # Migrate each transaction
    migrated_count = 0
    error_count = 0
    errors = []
    lines_updated = 0
    
    print("\nMigrating transaction lines to UUID format...")
    print("=" * 60)
    
    for item in transactions_to_migrate:
        txn = item['transaction']
        txn_id = txn.get('transaction_id') or txn.get('id')
        business_id = txn.get('business_id')
        lines = txn.get('lines', [])
        lines_to_update = item['lines_to_update']
        
        if not business_id:
            error_msg = f"Transaction {txn_id}: missing business_id"
            print(f"ERROR: {error_msg}")
            errors.append(error_msg)
            error_count += 1
            continue
        
        try:
            # Update lines that need migration
            updated_lines = []
            lines_changed = False
            
            for line in lines:
                chart_of_account_id = line.get('chart_of_account_id')
                
                # Check if this line needs updating
                needs_update = False
                for line_idx, old_id in lines_to_update:
                    if line.get('chart_of_account_id') == old_id:
                        needs_update = True
                        break
                
                if needs_update and chart_of_account_id:
                    # Look up the account to get UUID
                    uuid_id = normalize_account_id_to_uuid(chart_of_account_id, business_id)
                    if uuid_id:
                        line['chart_of_account_id'] = uuid_id
                        lines_changed = True
                        lines_updated += 1
                        print(f"✓ Transaction {txn_id}, Line: {chart_of_account_id} -> {uuid_id}")
                    else:
                        error_msg = f"Transaction {txn_id}, Line: Could not find account for chart_of_account_id={chart_of_account_id}"
                        print(f"WARNING: {error_msg}")
                        errors.append(error_msg)
                        # Keep the original value if lookup fails
                
                updated_lines.append(line)
            
            if lines_changed:
                # Update the transaction document
                txn['lines'] = updated_lines
                
                # Get the document ID for update
                doc_id = txn.get('id')
                if not doc_id:
                    error_msg = f"Transaction {txn_id}: missing document id"
                    print(f"ERROR: {error_msg}")
                    errors.append(error_msg)
                    error_count += 1
                    continue
                
                # Update the transaction
                # update_item signature: update_item(container_name: str, item: Dict[str, Any], partition_key: Optional[Union[str, int]] = None)
                update_item(
                    'transactions',
                    txn,
                    partition_key=str(business_id)
                )
                
                migrated_count += 1
                print(f"✓ Updated transaction {txn_id} ({len([l for l in lines_to_update])} lines)")
            else:
                print(f"⚠ Transaction {txn_id}: No lines were updated (account lookups failed)")
                
        except exceptions.CosmosResourceNotFoundError:
            error_msg = f"Transaction {txn_id}: not found"
            print(f"WARNING: {error_msg}")
            errors.append(error_msg)
            error_count += 1
        except Exception as e:
            error_msg = f"Transaction {txn_id}: Error migrating - {str(e)}"
            print(f"ERROR: {error_msg}")
            errors.append(error_msg)
            error_count += 1
            import traceback
            traceback.print_exc()
    
    # Summary
    print("\n" + "=" * 60)
    print("Migration Summary:")
    print(f"  Total transactions processed: {len(transactions_to_migrate)}")
    print(f"  Successfully migrated: {migrated_count}")
    print(f"  Total lines updated: {lines_updated}")
    print(f"  Errors: {error_count}")
    
    if errors:
        print("\nErrors encountered:")
        for error in errors[:20]:  # Show first 20 errors
            print(f"  - {error}")
        if len(errors) > 20:
            print(f"  ... and {len(errors) - 20} more errors")
    
    print("\nMigration completed!")
    print("\nNote: After migration, all transaction lines should reference accounts by UUID.")
    print("This should fix filtering issues in P&L drill-down and Transaction filtering.")

if __name__ == '__main__':
    # Check if Cosmos DB is configured
    if not os.environ.get('COSMOS_ENDPOINT') or not os.environ.get('COSMOS_KEY'):
        print("ERROR: COSMOS_ENDPOINT and COSMOS_KEY environment variables must be set")
        sys.exit(1)
    
    try:
        migrate_transaction_lines_to_uuid()
    except Exception as e:
        print(f"\nFATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
