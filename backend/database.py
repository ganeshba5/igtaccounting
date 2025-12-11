"""
Database initialization and schema for the accounting application.
"""
import sqlite3
import os
from datetime import datetime
from typing import Optional

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'accounting.db')

def get_db_connection():
    """Get a database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    """Initialize the database with all required tables."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Businesses table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS businesses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Chart of Accounts - Account types/categories
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS account_types (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            normal_balance TEXT NOT NULL CHECK(normal_balance IN ('DEBIT', 'CREDIT')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Chart of Accounts - Business specific accounts
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chart_of_accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            business_id INTEGER NOT NULL,
            account_type_id INTEGER,
            account_code TEXT NOT NULL,
            account_name TEXT NOT NULL,
            description TEXT,
            parent_account_id INTEGER,
            is_active BOOLEAN DEFAULT 1,
            FOREIGN KEY (business_id) REFERENCES businesses(id) ON DELETE CASCADE,
            FOREIGN KEY (account_type_id) REFERENCES account_types(id),
            FOREIGN KEY (parent_account_id) REFERENCES chart_of_accounts(id),
            UNIQUE(business_id, account_code)
        )
    ''')
    
    # Bank Accounts
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bank_accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            business_id INTEGER NOT NULL,
            account_name TEXT NOT NULL,
            account_number TEXT,
            bank_name TEXT,
            routing_number TEXT,
            opening_balance REAL DEFAULT 0,
            current_balance REAL DEFAULT 0,
            account_code TEXT,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (business_id) REFERENCES businesses(id) ON DELETE CASCADE
        )
    ''')
    
    # Credit Card Accounts
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS credit_card_accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            business_id INTEGER NOT NULL,
            account_name TEXT NOT NULL,
            card_number_last4 TEXT,
            issuer TEXT,
            credit_limit REAL DEFAULT 0,
            current_balance REAL DEFAULT 0,
            account_code TEXT,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (business_id) REFERENCES businesses(id) ON DELETE CASCADE
        )
    ''')
    
    # Loan Accounts
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS loan_accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            business_id INTEGER NOT NULL,
            account_name TEXT NOT NULL,
            lender_name TEXT,
            loan_number TEXT,
            principal_amount REAL DEFAULT 0,
            current_balance REAL DEFAULT 0,
            interest_rate REAL DEFAULT 0,
            account_code TEXT,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (business_id) REFERENCES businesses(id) ON DELETE CASCADE
        )
    ''')
    
    # Transactions
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            business_id INTEGER NOT NULL,
            transaction_date DATE NOT NULL,
            description TEXT,
            reference_number TEXT,
            transaction_type TEXT CHECK(transaction_type IN ('DEPOSIT', 'WITHDRAWAL', 'TRANSFER', 'PAYMENT', 'CHARGE', 'PAYMENT_RECEIVED', 'EXPENSE', 'INCOME', 'ADJUSTMENT')),
            amount REAL NOT NULL,
            account_id INTEGER,
            account_type TEXT CHECK(account_type IN ('BANK', 'CREDIT_CARD', 'LOAN', 'CHART_OF_ACCOUNTS')),
            chart_of_account_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (business_id) REFERENCES businesses(id) ON DELETE CASCADE,
            FOREIGN KEY (chart_of_account_id) REFERENCES chart_of_accounts(id)
        )
    ''')
    
    # Transaction Lines (Double-entry accounting)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transaction_lines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_id INTEGER NOT NULL,
            chart_of_account_id INTEGER NOT NULL,
            debit_amount REAL DEFAULT 0,
            credit_amount REAL DEFAULT 0,
            FOREIGN KEY (transaction_id) REFERENCES transactions(id) ON DELETE CASCADE,
            FOREIGN KEY (chart_of_account_id) REFERENCES chart_of_accounts(id)
        )
    ''')
    
    # Transaction Type Mappings - Maps CSV transaction types to internal types
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transaction_type_mappings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            csv_type TEXT NOT NULL UNIQUE,
            internal_type TEXT NOT NULL CHECK(internal_type IN ('DEPOSIT', 'WITHDRAWAL', 'TRANSFER', 'PAYMENT', 'CHARGE', 'PAYMENT_RECEIVED', 'EXPENSE', 'INCOME', 'ADJUSTMENT')),
            direction TEXT NOT NULL CHECK(direction IN ('DEBIT', 'CREDIT')),
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Insert default transaction type mappings
    default_mappings = [
        ('DEBIT', 'WITHDRAWAL', 'DEBIT', 'Debit transaction'),
        ('CREDIT', 'DEPOSIT', 'CREDIT', 'Credit transaction'),
        ('WITHDRAWAL', 'WITHDRAWAL', 'DEBIT', 'Withdrawal'),
        ('DEPOSIT', 'DEPOSIT', 'CREDIT', 'Deposit'),
        ('CHARGE', 'CHARGE', 'DEBIT', 'Charge'),
        ('PAYMENT', 'PAYMENT', 'DEBIT', 'Payment'),
        ('PAYMENT_RECEIVED', 'PAYMENT_RECEIVED', 'CREDIT', 'Payment received'),
        ('ACH_CREDIT', 'DEPOSIT', 'CREDIT', 'ACH credit transfer'),
        ('ACH_DEBIT', 'WITHDRAWAL', 'DEBIT', 'ACH debit transfer'),
        ('DEBIT_CARD', 'CHARGE', 'DEBIT', 'Debit card transaction'),
        ('CREDIT_CARD', 'CHARGE', 'DEBIT', 'Credit card charge'),
        ('FEE_TRANSACTION', 'EXPENSE', 'DEBIT', 'Fee transaction'),
        ('FEE', 'EXPENSE', 'DEBIT', 'Fee'),
        ('TRANSFER_IN', 'DEPOSIT', 'CREDIT', 'Transfer in'),
        ('TRANSFER_OUT', 'WITHDRAWAL', 'DEBIT', 'Transfer out'),
        ('CHECK', 'PAYMENT', 'DEBIT', 'Check payment'),
        ('WIRE_TRANSFER', 'TRANSFER', 'DEBIT', 'Wire transfer'),
        ('INTEREST', 'INCOME', 'CREDIT', 'Interest income'),
        ('DIVIDEND', 'INCOME', 'CREDIT', 'Dividend income'),
    ]
    
    cursor.executemany('''
        INSERT OR IGNORE INTO transaction_type_mappings (csv_type, internal_type, direction, description)
        VALUES (?, ?, ?, ?)
    ''', default_mappings)
    
    # Create indexes for better performance
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_business_date ON transactions(business_id, transaction_date)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_chart_of_accounts_business ON chart_of_accounts(business_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_transaction_lines_transaction ON transaction_lines(transaction_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_transaction_type_mappings_csv_type ON transaction_type_mappings(csv_type)')
    
    # Insert default account types
    default_account_types = [
        ('ASSET', 'Assets', 'ASSET', 'DEBIT'),
        ('CASH', 'Cash', 'ASSET', 'DEBIT'),
        ('BANK', 'Bank Accounts', 'ASSET', 'DEBIT'),
        ('ACCOUNTS_RECEIVABLE', 'Accounts Receivable', 'ASSET', 'DEBIT'),
        ('INVENTORY', 'Inventory', 'ASSET', 'DEBIT'),
        ('FIXED_ASSET', 'Fixed Assets', 'ASSET', 'DEBIT'),
        ('LIABILITY', 'Liabilities', 'LIABILITY', 'CREDIT'),
        ('ACCOUNTS_PAYABLE', 'Accounts Payable', 'LIABILITY', 'CREDIT'),
        ('CREDIT_CARD', 'Credit Cards', 'LIABILITY', 'CREDIT'),
        ('LOAN', 'Loans', 'LIABILITY', 'CREDIT'),
        ('EQUITY', 'Equity', 'EQUITY', 'CREDIT'),
        ('CAPITAL', 'Capital', 'EQUITY', 'CREDIT'),
        ('RETAINED_EARNINGS', 'Retained Earnings', 'EQUITY', 'CREDIT'),
        ('REVENUE', 'Revenue', 'REVENUE', 'CREDIT'),
        ('SALES', 'Sales', 'REVENUE', 'CREDIT'),
        ('SERVICE_REVENUE', 'Service Revenue', 'REVENUE', 'CREDIT'),
        ('EXPENSE', 'Expenses', 'EXPENSE', 'DEBIT'),
        ('COST_OF_GOODS_SOLD', 'Cost of Goods Sold', 'EXPENSE', 'DEBIT'),
        ('OPERATING_EXPENSE', 'Operating Expenses', 'EXPENSE', 'DEBIT'),
        ('PAYROLL_EXPENSE', 'Payroll Expense', 'EXPENSE', 'DEBIT'),
        ('UTILITIES_EXPENSE', 'Utilities Expense', 'EXPENSE', 'DEBIT'),
        ('RENT_EXPENSE', 'Rent Expense', 'EXPENSE', 'DEBIT'),
    ]
    
    cursor.executemany('''
        INSERT OR IGNORE INTO account_types (code, name, category, normal_balance)
        VALUES (?, ?, ?, ?)
    ''', default_account_types)
    
    conn.commit()
    conn.close()
    print("Database initialized successfully!")

if __name__ == '__main__':
    init_database()

