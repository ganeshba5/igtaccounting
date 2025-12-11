# CSV Import Formats and Mapping

This document describes the supported CSV import formats and how transaction types are mapped.

## Supported CSV Formats

The system supports **two CSV formats** for importing transactions, with column name aliases supported for Format 2.

### Format 1: Type-Based Format

**Required Columns:**
- `Details` (optional, used as fallback for Description)
- `Posting Date`
- `Description`
- `Amount`
- `Type` (transaction type from CSV)
- `Balance`
- `Check or Slip #` (optional)

**Example:**
```csv
Details,Posting Date,Description,Amount,Type,Balance,Check or Slip #
,06/04/2024,GOOGLE PAYMENT,100.00,ACH_CREDIT,5000.00,
,06/05/2024,AMAZON PURCHASE,50.00,DEBIT_CARD,4950.00,
```

**How it works:**
- The `Type` column determines if the transaction is a DEBIT or CREDIT
- The system looks up the `Type` value in the `transaction_type_mappings` table
- If not found, it auto-creates a mapping based on keywords in the type name

### Format 2: Amount Sign-Based Format

**Required Columns:**
- `Posting Date` (or alias: `Date`)
- `Description`
- `Amount` (negative = Debit, positive = Credit)
- `Balance` (or aliases: `Running Bal.`, `Running Balance`, `Running Bal`)

**Example 1 (Standard column names):**
```csv
Posting Date,Description,Amount,Balance
06/04/2024,GOOGLE PAYMENT,100.00,5000.00
06/05/2024,AMAZON PURCHASE,-50.00,4950.00
```

**Example 2 (With aliases):**
```csv
Date,Description,Amount,Running Bal.
06/04/2024,GOOGLE PAYMENT,100.00,5000.00
06/05/2024,AMAZON PURCHASE,-50.00,4950.00
```

**How it works:**
- **Negative Amount** = DEBIT (money going out) → Creates WITHDRAWAL transaction
- **Positive Amount** = CREDIT (money coming in) → Creates DEPOSIT transaction
- No `Type` column needed
- Column name aliases are automatically recognized and normalized

### Header Row Detection

The system automatically **skips lines until it finds the header row**. This is useful for CSV files that contain:
- Metadata lines at the top
- Account information
- Other non-data rows

**How it works:**
- Scans the first 20 lines of the CSV file
- Looks for a row that matches one of the supported formats (case-insensitive matching)
- Column name matching is case-insensitive (e.g., `Date`, `DATE`, `date` are all recognized)
- Once found, uses that row as the header and processes all subsequent rows as data
- If no header is found in the first 20 lines, returns an error

**Example CSV with metadata:**
```csv
Account Statement
Account Number: 123456789
Period: January 2024

Date,Description,Amount,Running Bal.
06/04/2024,GOOGLE PAYMENT,100.00,5000.00
06/05/2024,AMAZON PURCHASE,-50.00,4950.00
```

In this example, the system will skip the first 4 lines and use line 5 as the header row.

## Transaction Type Mapping

### Default Mappings

The system includes the following default transaction type mappings:

| CSV Type | Internal Type | Direction | Description |
|----------|---------------|-----------|-------------|
| `DEBIT` | WITHDRAWAL | DEBIT | Debit transaction |
| `CREDIT` | DEPOSIT | CREDIT | Credit transaction |
| `WITHDRAWAL` | WITHDRAWAL | DEBIT | Withdrawal |
| `DEPOSIT` | DEPOSIT | CREDIT | Deposit |
| `CHARGE` | CHARGE | DEBIT | Charge |
| `PAYMENT` | PAYMENT | DEBIT | Payment |
| `PAYMENT_RECEIVED` | PAYMENT_RECEIVED | CREDIT | Payment received |
| `ACH_CREDIT` | DEPOSIT | CREDIT | ACH credit transfer |
| `ACH_DEBIT` | WITHDRAWAL | DEBIT | ACH debit transfer |
| `DEBIT_CARD` | CHARGE | DEBIT | Debit card transaction |
| `CREDIT_CARD` | CHARGE | DEBIT | Credit card charge |
| `FEE_TRANSACTION` | EXPENSE | DEBIT | Fee transaction |
| `FEE` | EXPENSE | DEBIT | Fee |
| `TRANSFER_IN` | DEPOSIT | CREDIT | Transfer in |
| `TRANSFER_OUT` | WITHDRAWAL | DEBIT | Transfer out |
| `CHECK` | PAYMENT | DEBIT | Check payment |
| `WIRE_TRANSFER` | TRANSFER | DEBIT | Wire transfer |
| `INTEREST` | INCOME | CREDIT | Interest income |
| `DIVIDEND` | INCOME | CREDIT | Dividend income |

### Auto-Creation of Mappings

If a CSV transaction type is not found in the mapping table, the system **automatically creates** a new mapping by analyzing keywords in the type name:

**CREDIT Keywords** (money coming in):
- `CREDIT`, `DEPOSIT`, `INCOME`, `RECEIVED`, `INTEREST`, `DIVIDEND`
- Maps to: `DEPOSIT`, `INCOME`, or `PAYMENT_RECEIVED` (depending on keywords)
- Direction: `CREDIT`

**DEBIT Keywords** (money going out):
- `DEBIT`, `WITHDRAWAL`, `PAYMENT`, `CHARGE`, `FEE`, `EXPENSE`
- Maps to: `WITHDRAWAL`, `EXPENSE`, or `PAYMENT` (depending on keywords)
- Direction: `DEBIT`

**Default** (if no keywords match):
- Maps to: `ADJUSTMENT`
- Direction: `DEBIT`

## Internal Transaction Types

The system uses the following internal transaction types:

- `DEPOSIT` - Money deposited into account
- `WITHDRAWAL` - Money withdrawn from account
- `TRANSFER` - Transfer between accounts
- `PAYMENT` - Payment made
- `CHARGE` - Charge on account
- `PAYMENT_RECEIVED` - Payment received
- `EXPENSE` - Expense transaction
- `INCOME` - Income transaction
- `ADJUSTMENT` - Adjustment/correction

## Double-Entry Bookkeeping

Each CSV row creates a transaction with **two transaction lines** (double-entry):

### DEBIT Transactions (Money Going Out)
1. **Line 1**: Debit the **Expense Account** (or Uncategorized Expense)
2. **Line 2**: Credit the **Bank Account**

### CREDIT Transactions (Money Coming In)
1. **Line 1**: Debit the **Bank Account**
2. **Line 2**: Credit the **Revenue Account** (or Uncategorized Revenue)

## Account Mapping

### Required Accounts
- **Bank Account** (required): Selected during import, must exist in the system

### Optional Accounts
- **Expense Account** (optional): Used for DEBIT transactions
  - If not provided, defaults to "Uncategorized Expense" (auto-created if needed)
- **Revenue Account** (optional): Used for CREDIT transactions
  - If not provided, defaults to "Uncategorized Revenue" (auto-created if needed)

### Auto-Created Accounts
The system automatically creates the following accounts if they don't exist:
- `UNCATEGORIZED_EXPENSE` - For DEBIT transactions without a specific expense account
- `UNCATEGORIZED_REVENUE` - For CREDIT transactions without a specific revenue account

## Date Format Support

The system supports multiple date formats:

1. `%m/%d/%y` - 6/4/24 or 06/04/24 (2-digit year)
2. `%m/%d/%Y` - 6/4/2024 or 06/04/2024 (4-digit year)
3. `%Y-%m-%d` - 2024-06-04 (ISO format)
4. `%m-%d-%Y` - 06-04-2024
5. `%d/%m/%Y` - 04/06/2024 (European format)
6. `%d/%m/%y` - 04/06/24 (European format with 2-digit year)

**2-Digit Year Handling:**
- Years 00-49 → 2000-2049
- Years 50-99 → 1950-1999

If standard parsing fails, the system uses regex fallback to parse dates in `M/D/YY` or `M/D/YYYY` format.

## CSV Parsing Features

### Quoted Fields
The CSV parser correctly handles:
- Fields with embedded commas: `"GOOGLE, INC"` is parsed as a single field
- Escaped quotes: `"Company ""ABC"" Inc"` is parsed as `Company "ABC" Inc`
- Mixed quoted and unquoted fields

### Amount Parsing
- Removes commas: `1,000.00` → `1000.00`
- Removes dollar signs: `$100.00` → `100.00`
- Handles negative amounts: `-50.00` (for Format 2)

## Import Process Flow

1. **File Upload**: User selects CSV file and bank account
2. **Format Detection**: System detects Format 1 or Format 2 based on column names
3. **Row Processing**: For each row:
   - Parse date (try multiple formats)
   - Parse amount
   - Determine direction (from Type mapping or amount sign)
   - Get or create transaction type mapping
   - Create transaction with two lines (double-entry)
4. **Result**: Returns count of imported, skipped, and errors

## Error Handling

The system skips rows with:
- Missing required columns
- Invalid date format (after trying all formats)
- Invalid amount format
- Missing or invalid transaction type (Format 1 only)
- Missing required accounts

All errors are reported in the import result with row numbers.

## API Endpoint

**POST** `/api/businesses/:businessId/transactions/import-csv`

**Form Data:**
- `file` - CSV file (required)
- `bank_account_id` - Bank account ID (required)
- `expense_account_id` - Expense account ID (optional)
- `revenue_account_id` - Revenue account ID (optional)

**Response:**
```json
{
  "imported": 10,
  "skipped": 2,
  "errors": [
    "Row 5: Invalid date format: 13/45/24",
    "Row 8: Invalid amount: abc"
  ]
}
```

## Managing Transaction Type Mappings

You can manage transaction type mappings via API:

- **GET** `/api/transaction-type-mappings` - List all mappings
- **POST** `/api/transaction-type-mappings` - Create new mapping
- **PUT** `/api/transaction-type-mappings/:id` - Update mapping
- **DELETE** `/api/transaction-type-mappings/:id` - Delete mapping

**Mapping Schema:**
- `csv_type` - The transaction type as it appears in CSV (unique)
- `internal_type` - One of: DEPOSIT, WITHDRAWAL, TRANSFER, PAYMENT, CHARGE, PAYMENT_RECEIVED, EXPENSE, INCOME, ADJUSTMENT
- `direction` - DEBIT or CREDIT
- `description` - Human-readable description

