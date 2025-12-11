#!/usr/bin/env python3
"""
Script to fix incorrectly imported transactions where both lines use the same account.
This fixes transactions where expense/revenue accounts appear on both sides instead of
having the bank account on one side.
"""

import sqlite3
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))
from database import get_db_connection

def fix_transactions(business_id=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Find transactions where both lines have the same chart_of_account_id
    if business_id:
        query = '''
            SELECT t.id, t.business_id, t.transaction_date, t.transaction_type,
                   tl1.chart_of_account_id as account_id,
                   tl1.debit_amount as debit1, tl1.credit_amount as credit1,
                   tl2.debit_amount as debit2, tl2.credit_amount as credit2
            FROM transactions t
            JOIN transaction_lines tl1 ON t.id = tl1.transaction_id
            JOIN transaction_lines tl2 ON t.id = tl2.transaction_id
            WHERE t.business_id = ?
            AND tl1.chart_of_account_id = tl2.chart_of_account_id
            AND tl1.id < tl2.id
            ORDER BY t.id
        '''
        problematic_transactions = cursor.execute(query, (business_id,)).fetchall()
        print(f"Fixing transactions for business_id={business_id}")
    else:
        query = '''
            SELECT t.id, t.business_id, t.transaction_date, t.transaction_type,
                   tl1.chart_of_account_id as account_id,
                   tl1.debit_amount as debit1, tl1.credit_amount as credit1,
                   tl2.debit_amount as debit2, tl2.credit_amount as credit2
            FROM transactions t
            JOIN transaction_lines tl1 ON t.id = tl1.transaction_id
            JOIN transaction_lines tl2 ON t.id = tl2.transaction_id
            WHERE tl1.chart_of_account_id = tl2.chart_of_account_id
            AND tl1.id < tl2.id
            ORDER BY t.id
        '''
        problematic_transactions = cursor.execute(query).fetchall()
        print("Fixing transactions for all businesses")
    
    print(f"Found {len(problematic_transactions)} problematic transactions")
    
    fixed_count = 0
    for txn in problematic_transactions:
        txn_id = txn['id']
        business_id = txn['business_id']
        account_id = txn['account_id']
        
        # Get the account to determine if it's expense or revenue
        account = cursor.execute('''
            SELECT coa.*, at.category
            FROM chart_of_accounts coa
            JOIN account_types at ON coa.account_type_id = at.id
            WHERE coa.id = ?
        ''', (account_id,)).fetchone()
        
        if not account:
            continue
        
        # Get the bank account chart account for this business
        # Try to find bank account by matching with bank_accounts table first
        bank_chart_account = cursor.execute('''
            SELECT coa.id, coa.account_code
            FROM bank_accounts ba
            JOIN chart_of_accounts coa ON ba.business_id = coa.business_id
            JOIN account_types at ON coa.account_type_id = at.id
            WHERE ba.business_id = ?
            AND at.category = 'ASSET'
            AND (coa.account_code = ba.account_code OR coa.account_code LIKE 'BANK%' OR coa.account_name LIKE '%Bank%')
            LIMIT 1
        ''', (business_id,)).fetchone()
        
        # If not found, try just by account code pattern
        if not bank_chart_account:
            bank_chart_account = cursor.execute('''
                SELECT coa.id, coa.account_code
                FROM chart_of_accounts coa
                JOIN account_types at ON coa.account_type_id = at.id
                WHERE coa.business_id = ?
                AND at.category = 'ASSET'
                AND (coa.account_code LIKE 'BANK%' OR coa.account_name LIKE '%Bank%')
                LIMIT 1
            ''', (business_id,)).fetchone()
        
        if not bank_chart_account:
            print(f"Transaction {txn_id}: No bank account found, skipping")
            continue
        
        bank_account_id = bank_chart_account['id']
        account_category = account['category']
        
        # Get transaction type to determine direction
        transaction_type = txn['transaction_type']
        is_debit = transaction_type in ('WITHDRAWAL', 'PAYMENT', 'CHARGE', 'EXPENSE')
        
        # Get both lines for this transaction with the same account
        lines = cursor.execute('''
            SELECT id, debit_amount, credit_amount
            FROM transaction_lines
            WHERE transaction_id = ? AND chart_of_account_id = ?
            ORDER BY id
        ''', (txn_id, account_id)).fetchall()
        
        if len(lines) != 2:
            print(f"Transaction {txn_id}: Expected 2 lines, found {len(lines)}, skipping")
            continue
        
        line1 = dict(lines[0])
        line2 = dict(lines[1])
        
        # Determine which line should be changed based on account category
        if account_category == 'EXPENSE':
            # Expense transaction should be: Debit expense, Credit bank
            # Line 1 has debit (correct), Line 2 has credit (should be bank account)
            if line1['debit_amount'] > 0 and line2['credit_amount'] > 0:
                cursor.execute('''
                    UPDATE transaction_lines
                    SET chart_of_account_id = ?
                    WHERE id = ?
                ''', (bank_account_id, line2['id']))
                print(f"Transaction {txn_id}: Changed credit line (id={line2['id']}) from expense account to bank account")
            else:
                print(f"Transaction {txn_id}: Unexpected line structure, skipping")
                continue
                
        elif account_category == 'REVENUE':
            # Revenue transaction should be: Debit bank, Credit revenue
            # Line 1 has debit (should be bank), Line 2 has credit (correct)
            if line1['debit_amount'] > 0 and line2['credit_amount'] > 0:
                cursor.execute('''
                    UPDATE transaction_lines
                    SET chart_of_account_id = ?
                    WHERE id = ?
                ''', (bank_account_id, line1['id']))
                print(f"Transaction {txn_id}: Changed debit line (id={line1['id']}) from revenue account to bank account")
            else:
                print(f"Transaction {txn_id}: Unexpected line structure, skipping")
                continue
        
        fixed_count += 1
        print(f"Fixed transaction {txn_id}: Changed second line to bank account {bank_account_id}")
    
    conn.commit()
    conn.close()
    
    print(f"\nFixed {fixed_count} transactions")

if __name__ == '__main__':
    import sys
    business_id = None
    if len(sys.argv) > 1:
        try:
            business_id = int(sys.argv[1])
        except ValueError:
            print(f"Invalid business_id: {sys.argv[1]}. Usage: python fix_transactions.py [business_id]")
            sys.exit(1)
    fix_transactions(business_id)

