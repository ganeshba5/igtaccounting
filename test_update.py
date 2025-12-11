#!/usr/bin/env python3
"""
Simple test script to verify that Cosmos DB update_item works correctly.
This tests updating a single transaction line directly.

Run with: source venv/bin/activate && python3 test_update.py
Or: venv/bin/python3 test_update.py
"""

import os
import sys

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.database_cosmos import get_transaction, update_item

# Set up environment
os.environ.setdefault('COSMOS_ENDPOINT', os.getenv('COSMOS_ENDPOINT', ''))
os.environ.setdefault('COSMOS_KEY', os.getenv('COSMOS_KEY', ''))
os.environ.setdefault('COSMOS_DATABASE', os.getenv('COSMOS_DATABASE', 'accounting-db'))

def test_update_transaction_line():
    """Test updating a single transaction line."""
    business_id = 2
    transaction_id = 1301
    
    print(f"Testing update for transaction {transaction_id} in business {business_id}...")
    
    # Get the transaction
    print("\n1. Fetching transaction...")
    transaction = get_transaction(transaction_id, business_id)
    if not transaction:
        print(f"❌ Transaction {transaction_id} not found")
        return False
    
    print(f"✓ Transaction found: {transaction.get('id')}")
    print(f"  Lines before update:")
    for idx, line in enumerate(transaction.get('lines', [])):
        print(f"    Line {idx}: account_id={line.get('chart_of_account_id')}, "
              f"debit={line.get('debit_amount')}, credit={line.get('credit_amount')}")
    
    # Update the second line (index 1) to a test account
    lines = transaction.get('lines', [])
    if len(lines) < 2:
        print("❌ Transaction doesn't have 2 lines")
        return False
    
    # Store original value
    original_account_id = lines[1].get('chart_of_account_id')
    print(f"\n2. Original account_id for line 1: {original_account_id}")
    
    # Update line 1 to a different account (let's use 131, same as line 0 for testing)
    # Note: This would create duplicate accounts, but it's just a test
    updated_lines = []
    for idx, line in enumerate(lines):
        updated_line = dict(line)
        if idx == 1:
            updated_line['chart_of_account_id'] = 131  # Test account
            print(f"  Updating line {idx} to account_id: 131")
        updated_lines.append(updated_line)
    
    transaction['lines'] = updated_lines
    
    # Update in Cosmos DB
    print("\n3. Updating transaction in Cosmos DB...")
    try:
        result = update_item(
            'transactions',
            transaction,
            partition_key=str(business_id)
        )
        print("✓ Update successful")
        print(f"  Result lines:")
        for idx, line in enumerate(result.get('lines', [])):
            print(f"    Line {idx}: account_id={line.get('chart_of_account_id')}, "
                  f"debit={line.get('debit_amount')}, credit={line.get('credit_amount')}")
    except Exception as e:
        print(f"❌ Update failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Fetch again to verify
    print("\n4. Fetching transaction again to verify...")
    transaction_after = get_transaction(transaction_id, business_id)
    if not transaction_after:
        print("❌ Transaction not found after update")
        return False
    
    print(f"✓ Transaction fetched")
    print(f"  Lines after update:")
    for idx, line in enumerate(transaction_after.get('lines', [])):
        print(f"    Line {idx}: account_id={line.get('chart_of_account_id')}, "
              f"debit={line.get('debit_amount')}, credit={line.get('credit_amount')}")
    
    # Verify the update
    line_1_account = transaction_after.get('lines', [])[1].get('chart_of_account_id')
    if line_1_account == 131:
        print("\n✅ SUCCESS: Line 1 was updated correctly")
        
        # Restore original value
        print("\n5. Restoring original value...")
        lines_restore = []
        for idx, line in enumerate(transaction_after.get('lines', [])):
            restored_line = dict(line)
            if idx == 1:
                restored_line['chart_of_account_id'] = original_account_id
                print(f"  Restoring line {idx} to account_id: {original_account_id}")
            lines_restore.append(restored_line)
        
        transaction_after['lines'] = lines_restore
        update_item('transactions', transaction_after, partition_key=str(business_id))
        print("✓ Original value restored")
        
        return True
    else:
        print(f"\n❌ FAILED: Line 1 account_id is {line_1_account}, expected 131")
        return False

if __name__ == '__main__':
    # Check for environment variables
    cosmos_endpoint = os.getenv('COSMOS_ENDPOINT')
    cosmos_key = os.getenv('COSMOS_KEY')
    
    if not cosmos_endpoint or not cosmos_key:
        print("❌ Error: COSMOS_ENDPOINT and COSMOS_KEY environment variables must be set")
        print("\nPlease set them:")
        print("  export COSMOS_ENDPOINT='https://your-account.documents.azure.com:443/'")
        print("  export COSMOS_KEY='your-primary-key'")
        print("\nOr run: source venv/bin/activate && export COSMOS_ENDPOINT=... && export COSMOS_KEY=... && python3 test_update.py")
        sys.exit(1)
    
    success = test_update_transaction_line()
    sys.exit(0 if success else 1)

