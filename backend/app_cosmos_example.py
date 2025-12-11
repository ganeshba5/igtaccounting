"""
Example: How to modify app.py to use Cosmos DB

This file shows example route modifications. You would integrate these
patterns into your existing app.py file.
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime, date
import os

# Conditionally import database module
USE_COSMOS_DB = os.environ.get('USE_COSMOS_DB') == '1'

if USE_COSMOS_DB:
    from database_cosmos import (
        get_businesses as cosmos_get_businesses,
        get_business as cosmos_get_business,
        get_chart_of_accounts as cosmos_get_chart_of_accounts,
        get_transactions as cosmos_get_transactions,
        create_item,
        update_item,
        delete_item,
        get_container
    )
else:
    from database import get_db_connection, init_database

app = Flask(__name__)
CORS(app)

# ========== EXAMPLE ROUTES ==========

@app.route('/api/businesses', methods=['GET'])
def get_businesses():
    """Get all businesses - Cosmos DB version."""
    if USE_COSMOS_DB:
        businesses = cosmos_get_businesses()
        # Transform to match expected format
        return jsonify([{
            'id': b['id'],
            'name': b['name'],
            'created_at': b.get('created_at'),
            'updated_at': b.get('updated_at')
        } for b in businesses])
    else:
        # Original SQLite version
        conn = get_db_connection()
        businesses = conn.execute('SELECT * FROM businesses ORDER BY name').fetchall()
        conn.close()
        return jsonify([dict(b) for b in businesses])

@app.route('/api/businesses/<int:business_id>', methods=['GET'])
def get_business(business_id):
    """Get a specific business - Cosmos DB version."""
    if USE_COSMOS_DB:
        business = cosmos_get_business(business_id)
        if business is None:
            return jsonify({'error': 'Business not found'}), 404
        return jsonify({
            'id': business['business_id'],
            'name': business['name'],
            'created_at': business.get('created_at'),
            'updated_at': business.get('updated_at')
        })
    else:
        # Original SQLite version
        conn = get_db_connection()
        business = conn.execute('SELECT * FROM businesses WHERE id = ?', (business_id,)).fetchone()
        conn.close()
        if business is None:
            return jsonify({'error': 'Business not found'}), 404
        return jsonify(dict(business))

@app.route('/api/businesses', methods=['POST'])
def create_business():
    """Create a new business - Cosmos DB version."""
    data = request.get_json()
    name = data.get('name')
    
    if not name:
        return jsonify({'error': 'Business name is required'}), 400
    
    if USE_COSMOS_DB:
        # Get next business_id (in production, use a sequence or UUID)
        businesses = cosmos_get_businesses()
        next_id = max([b['id'] for b in businesses], default=0) + 1
        
        business_doc = {
            'id': f'business-{next_id}',
            'type': 'business',
            'business_id': next_id,
            'name': name,
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }
        
        created = create_item('businesses', business_doc, partition_key=str(next_id))
        return jsonify({
            'id': created['business_id'],
            'name': created['name'],
            'created_at': created['created_at'],
            'updated_at': created['updated_at']
        }), 201
    else:
        # Original SQLite version
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO businesses (name) VALUES (?)', (name,))
        business_id = cursor.lastrowid
        conn.commit()
        business = conn.execute('SELECT * FROM businesses WHERE id = ?', (business_id,)).fetchone()
        conn.close()
        return jsonify(dict(business)), 201

@app.route('/api/businesses/<int:business_id>/chart-of-accounts', methods=['GET'])
def get_chart_of_accounts(business_id):
    """Get chart of accounts - Cosmos DB version."""
    if USE_COSMOS_DB:
        accounts = cosmos_get_chart_of_accounts(business_id)
        # Transform to match expected format
        result = []
        for acc in accounts:
            account_type = acc.get('account_type', {})
            result.append({
                'id': acc['id'],
                'business_id': business_id,
                'account_code': acc['account_code'],
                'account_name': acc['account_name'],
                'description': acc.get('description'),
                'parent_account_id': acc.get('parent_account_id'),
                'is_active': acc.get('is_active', True),
                'account_type_id': account_type.get('id') if account_type else None,
                'account_type_code': account_type.get('code', ''),
                'account_type_name': account_type.get('name', ''),
                'category': account_type.get('category', ''),
                'normal_balance': account_type.get('normal_balance', '')
            })
        return jsonify(result)
    else:
        # Original SQLite version
        conn = get_db_connection()
        accounts = conn.execute('''
            SELECT coa.*, at.code as account_type_code, at.name as account_type_name, 
                   at.category, at.normal_balance
            FROM chart_of_accounts coa
            LEFT JOIN account_types at ON coa.account_type_id = at.id
            WHERE coa.business_id = ?
            ORDER BY coa.account_code
        ''', (business_id,)).fetchall()
        conn.close()
        return jsonify([dict(a) for a in accounts])

@app.route('/api/businesses/<int:business_id>/transactions', methods=['GET'])
def get_transactions(business_id):
    """Get transactions - Cosmos DB version."""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    account_id = request.args.get('account_id', type=int)
    
    if USE_COSMOS_DB:
        transactions = cosmos_get_transactions(
            business_id,
            start_date=start_date,
            end_date=end_date,
            account_id=account_id
        )
        
        # Transform to match expected format
        result = []
        for txn in transactions:
            txn_dict = {
                'id': txn['id'],
                'business_id': txn['business_id'],
                'transaction_date': txn['transaction_date'],
                'description': txn.get('description'),
                'reference_number': txn.get('reference_number'),
                'transaction_type': txn.get('transaction_type'),
                'amount': txn.get('amount', 0),
                'created_at': txn.get('created_at'),
                'lines': []
            }
            
            # Transform embedded lines
            for line in txn.get('lines', []):
                txn_dict['lines'].append({
                    'id': line.get('transaction_line_id'),
                    'transaction_id': txn['id'],
                    'chart_of_account_id': line.get('chart_of_account_id'),
                    'debit_amount': line.get('debit_amount', 0),
                    'credit_amount': line.get('credit_amount', 0),
                    'account_code': line.get('account_code'),
                    'account_name': line.get('account_name')
                })
            
            result.append(txn_dict)
        
        return jsonify(result)
    else:
        # Original SQLite version
        conn = get_db_connection()
        
        if account_id:
            query = '''
                SELECT DISTINCT t.*
                FROM transactions t
                INNER JOIN transaction_lines tl ON t.id = tl.transaction_id
                WHERE t.business_id = ? AND tl.chart_of_account_id = ?
            '''
            params = [business_id, account_id]
        else:
            query = 'SELECT * FROM transactions WHERE business_id = ?'
            params = [business_id]
        
        if start_date:
            query += ' AND transaction_date >= ?'
            params.append(start_date)
        if end_date:
            query += ' AND transaction_date <= ?'
            params.append(end_date)
        
        query += ' ORDER BY transaction_date DESC, id DESC'
        transactions = conn.execute(query, params).fetchall()
        
        result = []
        for txn in transactions:
            txn_dict = dict(txn)
            lines = conn.execute('''
                SELECT tl.*, coa.account_code, coa.account_name
                FROM transaction_lines tl
                JOIN chart_of_accounts coa ON tl.chart_of_account_id = coa.id
                WHERE tl.transaction_id = ?
            ''', (txn['id'],)).fetchall()
            txn_dict['lines'] = [dict(l) for l in lines]
            result.append(txn_dict)
        
        conn.close()
        return jsonify(result)

# ========== NOTES ==========

"""
Key Differences When Using Cosmos DB:

1. **No Foreign Key Constraints**: 
   - Must validate relationships in application code
   - Cascading deletes must be implemented manually

2. **Partition Keys**:
   - Always provide partition key for single-partition queries (faster, cheaper)
   - Cross-partition queries are slower and consume more RUs

3. **Embedded vs Referenced Data**:
   - Transaction lines are embedded in transactions (atomicity)
   - Account types are embedded in chart_of_accounts (denormalization for performance)

4. **Query Limitations**:
   - JOINs are limited (only self-joins and single-level)
   - Complex aggregations may need to be done in application code
   - Date filtering uses string comparison (ensure ISO format)

5. **ID Generation**:
   - Cosmos DB uses string IDs (we use "type-id" format)
   - Need to maintain integer IDs for compatibility
   - Consider using UUIDs for new systems

6. **Transactions**:
   - Cosmos DB transactions are limited to single partition
   - Double-entry bookkeeping must ensure transaction and lines are in same partition
   - We use business_id as partition key to ensure this

7. **Error Handling**:
   - CosmosResourceNotFoundError instead of None checks
   - Rate limiting errors (429) need retry logic
   - Connection errors need proper handling
"""

if __name__ == '__main__':
    if not USE_COSMOS_DB:
        init_database()
    app.run(debug=True, port=5001)

