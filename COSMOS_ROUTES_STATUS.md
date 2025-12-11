# Cosmos DB Routes Update Status

## ✅ Completed Routes

The following routes have been updated to support Cosmos DB:

1. **Business Routes**
   - ✅ GET `/api/businesses` - List all businesses
   - ✅ POST `/api/businesses` - Create business
   - ✅ GET `/api/businesses/<id>` - Get business
   - ✅ PUT `/api/businesses/<id>` - Update business
   - ✅ DELETE `/api/businesses/<id>` - Delete business

2. **Chart of Accounts Routes**
   - ✅ GET `/api/businesses/<id>/chart-of-accounts` - List accounts
   - ⚠️ POST `/api/businesses/<id>/chart-of-accounts` - Create account (needs update)
   - ⚠️ PUT `/api/businesses/<id>/chart-of-accounts/<id>` - Update account (needs update)

3. **Account Types Routes**
   - ✅ GET `/api/account-types` - List account types

4. **Transaction Routes**
   - ✅ GET `/api/businesses/<id>/transactions` - List transactions
   - ⚠️ POST `/api/businesses/<id>/transactions` - Create transaction (needs update)
   - ⚠️ PUT `/api/businesses/<id>/transactions/bulk-update` - Bulk update (needs update)

5. **Report Routes**
   - ✅ GET `/api/businesses/<id>/reports/profit-loss` - P&L report
   - ⚠️ GET `/api/businesses/<id>/reports/balance-sheet` - Balance Sheet (needs update)
   - ⚠️ GET `/api/reports/combined-profit-loss` - Combined P&L (needs update)

## ⚠️ Routes That Need Updates

These routes still use SQLite and need to be updated:

### High Priority

1. **Chart of Accounts - Create/Update**
   - POST `/api/businesses/<id>/chart-of-accounts` 
   - PUT `/api/businesses/<id>/chart-of-accounts/<id>`
   - **Complexity**: Medium - Need to handle account type lookup and parent validation

2. **Transaction Creation**
   - POST `/api/businesses/<id>/transactions`
   - **Complexity**: High - Double-entry bookkeeping with embedded lines in Cosmos DB

3. **CSV Import**
   - POST `/api/businesses/<id>/transactions/import-csv`
   - **Complexity**: Very High - Complex logic with account creation, transaction creation, etc.

### Medium Priority

4. **Bank/Credit Card/Loan Accounts**
   - GET/POST routes for bank_accounts, credit_card_accounts, loan_accounts
   - **Complexity**: Low - Similar pattern to businesses

5. **Balance Sheet Report**
   - GET `/api/businesses/<id>/reports/balance-sheet`
   - **Complexity**: Medium - Need to calculate balances from transactions

6. **Combined P&L Report**
   - GET `/api/reports/combined-profit-loss`
   - **Complexity**: High - Hierarchical grouping across all businesses

## How Routes Work

Routes check `USE_COSMOS_DB` environment variable:
- If `USE_COSMOS_DB=1`: Uses Cosmos DB functions
- Otherwise: Uses SQLite (default)

## Example Pattern

```python
@app.route('/api/endpoint', methods=['GET'])
def my_route():
    if USE_COSMOS_DB:
        # Cosmos DB implementation
        data = cosmos_function()
        return jsonify(data)
    else:
        # SQLite implementation
        conn = get_db_connection()
        data = conn.execute('SELECT ...').fetchall()
        conn.close()
        return jsonify([dict(d) for d in data])
```

## Testing

To test with Cosmos DB:

```bash
export USE_COSMOS_DB=1
export COSMOS_ENDPOINT="your-endpoint"
export COSMOS_KEY="your-key"
./start_backend_cosmos.sh
```

## Notes

- **Data Format**: Cosmos DB documents use different field names (e.g., `business_id` vs `id`)
- **Transformation**: Routes transform Cosmos DB format to match frontend expectations
- **Partition Keys**: Always use partition keys in Cosmos DB queries for performance
- **Embedded Data**: Transactions have embedded lines (no separate transaction_lines container)

## Next Steps

1. Update transaction creation route (POST)
2. Update chart of accounts POST/PUT routes
3. Update CSV import (most complex)
4. Update balance sheet report
5. Test all routes with real data

