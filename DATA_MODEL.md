# Accounting System Data Model

## Overview
This document describes the complete database schema for the multi-business accounting system. The system uses SQLite and implements double-entry bookkeeping principles.

## Entity Relationship Diagram (Textual)

```
Businesses (1) ────┬─── (Many) Chart of Accounts
                   ├─── (Many) Bank Accounts
                   ├─── (Many) Credit Card Accounts
                   ├─── (Many) Loan Accounts
                   └─── (Many) Transactions

Account Types (1) ──── (Many) Chart of Accounts

Chart of Accounts (1) ────┬─── (Many) Chart of Accounts (parent)
                          └─── (Many) Transaction Lines

Transactions (1) ──── (Many) Transaction Lines

Transaction Type Mappings (Standalone lookup table)
```

## Tables

### 1. businesses
Stores business entities - supports multiple businesses in the system.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY, AUTOINCREMENT | Unique business identifier |
| name | TEXT | NOT NULL | Business name |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Record creation timestamp |
| updated_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Last update timestamp |

**Relationships:**
- One-to-Many: `chart_of_accounts`, `bank_accounts`, `credit_card_accounts`, `loan_accounts`, `transactions`

---

### 2. account_types
Master list of account types/categories. Pre-populated with standard accounting categories.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY, AUTOINCREMENT | Unique account type identifier |
| code | TEXT | NOT NULL, UNIQUE | Account type code (e.g., 'ASSET', 'LIABILITY') |
| name | TEXT | NOT NULL | Account type name |
| category | TEXT | NOT NULL | Category: ASSET, LIABILITY, EQUITY, REVENUE, EXPENSE |
| normal_balance | TEXT | NOT NULL, CHECK (DEBIT/CREDIT) | Normal balance side |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Record creation timestamp |

**Default Categories:**
- **ASSET**: Assets, Cash, Bank Accounts, Accounts Receivable, Inventory, Fixed Assets
- **LIABILITY**: Liabilities, Accounts Payable, Credit Cards, Loans
- **EQUITY**: Equity, Capital, Retained Earnings
- **REVENUE**: Revenue, Sales, Service Revenue
- **EXPENSE**: Expenses, COGS, Operating Expenses, Payroll, Utilities, Rent

**Relationships:**
- One-to-Many: `chart_of_accounts`

---

### 3. chart_of_accounts
Business-specific chart of accounts. Each business has its own configurable chart.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY, AUTOINCREMENT | Unique account identifier |
| business_id | INTEGER | NOT NULL, FOREIGN KEY | References businesses(id) |
| account_type_id | INTEGER | FOREIGN KEY | References account_types(id) |
| account_code | TEXT | NOT NULL | Unique account code per business |
| account_name | TEXT | NOT NULL | Account name |
| description | TEXT | | Account description |
| parent_account_id | INTEGER | FOREIGN KEY | References chart_of_accounts(id) - for hierarchy |
| is_active | BOOLEAN | DEFAULT 1 | Whether account is active |

**Constraints:**
- `UNIQUE(business_id, account_code)` - Account codes must be unique per business
- `FOREIGN KEY (business_id) REFERENCES businesses(id) ON DELETE CASCADE`
- `FOREIGN KEY (account_type_id) REFERENCES account_types(id)`
- `FOREIGN KEY (parent_account_id) REFERENCES chart_of_accounts(id)`

**Relationships:**
- Many-to-One: `businesses`, `account_types`
- One-to-Many: `chart_of_accounts` (self-referential for parent accounts)
- One-to-Many: `transaction_lines`

---

### 4. bank_accounts
Stores bank account information for each business.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY, AUTOINCREMENT | Unique bank account identifier |
| business_id | INTEGER | NOT NULL, FOREIGN KEY | References businesses(id) |
| account_name | TEXT | NOT NULL | Bank account name |
| account_number | TEXT | | Bank account number |
| bank_name | TEXT | | Name of the bank |
| routing_number | TEXT | | Bank routing number |
| opening_balance | REAL | DEFAULT 0 | Opening balance |
| current_balance | REAL | DEFAULT 0 | Current balance |
| account_code | TEXT | | Optional account code for chart of accounts mapping |
| is_active | BOOLEAN | DEFAULT 1 | Whether account is active |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Record creation timestamp |

**Relationships:**
- Many-to-One: `businesses`

---

### 5. credit_card_accounts
Stores credit card account information for each business.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY, AUTOINCREMENT | Unique credit card identifier |
| business_id | INTEGER | NOT NULL, FOREIGN KEY | References businesses(id) |
| account_name | TEXT | NOT NULL | Credit card account name |
| card_number_last4 | TEXT | | Last 4 digits of card number |
| issuer | TEXT | | Credit card issuer (e.g., Visa, MasterCard) |
| credit_limit | REAL | DEFAULT 0 | Credit limit |
| current_balance | REAL | DEFAULT 0 | Current balance |
| account_code | TEXT | | Optional account code for chart of accounts mapping |
| is_active | BOOLEAN | DEFAULT 1 | Whether account is active |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Record creation timestamp |

**Relationships:**
- Many-to-One: `businesses`

---

### 6. loan_accounts
Stores loan account information for each business.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY, AUTOINCREMENT | Unique loan identifier |
| business_id | INTEGER | NOT NULL, FOREIGN KEY | References businesses(id) |
| account_name | TEXT | NOT NULL | Loan account name |
| lender_name | TEXT | | Name of the lender |
| loan_number | TEXT | | Loan number |
| principal_amount | REAL | DEFAULT 0 | Original principal amount |
| current_balance | REAL | DEFAULT 0 | Current outstanding balance |
| interest_rate | REAL | DEFAULT 0 | Interest rate percentage |
| account_code | TEXT | | Optional account code for chart of accounts mapping |
| is_active | BOOLEAN | DEFAULT 1 | Whether account is active |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Record creation timestamp |

**Relationships:**
- Many-to-One: `businesses`

---

### 7. transactions
Main transaction header table. Stores transaction metadata.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY, AUTOINCREMENT | Unique transaction identifier |
| business_id | INTEGER | NOT NULL, FOREIGN KEY | References businesses(id) |
| transaction_date | DATE | NOT NULL | Transaction date |
| description | TEXT | | Transaction description |
| reference_number | TEXT | | Reference number (check number, invoice, etc.) |
| transaction_type | TEXT | CHECK constraint | Type: DEPOSIT, WITHDRAWAL, TRANSFER, PAYMENT, CHARGE, PAYMENT_RECEIVED, EXPENSE, INCOME, ADJUSTMENT |
| amount | REAL | NOT NULL | Total transaction amount |
| account_id | INTEGER | | Legacy: References specific account (optional) |
| account_type | TEXT | CHECK constraint | Legacy: Type of account (BANK, CREDIT_CARD, LOAN, CHART_OF_ACCOUNTS) |
| chart_of_account_id | INTEGER | FOREIGN KEY | Legacy: References chart_of_accounts(id) |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Record creation timestamp |

**Constraints:**
- `FOREIGN KEY (business_id) REFERENCES businesses(id) ON DELETE CASCADE`
- `FOREIGN KEY (chart_of_account_id) REFERENCES chart_of_accounts(id)`

**Relationships:**
- Many-to-One: `businesses`, `chart_of_accounts` (optional)
- One-to-Many: `transaction_lines`

**Note:** The actual accounting entries are stored in `transaction_lines` table (double-entry bookkeeping).

---

### 8. transaction_lines
Double-entry bookkeeping transaction lines. Each transaction has at least 2 lines (one debit, one credit).

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY, AUTOINCREMENT | Unique line identifier |
| transaction_id | INTEGER | NOT NULL, FOREIGN KEY | References transactions(id) |
| chart_of_account_id | INTEGER | NOT NULL, FOREIGN KEY | References chart_of_accounts(id) |
| debit_amount | REAL | DEFAULT 0 | Debit amount (if applicable) |
| credit_amount | REAL | DEFAULT 0 | Credit amount (if applicable) |

**Constraints:**
- `FOREIGN KEY (transaction_id) REFERENCES transactions(id) ON DELETE CASCADE`
- `FOREIGN KEY (chart_of_account_id) REFERENCES chart_of_accounts(id)`

**Business Rules:**
- Each transaction must have at least 2 lines
- Total debits must equal total credits
- Each line must have either a debit_amount OR credit_amount (not both, not neither)

**Relationships:**
- Many-to-One: `transactions`, `chart_of_accounts`

---

### 9. transaction_type_mappings
Maps CSV transaction types to internal transaction types. Supports CSV import functionality.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY, AUTOINCREMENT | Unique mapping identifier |
| csv_type | TEXT | NOT NULL, UNIQUE | CSV transaction type (e.g., 'ACH_CREDIT', 'DEBIT_CARD') |
| internal_type | TEXT | NOT NULL, CHECK constraint | Internal type: DEPOSIT, WITHDRAWAL, TRANSFER, PAYMENT, CHARGE, PAYMENT_RECEIVED, EXPENSE, INCOME, ADJUSTMENT |
| direction | TEXT | NOT NULL, CHECK constraint | Direction: DEBIT (money out) or CREDIT (money in) |
| description | TEXT | | Human-readable description |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Record creation timestamp |

**Default Mappings Include:**
- `ACH_CREDIT` → DEPOSIT (CREDIT)
- `ACH_DEBIT` → WITHDRAWAL (DEBIT)
- `DEBIT_CARD` → CHARGE (DEBIT)
- `FEE_TRANSACTION` → EXPENSE (DEBIT)
- `INTEREST` → INCOME (CREDIT)
- And 14+ more common types

**Auto-Creation:**
- If a CSV type is not found, the system automatically creates a mapping by analyzing keywords in the type name.

---

## Indexes

For performance optimization:

1. **idx_transactions_business_date** - `transactions(business_id, transaction_date)`
   - Speeds up date range queries and business-specific transaction lookups

2. **idx_chart_of_accounts_business** - `chart_of_accounts(business_id)`
   - Speeds up chart of accounts retrieval per business

3. **idx_transaction_lines_transaction** - `transaction_lines(transaction_id)`
   - Speeds up transaction line lookups for each transaction

4. **idx_transaction_type_mappings_csv_type** - `transaction_type_mappings(csv_type)`
   - Speeds up CSV type lookups during import

---

## Double-Entry Bookkeeping Model

The system implements **double-entry bookkeeping** where:

1. **Every transaction** creates at least 2 entries in `transaction_lines`
2. **Total debits = Total credits** for each transaction
3. **Account balances** are calculated from the sum of transaction lines

**Example Transaction:**
```
Transaction: Pay rent $1,000 from bank account

Transaction Lines:
1. Debit:  Rent Expense Account    $1,000
2. Credit: Bank Account            $1,000
```

---

## Account Categories & Normal Balances

| Category | Normal Balance | Examples |
|----------|---------------|----------|
| ASSET | DEBIT | Cash, Bank Accounts, Inventory, Equipment |
| LIABILITY | CREDIT | Loans, Credit Cards, Accounts Payable |
| EQUITY | CREDIT | Capital, Retained Earnings |
| REVENUE | CREDIT | Sales, Service Revenue, Interest Income |
| EXPENSE | DEBIT | Rent, Utilities, Payroll, Cost of Goods Sold |

---

## Key Design Decisions

1. **Multi-business Support**: All business-specific data references `business_id`
2. **Configurable Chart of Accounts**: Each business has its own chart (`business_id` + `account_code` unique)
3. **Double-Entry**: All transactions use `transaction_lines` with debits and credits
4. **Account Types vs Chart of Accounts**: 
   - `account_types` = Master list (shared across all businesses)
   - `chart_of_accounts` = Business-specific instances
5. **Account Codes**: Unique per business, allowing same code across different businesses
6. **Cascading Deletes**: Deleting a business removes all related accounts and transactions
7. **Transaction Type Mapping**: Flexible system for CSV imports with auto-creation capability

---

## Data Flow Example: CSV Import

1. CSV file uploaded with transaction type `ACH_CREDIT`
2. System looks up `transaction_type_mappings` for `ACH_CREDIT`
3. Finds: `internal_type = DEPOSIT`, `direction = CREDIT`
4. Creates transaction with type `DEPOSIT`
5. Creates 2 transaction lines:
   - Debit: Bank Account (from selected bank account)
   - Credit: Revenue Account (from selected or uncategorized)
6. Both lines reference `chart_of_accounts` entries

---

## Notes

- The database is SQLite, stored at `/accounting.db`
- All timestamps use SQLite's CURRENT_TIMESTAMP
- Currency amounts are stored as REAL (floating point) - consider using DECIMAL in production
- Account codes are case-sensitive text fields
- The system supports hierarchical chart of accounts via `parent_account_id`

