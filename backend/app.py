"""
Main Flask application for the accounting system.
"""
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from datetime import datetime, date
import json
import sqlite3
import csv
import io
import os
import sys
from functools import wraps

# Check if using Cosmos DB
USE_COSMOS_DB = os.environ.get('USE_COSMOS_DB') == '1'

if USE_COSMOS_DB:
    # Use Cosmos DB
    from database_cosmos import (
        get_businesses as cosmos_get_businesses,
        get_business as cosmos_get_business,
        get_chart_of_accounts as cosmos_get_chart_of_accounts,
        get_transactions as cosmos_get_transactions,
        get_profit_loss_accounts as cosmos_get_profit_loss_accounts,
        query_items, create_item, update_item, delete_item, get_item,
        get_container, init_database as cosmos_init_database,
        get_chart_of_account, get_transaction, get_next_id
    )
    # Import account types and other getters
    from database_cosmos import query_items as cosmos_query_items
    print("✅ Using Azure Cosmos DB")
else:
    # Use SQLite (default)
    from database import get_db_connection, init_database
    print("✅ Using SQLite database")

# Determine if we should serve static files (production mode)
# Set FLASK_ENV=production or BUILD_FRONTEND=1 to enable
SERVE_STATIC = os.environ.get('FLASK_ENV') == 'production' or os.environ.get('BUILD_FRONTEND') == '1'

app = Flask(__name__)

# Configure CORS based on environment
if os.environ.get('FLASK_ENV') == 'production':
    # In production, allow specific origins
    cors_origins_env = os.environ.get('CORS_ORIGINS', '')
    allowed_origins = None
    
    if cors_origins_env:
        # Split and strip whitespace from each origin
        parsed_origins = [origin.strip() for origin in cors_origins_env.split(',') if origin.strip()]
        if parsed_origins:
            allowed_origins = parsed_origins
            print(f"✅ CORS configured with origins from environment: {allowed_origins}")
        else:
            print("⚠️ CORS_ORIGINS is set but empty after parsing, using fallback")
    
    # Use fallback if no valid origins from environment
    if not allowed_origins:
        print("⚠️ Using fallback CORS origins")
        allowed_origins = [
            'https://thankful-rock-0bea0c80f.3.azurestaticapps.net',
            'https://acc.infogloballink.com',
            'http://localhost:3000',  # For local testing
            'http://localhost:5001'   # For local testing
        ]
    
    print(f"✅ CORS configured with origins: {allowed_origins}")
    # Configure CORS with explicit settings for flask-cors 4.0.0
    CORS(app, 
         origins=allowed_origins,
         supports_credentials=True,
         allow_headers=["Content-Type", "Authorization"],
         methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
    print(f"✅ CORS initialized with {len(allowed_origins)} allowed origins")
else:
    # In development, allow all origins
    CORS(app)

# Path to frontend build directory
FRONTEND_BUILD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'frontend', 'build')

# Initialize database on startup
if USE_COSMOS_DB:
    # Check if Cosmos DB environment variables are set
    cosmos_endpoint = os.environ.get('COSMOS_ENDPOINT')
    cosmos_key = os.environ.get('COSMOS_KEY')
    
    if not cosmos_endpoint or not cosmos_key:
        print("⚠️  Warning: USE_COSMOS_DB=1 but COSMOS_ENDPOINT and/or COSMOS_KEY are not set.")
        print("   The server will start, but Cosmos DB operations will fail.")
        print("   To use Cosmos DB, set these environment variables:")
        print("   export COSMOS_ENDPOINT='https://your-account.documents.azure.com:443/'")
        print("   export COSMOS_KEY='your-primary-key'")
    else:
        try:
            cosmos_init_database()
            print("✅ Cosmos DB initialized successfully")
        except Exception as e:
            print(f"⚠️  Warning: Could not initialize Cosmos DB: {e}")
            print("   The server will start, but Cosmos DB operations may fail.")
else:
    init_database()

def date_handler(obj):
    """JSON serializer for datetime and date objects."""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

# Import authentication
try:
    from auth import require_auth
    AUTH_ENABLED = os.environ.get('ENABLE_AUTH', '0') == '1'
    if not AUTH_ENABLED:
        # Create no-op decorator if auth is disabled
        def require_auth(f):
            return f
except ImportError:
    # No-op decorator if auth module not available
    def require_auth(f):
        return f
    AUTH_ENABLED = False

# ========== USER MANAGEMENT UTILITIES ==========

def get_user_by_email(email):
    """Get user by email address."""
    if USE_COSMOS_DB:
        # Query users by email (email is partition key)
        try:
            # Try to get directly by id (email) first
            user = get_item('users', email, partition_key=email)
            if user and user.get('type') == 'user':
                return user
        except:
            pass
        
        # Fallback: query by email
        users = cosmos_query_items(
            'users',
            'SELECT * FROM c WHERE c.type = "user" AND c.email = @email',
            [{"name": "@email", "value": email}],
            partition_key=email
        )
        return users[0] if users else None
    else:
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        conn.close()
        return dict(user) if user else None

def user_has_business_access(user, business_id):
    """Check if user has access to a specific business."""
    if not user:
        return False
    
    # Get business IDs user has access to
    business_ids = user.get('business_ids', [])
    if isinstance(business_ids, str):
        # If stored as JSON string, parse it
        try:
            business_ids = json.loads(business_ids)
        except:
            business_ids = []
    
    # Convert to list of integers for comparison
    business_ids = [int(bid) for bid in business_ids if bid]
    return int(business_id) in business_ids

def require_user_access(f):
    """Decorator to ensure user is in the users list and has business access."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Get user from request (set by require_auth decorator)
        user_info = getattr(request, 'user', None)
        if not user_info:
            return jsonify({'error': 'User not authenticated'}), 401
        
        # Get user email from token
        user_email = user_info.get('preferred_username') or user_info.get('email') or user_info.get('upn')
        if not user_email:
            print(f"DEBUG require_user_access: No email found in token. Available fields: {list(user_info.keys())}")
            return jsonify({'error': 'User email not found in token'}), 401
        
        print(f"DEBUG require_user_access: Checking user access for email: {user_email}")
        print(f"DEBUG require_user_access: Token fields: preferred_username={user_info.get('preferred_username')}, email={user_info.get('email')}, upn={user_info.get('upn')}")
        
        # Check if user exists in users table
        user = get_user_by_email(user_email)
        if not user:
            print(f"DEBUG require_user_access: User '{user_email}' not found in users table")
            return jsonify({
                'error': 'Access denied',
                'message': f'Your email ({user_email}) is not authorized to access this application. Please contact your administrator.',
                'debug_email': user_email  # Include in response for debugging
            }), 403
        
        print(f"DEBUG require_user_access: User '{user_email}' found, has access to businesses: {user.get('business_ids', [])}")
        
        # Check business access if business_id is present
        business_id = kwargs.get('business_id')
        if not business_id:
            # Try to get from args
            for arg in args:
                if isinstance(arg, int):
                    business_id = arg
                    break
        
        if business_id:
            if not user_has_business_access(user, business_id):
                return jsonify({
                    'error': 'Access denied',
                    'message': f'You do not have access to business {business_id}.'
                }), 403
        
        # Store user info in request for use in route handlers
        request.current_user = user
        return f(*args, **kwargs)
    
    return decorated_function

# ========== DEBUG ROUTE ==========

@app.route('/api/debug/user-info', methods=['GET'])
@require_auth
def debug_user_info():
    """Debug endpoint to see what user information is in the token."""
    user_info = getattr(request, 'user', None)
    if not user_info:
        return jsonify({'error': 'No user info in token'}), 401
    
    # Get user email from token
    user_email = user_info.get('preferred_username') or user_info.get('email') or user_info.get('upn')
    
    # Check if user exists
    user = None
    if user_email:
        user = get_user_by_email(user_email)
    
    return jsonify({
        'token_fields': {
            'preferred_username': user_info.get('preferred_username'),
            'email': user_info.get('email'),
            'upn': user_info.get('upn'),
            'name': user_info.get('name'),
            'oid': user_info.get('oid'),
            'tid': user_info.get('tid'),
            'all_fields': list(user_info.keys())
        },
        'extracted_email': user_email,
        'user_found_in_db': user is not None,
        'user_business_ids': user.get('business_ids', []) if user else None,
        'message': 'Check extracted_email and compare with users in database'
    }), 200

# ========== BUSINESS ROUTES ==========

@app.route('/api/businesses', methods=['GET'])
@require_auth
@require_user_access
def get_businesses():
    """Get all businesses the user has access to."""
    # User should already be validated and stored in request.current_user by require_user_access
    user = getattr(request, 'current_user', {})
    
    if not user:
        print("ERROR get_businesses: current_user not found in request")
        return jsonify({'error': 'User not found in request'}), 500
    
    print(f"DEBUG get_businesses: Request received, user email: {user.get('email', 'N/A')}")
    
    # Get business IDs user has access to
    business_ids = user.get('business_ids', [])
    if isinstance(business_ids, str):
        try:
            business_ids = json.loads(business_ids)
        except:
            business_ids = []
    business_ids = [int(bid) for bid in business_ids if bid]
    
    print(f"DEBUG get_businesses: Business IDs user has access to: {business_ids}")
    
    if USE_COSMOS_DB:
        all_businesses = cosmos_get_businesses()
        print(f"DEBUG get_businesses: Found {len(all_businesses)} total businesses in database")
        
        # Filter to only businesses user has access to
        businesses = []
        for b in all_businesses:
            # cosmos_get_businesses() returns: {'id': business_id, 'name': ..., ...}
            # The 'id' field is actually the business_id (from SELECT c.business_id as id)
            bid = b.get('business_id') or b.get('id')
            if bid is None:
                # Try to extract from id if it's in format "business-1"
                id_str = str(b.get('id', ''))
                if id_str.startswith('business-'):
                    try:
                        bid = int(id_str.replace('business-', ''))
                    except:
                        continue
                else:
                    continue
            
            bid_int = int(bid) if bid else None
            print(f"DEBUG get_businesses: Checking business bid={bid_int}, business_ids list={business_ids}")
            if bid_int and bid_int in business_ids:
                businesses.append({
                    'id': bid_int,
                    'name': b.get('name'),
                    'created_at': b.get('created_at'),
                    'updated_at': b.get('updated_at')
                })
        
        print(f"DEBUG get_businesses: Returning {len(businesses)} businesses for user: {[b['id'] for b in businesses]}")
        return jsonify(businesses)
    else:
        conn = get_db_connection()
        if business_ids:
            # Get only businesses user has access to
            placeholders = ','.join(['?'] * len(business_ids))
            query = f'SELECT id, name, created_at, updated_at FROM businesses WHERE id IN ({placeholders}) ORDER BY name'
            businesses = conn.execute(query, business_ids).fetchall()
        else:
            # User has no business access
            businesses = []
        conn.close()
        return jsonify([dict(b) for b in businesses])

@app.route('/api/businesses', methods=['POST'])
@require_auth
@require_user_access
def create_business():
    """Create a new business."""
    data = request.get_json()
    name = data.get('name')
    
    if not name:
        return jsonify({'error': 'Business name is required'}), 400
    
    if USE_COSMOS_DB:
        try:
            # Get next business_id
            # Note: cosmos_get_businesses() returns objects with 'id' field (aliased from business_id)
            businesses = cosmos_get_businesses()
            business_ids = []
            for b in businesses:
                # get_businesses() returns 'business_id as id', so check 'id' first, then 'business_id' as fallback
                bid = b.get('id') or b.get('business_id')
                if bid is not None:
                    try:
                        # Convert to int if it's a string like "business-1" or already an int
                        if isinstance(bid, str):
                            if bid.startswith('business-'):
                                bid = int(bid.replace('business-', ''))
                            else:
                                bid = int(bid)
                        else:
                            bid = int(bid)
                        business_ids.append(bid)
                    except (ValueError, TypeError):
                        continue
            
            next_id = max(business_ids, default=0) + 1
            
            business_doc = {
                'id': f'business-{next_id}',
                'type': 'business',
                'business_id': next_id,
                'name': name,
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }
            
            # Businesses container uses /id as partition key, so partition_key should be the document id
            created = create_item('businesses', business_doc, partition_key=business_doc['id'])
            return jsonify({
                'id': created.get('business_id') or created.get('id'),
                'name': created['name'],
                'created_at': created['created_at'],
                'updated_at': created['updated_at']
            }), 201
        except Exception as e:
            print(f"Error creating business: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': f'Error creating business: {str(e)}'}), 500
    else:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO businesses (name) VALUES (?)', (name,))
        business_id = cursor.lastrowid
        conn.commit()
        
        business = conn.execute('SELECT id, name, created_at, updated_at FROM businesses WHERE id = ?', (business_id,)).fetchone()
        conn.close()
        return jsonify(dict(business)), 201

@app.route('/api/businesses/<int:business_id>', methods=['GET'])
@require_auth
@require_user_access
def get_business(business_id):
    """Get a specific business."""
    if USE_COSMOS_DB:
        try:
            business = cosmos_get_business(business_id)
            if business is None:
                return jsonify({'error': 'Business not found'}), 404
            return jsonify({
                'id': business.get('business_id') or business.get('id'),
                'name': business['name'],
                'created_at': business.get('created_at'),
                'updated_at': business.get('updated_at')
            })
        except Exception as e:
            print(f"Error getting business {business_id}: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': f'Error retrieving business: {str(e)}'}), 500
    else:
        conn = get_db_connection()
        business = conn.execute('SELECT id, name, created_at, updated_at FROM businesses WHERE id = ?', (business_id,)).fetchone()
        conn.close()
        
        if business is None:
            return jsonify({'error': 'Business not found'}), 404
        
        return jsonify(dict(business))

@app.route('/api/businesses/<int:business_id>', methods=['PUT'])
@require_auth
@require_user_access
def update_business(business_id):
    """Update a business."""
    data = request.get_json()
    name = data.get('name')
    
    if USE_COSMOS_DB:
        try:
            business = cosmos_get_business(business_id)
            if business is None:
                return jsonify({'error': 'Business not found'}), 404
            
            # Ensure the business document has the correct id field for Cosmos DB
            # The id should be in format "business-{business_id}"
            if 'id' not in business:
                business['id'] = f"business-{business_id}"
            elif not business['id'].startswith('business-'):
                business['id'] = f"business-{business_id}"
            
            # Ensure business_id is set
            if 'business_id' not in business:
                business['business_id'] = business_id
            
            business['name'] = name
            business['updated_at'] = datetime.utcnow().isoformat()
            
            # For businesses container, partition key is the document id (e.g., "business-1")
            updated = update_item('businesses', business, partition_key=business['id'])
            return jsonify({
                'id': updated.get('business_id') or updated.get('id'),
                'name': updated['name'],
                'created_at': updated.get('created_at'),
                'updated_at': updated.get('updated_at')
            })
        except Exception as e:
            print(f"Error updating business: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': f'Error updating business: {str(e)}'}), 500
    else:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE businesses SET name = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
            (name, business_id)
        )
        
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({'error': 'Business not found'}), 404
        
        conn.commit()
        business = conn.execute('SELECT id, name, created_at, updated_at FROM businesses WHERE id = ?', (business_id,)).fetchone()
        conn.close()
        return jsonify(dict(business))

@app.route('/api/businesses/<int:business_id>', methods=['DELETE'])
@require_auth
@require_user_access
def delete_business(business_id):
    """Delete a business."""
    if USE_COSMOS_DB:
        business = cosmos_get_business(business_id)
        if business is None:
            return jsonify({'error': 'Business not found'}), 404
        
        # Note: In Cosmos DB, cascading deletes must be done manually
        # For now, just delete the business. Related data cleanup can be added later.
        # Businesses container uses /id as partition key
        delete_item('businesses', f'business-{business_id}', partition_key=f'business-{business_id}')
        return jsonify({'message': 'Business deleted successfully'}), 200
    else:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM businesses WHERE id = ?', (business_id,))
        
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({'error': 'Business not found'}), 404
        
        conn.commit()
        conn.close()
        return jsonify({'message': 'Business deleted successfully'}), 200

# ========== CHART OF ACCOUNTS ROUTES ==========

@app.route('/api/businesses/<int:business_id>/chart-of-accounts', methods=['GET'])
@require_auth
@require_user_access
def get_chart_of_accounts(business_id):
    """Get chart of accounts for a business."""
    if USE_COSMOS_DB:
        try:
            accounts = cosmos_get_chart_of_accounts(business_id)
            # Transform to match expected format
            result = []
            for acc in accounts:
                account_type = acc.get('account_type', {})
                result.append({
                    'id': acc.get('id') or acc.get('account_id'),
                    'business_id': business_id,
                    'account_code': acc.get('account_code'),
                    'account_name': acc.get('account_name'),
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
        except Exception as e:
            print(f"Error getting chart of accounts: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': f'Error retrieving chart of accounts: {str(e)}'}), 500
    else:
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

@app.route('/api/businesses/<int:business_id>/chart-of-accounts', methods=['POST'])
@require_auth
@require_user_access
def create_chart_of_account(business_id):
    """Create a new account in the chart of accounts."""
    data = request.get_json()
    print(f"DEBUG create_chart_of_account: Called for business_id={business_id}, data={data}", flush=True)
    
    account_code = data.get('account_code')
    account_name = data.get('account_name')
    account_type_id = data.get('account_type_id')
    description = data.get('description', '')
    parent_account_id = data.get('parent_account_id')
    
    print(f"DEBUG create_chart_of_account: account_type_id={account_type_id} (type: {type(account_type_id)})", flush=True)
    
    if not account_code or not account_name:
        return jsonify({'error': 'Account code and name are required'}), 400
    
    # Convert empty string to None for parent_account_id
    if parent_account_id == '' or parent_account_id is None:
        parent_account_id = None
    else:
        try:
            parent_account_id = int(parent_account_id)
        except (ValueError, TypeError):
            return jsonify({'error': 'Invalid parent account ID'}), 400
    
    if USE_COSMOS_DB:
        try:
            # Validate parent account exists and belongs to same business
            if parent_account_id:
                parent_account = get_chart_of_account(parent_account_id, business_id)
                if not parent_account:
                    return jsonify({'error': 'Parent account not found'}), 404
                if parent_account.get('business_id') != business_id:
                    return jsonify({'error': 'Parent account must belong to the same business'}), 400
            
            # Check if account code already exists
            existing = query_items(
                'chart_of_accounts',
                'SELECT * FROM c WHERE c.type = "chart_of_account" AND c.business_id = @business_id AND c.account_code = @account_code',
                [
                    {"name": "@business_id", "value": business_id},
                    {"name": "@account_code", "value": account_code}
                ],
                partition_key=str(business_id)
            )
            if existing:
                return jsonify({'error': 'Account code already exists for this business'}), 400
            
            # Get account type info if provided - MUST embed for P&L reports to work
            account_type_info = None
            if account_type_id:
                print(f"DEBUG create_chart_of_account: Attempting to fetch account_type for account_type_id={account_type_id} (type: {type(account_type_id)})", flush=True)
                try:
                    # Normalize account_type_id to int for query
                    account_type_id_int = int(account_type_id) if account_type_id else None
                    print(f"DEBUG create_chart_of_account: Normalized account_type_id to {account_type_id_int}", flush=True)
                    
                    # Try querying with account_type_id as the field name
                    account_types = query_items(
                        'account_types',
                        'SELECT * FROM c WHERE c.type = "account_type" AND c.account_type_id = @account_type_id',
                        [{"name": "@account_type_id", "value": account_type_id_int}],
                        partition_key=None
                    )
                    print(f"DEBUG create_chart_of_account: Query returned {len(account_types) if account_types else 0} account_types", flush=True)
                    
                    if not account_types or len(account_types) == 0:
                        # Try alternative query - maybe the field is just 'id'?
                        print(f"DEBUG create_chart_of_account: Trying alternative query with id field", flush=True)
                        account_types = query_items(
                            'account_types',
                            'SELECT * FROM c WHERE c.type = "account_type" AND c.id = @account_type_id',
                            [{"name": "@account_type_id", "value": account_type_id_int}],
                            partition_key=None
                        )
                        print(f"DEBUG create_chart_of_account: Alternative query returned {len(account_types) if account_types else 0} account_types", flush=True)
                    
                    # If still not found, try getting all and filtering
                    if not account_types or len(account_types) == 0:
                        print(f"DEBUG create_chart_of_account: Trying to get all account types and filter", flush=True)
                        all_account_types = query_items(
                            'account_types',
                            'SELECT * FROM c WHERE c.type = "account_type"',
                            [],
                            partition_key=None
                        )
                        print(f"DEBUG create_chart_of_account: Found {len(all_account_types) if all_account_types else 0} total account types", flush=True)
                        if all_account_types:
                            for at in all_account_types:
                                at_id = at.get('account_type_id') or at.get('id')
                                print(f"DEBUG create_chart_of_account: Checking account_type with id={at_id} (type: {type(at_id)})", flush=True)
                                if at_id == account_type_id_int or str(at_id) == str(account_type_id):
                                    account_types = [at]
                                    print(f"DEBUG create_chart_of_account: Found matching account_type!", flush=True)
                                    break
                    
                    if account_types and len(account_types) > 0:
                        at = account_types[0]
                        print(f"DEBUG create_chart_of_account: Account type document keys: {list(at.keys())}", flush=True)
                        print(f"DEBUG create_chart_of_account: Account type document: {at}", flush=True)
                        account_type_info = {
                            'id': at.get('account_type_id') or at.get('id'),
                            'code': at.get('code'),
                            'name': at.get('name'),
                            'category': at.get('category'),
                            'normal_balance': at.get('normal_balance')
                        }
                        print(f"DEBUG create_chart_of_account: Found account_type for account_type_id={account_type_id}: {account_type_info}", flush=True)
                    else:
                        print(f"WARNING create_chart_of_account: No account_type found for account_type_id={account_type_id} after trying all queries", flush=True)
                except Exception as e:
                    print(f"ERROR create_chart_of_account: Failed to fetch account_type for account_type_id={account_type_id}: {e}", flush=True)
                    import traceback
                    traceback.print_exc()
            else:
                print(f"WARNING create_chart_of_account: account_type_id is None or empty, skipping account_type embedding", flush=True)
            
            # Get next account_id
            existing_accounts = cosmos_get_chart_of_accounts(business_id)
            next_id = max([acc.get('id') or acc.get('account_id', 0) for acc in existing_accounts], default=0) + 1
            
            # Create account document with UUID for portability across NoSQL databases
            import uuid
            account_doc = {
                'id': str(uuid.uuid4()),  # Use UUID for document ID - portable across NoSQL databases
                'type': 'chart_of_account',
                'account_id': next_id,
                'business_id': business_id,
                'account_code': account_code,
                'account_name': account_name,
                'account_type_id': account_type_id,
                'description': description or '',
                'parent_account_id': parent_account_id,
                'is_active': True,
                'created_at': datetime.utcnow().isoformat()
            }
            
            # ALWAYS embed account_type if account_type_id is provided and we have the info
            if account_type_info:
                account_doc['account_type'] = account_type_info
                print(f"DEBUG create_chart_of_account: Embedding account_type in account_doc", flush=True)
            elif account_type_id:
                print(f"WARNING create_chart_of_account: account_type_id={account_type_id} provided but account_type_info is None - account_type will NOT be embedded!", flush=True)
            
            created = create_item('chart_of_accounts', account_doc, partition_key=str(business_id))
            
            # Verify account_type was saved
            if 'account_type' in created:
                print(f"DEBUG create_chart_of_account: account_type successfully embedded in created document", flush=True)
            elif account_type_id:
                print(f"WARNING create_chart_of_account: account_type was NOT saved in created document despite account_type_id={account_type_id}", flush=True)
            
            # Return in expected format
            result = {
                'id': created.get('account_id'),
                'business_id': created.get('business_id'),
                'account_code': created.get('account_code'),
                'account_name': created.get('account_name'),
                'description': created.get('description'),
                'parent_account_id': created.get('parent_account_id'),
                'is_active': created.get('is_active', True),
                'account_type_id': created.get('account_type_id'),
                'created_at': created.get('created_at')
            }
            
            if account_type_info:
                result['account_type_code'] = account_type_info['code']
                result['account_type_name'] = account_type_info['name']
                result['category'] = account_type_info['category']
                result['normal_balance'] = account_type_info['normal_balance']
            
            return jsonify(result), 201
        except Exception as e:
            print(f"Error creating chart of account: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': f'Error creating account: {str(e)}'}), 400
    else:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Validate parent account exists and belongs to same business
        if parent_account_id:
            parent_account = conn.execute(
                'SELECT id, business_id FROM chart_of_accounts WHERE id = ?',
                (parent_account_id,)
            ).fetchone()
            
            if not parent_account:
                conn.close()
                return jsonify({'error': 'Parent account not found'}), 404
            
            if parent_account['business_id'] != business_id:
                conn.close()
                return jsonify({'error': 'Parent account must belong to the same business'}), 400
        
        try:
            cursor.execute('''
                INSERT INTO chart_of_accounts 
                (business_id, account_type_id, account_code, account_name, description, parent_account_id)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (business_id, account_type_id, account_code, account_name, description, parent_account_id))
            
            account_id = cursor.lastrowid
            conn.commit()
            
            account = conn.execute('''
                SELECT coa.*, at.code as account_type_code, at.name as account_type_name, 
                       at.category, at.normal_balance
                FROM chart_of_accounts coa
                LEFT JOIN account_types at ON coa.account_type_id = at.id
                WHERE coa.id = ?
            ''', (account_id,)).fetchone()
            
            conn.close()
            return jsonify(dict(account)), 201
        except sqlite3.IntegrityError as e:
            conn.close()
            return jsonify({'error': 'Account code already exists for this business'}), 400

@app.route('/api/businesses/<int:business_id>/chart-of-accounts/<int:account_id>', methods=['PUT'])
@require_auth
@require_user_access
def update_chart_of_account(business_id, account_id):
    """Update an existing account in the chart of accounts."""
    data = request.get_json()
    
    if USE_COSMOS_DB:
        try:
            # Get existing account
            account = get_chart_of_account(account_id, business_id)
            if not account:
                return jsonify({'error': 'Account not found'}), 404
            
            # Use the ID from the query result - support both old format (chart-{id}) and new format (account-{business_id}-{id})
            # Don't try to fix/change existing IDs to maintain compatibility with older data
            if 'id' not in account:
                # Only construct if truly missing (shouldn't happen, but handle gracefully)
                account['id'] = f"account-{business_id}-{account_id}"
                print(f"DEBUG update_chart_of_account: WARNING - Account document missing 'id' field, constructed: {account['id']}", flush=True)
            else:
                print(f"DEBUG update_chart_of_account: Using existing account document id: {account.get('id')} (supports both chart-{account_id} and account-{business_id}-{account_id} formats)", flush=True)
            
            # Ensure business_id is set for partition key
            if 'business_id' not in account:
                account['business_id'] = business_id
                print(f"DEBUG update_chart_of_account: Set missing business_id to: {business_id}", flush=True)
            
            # Debug: Log account info
            print(f"DEBUG update_chart_of_account: Updating chart of account - id={account.get('id')}, account_id={account.get('account_id')}, business_id={account.get('business_id')}", flush=True)
            
            # Validate parent account if provided
            if 'parent_account_id' in data:
                parent_account_id = data['parent_account_id']
                if parent_account_id == '' or parent_account_id is None:
                    parent_account_id = None
                else:
                    try:
                        parent_account_id = int(parent_account_id)
                    except (ValueError, TypeError):
                        return jsonify({'error': 'Invalid parent account ID'}), 400
                
                if parent_account_id:
                    parent_account = get_chart_of_account(parent_account_id, business_id)
                    if not parent_account:
                        return jsonify({'error': 'Parent account not found'}), 404
                    if parent_account.get('business_id') != business_id:
                        return jsonify({'error': 'Parent account must belong to the same business'}), 400
                    if parent_account_id == account_id:
                        return jsonify({'error': 'Account cannot be its own parent'}), 400
                account['parent_account_id'] = parent_account_id
            
            # Update fields
            if 'account_code' in data:
                # Check if new code conflicts with existing
                if data['account_code'] != account.get('account_code'):
                    existing = query_items(
                        'chart_of_accounts',
                        'SELECT * FROM c WHERE c.type = "chart_of_account" AND c.business_id = @business_id AND c.account_code = @account_code AND c.account_id != @account_id',
                        [
                            {"name": "@business_id", "value": business_id},
                            {"name": "@account_code", "value": data['account_code']},
                            {"name": "@account_id", "value": account_id}
                        ],
                        partition_key=int(business_id)
                    )
                    if existing:
                        return jsonify({'error': 'Account code already exists for this business'}), 400
                account['account_code'] = data['account_code']
            
            if 'account_name' in data:
                account['account_name'] = data['account_name']
            
            if 'account_type_id' in data:
                account['account_type_id'] = data['account_type_id'] if data['account_type_id'] else None
                # Update account type info if provided - use same pattern as create_chart_of_account
                print(f"DEBUG update_chart_of_account: Updating account_type_id to {data['account_type_id']}", flush=True)
                if data['account_type_id']:
                    account_type_id_int = int(data['account_type_id']) if data['account_type_id'] else None
                    print(f"DEBUG update_chart_of_account: Looking for account_type with id={account_type_id_int}", flush=True)
                    # Try querying with id field first
                    account_types = query_items(
                        'account_types',
                        'SELECT * FROM c WHERE c.type = "account_type" AND c.id = @account_type_id',
                        [{"name": "@account_type_id", "value": account_type_id_int}],
                        partition_key=None
                    )
                    print(f"DEBUG update_chart_of_account: Query by id returned {len(account_types) if account_types else 0} results", flush=True)
                    # If not found, try alternative field names
                    if not account_types:
                        account_types = query_items(
                            'account_types',
                            'SELECT * FROM c WHERE c.type = "account_type"',
                            [],
                            partition_key=None
                        )
                        print(f"DEBUG update_chart_of_account: Query all returned {len(account_types) if account_types else 0} total account_types", flush=True)
                        # Filter by id in Python
                        account_types = [at for at in account_types if at.get('id') == account_type_id_int]
                        print(f"DEBUG update_chart_of_account: After filtering, found {len(account_types)} matching account_types", flush=True)
                    
                    if account_types:
                        at = account_types[0]
                        print(f"DEBUG update_chart_of_account: Found account_type: {at}", flush=True)
                        account['account_type'] = {
                            'id': at.get('id'),
                            'code': at.get('code'),
                            'name': at.get('name'),
                            'category': at.get('category'),
                            'normal_balance': at.get('normal_balance')
                        }
                        print(f"DEBUG update_chart_of_account: Set account['account_type'] = {account.get('account_type')}", flush=True)
                    else:
                        print(f"WARNING update_chart_of_account: Account type {account_type_id_int} not found", flush=True)
                else:
                    # If account_type_id is None/empty, remove account_type
                    account['account_type'] = None
                    print(f"DEBUG update_chart_of_account: Removed account_type (account_type_id is None/empty)", flush=True)
            
            if 'description' in data:
                account['description'] = data['description'] or ''
            
            if 'is_active' in data:
                account['is_active'] = bool(data['is_active'])
            
            account['updated_at'] = datetime.utcnow().isoformat()
            
            # Debug: Log what we're about to update
            print(f"DEBUG update_chart_of_account: About to update account. ID: {account.get('id')}, account_type_id: {account.get('account_type_id')}, account_type: {account.get('account_type')}", flush=True)
            
            # Update in Cosmos DB - use integer partition key to match document field type
            # For chart_of_accounts, partition key is /business_id which is an integer in documents
            updated = update_item('chart_of_accounts', account, partition_key=int(business_id))
            
            # Debug: Verify account_type was saved
            if 'account_type' in updated:
                print(f"DEBUG update_chart_of_account: account_type successfully saved: {updated.get('account_type')}", flush=True)
            else:
                print(f"WARNING update_chart_of_account: account_type was NOT saved in updated document! account_type_id={account.get('account_type_id')}", flush=True)
            
            # Return in expected format
            result = {
                'id': updated.get('account_id'),
                'business_id': updated.get('business_id'),
                'account_code': updated.get('account_code'),
                'account_name': updated.get('account_name'),
                'description': updated.get('description'),
                'parent_account_id': updated.get('parent_account_id'),
                'is_active': updated.get('is_active', True),
                'account_type_id': updated.get('account_type_id'),
                'created_at': updated.get('created_at'),
                'updated_at': updated.get('updated_at')
            }
            
            if 'account_type' in updated:
                at = updated['account_type']
                result['account_type_code'] = at.get('code')
                result['account_type_name'] = at.get('name')
                result['category'] = at.get('category')
                result['normal_balance'] = at.get('normal_balance')
            
            return jsonify(result)
        except Exception as e:
            print(f"Error updating chart of account: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': f'Error updating account: {str(e)}'}), 400
    else:
        conn = get_db_connection()
        
        # Verify account exists and belongs to business
        account = conn.execute(
            'SELECT * FROM chart_of_accounts WHERE id = ? AND business_id = ?',
            (account_id, business_id)
        ).fetchone()
        
        if not account:
            conn.close()
            return jsonify({'error': 'Account not found'}), 404
        
        # Build update query dynamically
        updates = []
        params = []
        
        if 'account_code' in data:
            updates.append('account_code = ?')
            params.append(data['account_code'])
        
        if 'account_name' in data:
            updates.append('account_name = ?')
            params.append(data['account_name'])
        
        if 'account_type_id' in data:
            updates.append('account_type_id = ?')
            params.append(data['account_type_id'] if data['account_type_id'] else None)
        
        if 'description' in data:
            updates.append('description = ?')
            params.append(data['description'] or '')
        
        if 'parent_account_id' in data:
            parent_account_id = data['parent_account_id']
            if parent_account_id == '' or parent_account_id is None:
                parent_account_id = None
            else:
                try:
                    parent_account_id = int(parent_account_id)
                except (ValueError, TypeError):
                    conn.close()
                    return jsonify({'error': 'Invalid parent account ID'}), 400
            
            # Validate parent account if provided
            if parent_account_id:
                parent_account = conn.execute(
                    'SELECT id, business_id FROM chart_of_accounts WHERE id = ?',
                    (parent_account_id,)
                ).fetchone()
                
                if not parent_account:
                    conn.close()
                    return jsonify({'error': 'Parent account not found'}), 404
                
                if parent_account['business_id'] != business_id:
                    conn.close()
                    return jsonify({'error': 'Parent account must belong to the same business'}), 400
                
                # Prevent circular reference (account cannot be its own parent)
                if parent_account_id == account_id:
                    conn.close()
                    return jsonify({'error': 'Account cannot be its own parent'}), 400
            
            updates.append('parent_account_id = ?')
            params.append(parent_account_id)
        
        if 'is_active' in data:
            updates.append('is_active = ?')
            params.append(1 if data['is_active'] else 0)
        
        if not updates:
            conn.close()
            return jsonify({'error': 'No fields to update'}), 400
        
        # Add account_id and business_id for WHERE clause
        params.append(account_id)
        params.append(business_id)
        
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                f'UPDATE chart_of_accounts SET {", ".join(updates)} WHERE id = ? AND business_id = ?',
                params
            )
            
            if cursor.rowcount == 0:
                conn.close()
                return jsonify({'error': 'Account not found or no changes made'}), 404
            
            conn.commit()
            
            # Fetch updated account
            account = conn.execute('''
                SELECT coa.*, at.code as account_type_code, at.name as account_type_name, 
                       at.category, at.normal_balance
                FROM chart_of_accounts coa
                LEFT JOIN account_types at ON coa.account_type_id = at.id
                WHERE coa.id = ?
            ''', (account_id,)).fetchone()
            
            conn.close()
            return jsonify(dict(account))
        except sqlite3.IntegrityError as e:
            conn.rollback()
            conn.close()
            return jsonify({'error': 'Account code already exists for this business'}), 400

@app.route('/api/businesses/<int:business_id>/chart-of-accounts/<int:account_id>', methods=['DELETE'])
@require_auth
@require_user_access
def delete_chart_of_account(business_id, account_id):
    """Delete an account from the chart of accounts."""
    print(f"DEBUG delete_chart_of_account: Called for business_id={business_id}, account_id={account_id}", flush=True)
    if USE_COSMOS_DB:
        try:
            from azure.cosmos import exceptions as cosmos_exceptions
            
            # Get the account to verify it exists and belongs to the business
            # Use the same approach as delete_transaction
            print(f"DEBUG delete_chart_of_account: Looking for account_id={account_id} (type: {type(account_id).__name__}), business_id={business_id} (type: {type(business_id).__name__})", flush=True)
            account = get_chart_of_account(account_id, business_id)
            
            if not account:
                print(f"DEBUG delete_chart_of_account: Account {account_id} not found for business {business_id}", flush=True)
                return jsonify({'error': 'Account not found'}), 404
            
            # Verify business_id matches
            acc_business_id = account.get('business_id')
            if acc_business_id and int(acc_business_id) != business_id:
                print(f"DEBUG delete_chart_of_account: Business ID mismatch - account has {acc_business_id}, requested {business_id}", flush=True)
                return jsonify({'error': 'Account does not belong to this business'}), 403
            
            # Get the actual document ID from the retrieved account
            # Document IDs are now UUIDs for portability
            actual_doc_id = account.get('id')
            if not actual_doc_id:
                # This should never happen, but if it does, we can't delete without an ID
                print(f"ERROR delete_chart_of_account: Account document missing 'id' field - cannot delete", flush=True)
                return jsonify({'error': 'Account document missing ID field'}), 500
            
            # For chart_of_accounts container, partition key path is /business_id
            # The document shows business_id as an integer (3), so use integer partition key
            # Use the business_id from the account document to ensure exact match
            acc_business_id = account.get('business_id')
            if acc_business_id:
                partition_key_value = int(acc_business_id)
            else:
                partition_key_value = business_id
            
            # Ensure business_id from account matches
            if acc_business_id and int(acc_business_id) != business_id:
                print(f"DEBUG delete_chart_of_account: Business ID mismatch - account has {acc_business_id}, requested {business_id}", flush=True)
                return jsonify({'error': 'Account does not belong to this business'}), 403
            
            print(f"DEBUG delete_chart_of_account: Account document actual 'id' field: {actual_doc_id}", flush=True)
            print(f"DEBUG delete_chart_of_account: Using document ID: {actual_doc_id}, partition_key: {partition_key_value} (type: {type(partition_key_value).__name__})", flush=True)
            print(f"DEBUG delete_chart_of_account: Account document fields: id={account.get('id')}, account_id={account.get('account_id')}, business_id={account.get('business_id')} (type: {type(account.get('business_id')).__name__})", flush=True)
            
            # Check if account has child accounts
            child_accounts = query_items(
                'chart_of_accounts',
                'SELECT * FROM c WHERE c.type = "chart_of_account" AND c.business_id = @business_id AND c.parent_account_id = @account_id',
                [
                    {"name": "@business_id", "value": business_id},
                    {"name": "@account_id", "value": account_id}
                ],
                partition_key=business_id  # Try integer partition key for query too
            )
            
            if child_accounts:
                return jsonify({
                    'error': 'Cannot delete account with child accounts',
                    'message': f'This account has {len(child_accounts)} child account(s). Please delete or reassign child accounts first.'
                }), 400
            
            # Delete the account - use integer partition key to match document field type
            # For chart_of_accounts container, partition key is /business_id (integer)
            from database_cosmos import delete_item
            delete_item('chart_of_accounts', actual_doc_id, partition_key=int(business_id))
            
            print(f"DEBUG delete_chart_of_account: Successfully deleted account {account_id}", flush=True)
            
            return jsonify({'message': 'Account deleted successfully'}), 200
        except cosmos_exceptions.CosmosResourceNotFoundError as e:
            print(f"ERROR delete_chart_of_account: Account document not found in Cosmos DB: {e}", flush=True)
            return jsonify({'error': 'Account not found in database'}), 404
        except cosmos_exceptions.CosmosAccessConditionFailedError as e:
            print(f"ERROR delete_chart_of_account: Access condition failed (concurrency conflict): {e}", flush=True)
            return jsonify({'error': 'Account was modified by another operation. Please try again.'}), 409
        except Exception as e:
            print(f"ERROR delete_chart_of_account: Unexpected error: {e}", flush=True)
            import traceback
            error_trace = traceback.format_exc()
            print(f"Full traceback:\n{error_trace}", flush=True)
            return jsonify({'error': f'Error deleting account: {str(e)}'}), 500
    else:
        conn = get_db_connection()
        
        # Verify account exists and belongs to business
        account = conn.execute(
            'SELECT * FROM chart_of_accounts WHERE id = ? AND business_id = ?',
            (account_id, business_id)
        ).fetchone()
        
        if not account:
            conn.close()
            return jsonify({'error': 'Account not found'}), 404
        
        # Check if account has child accounts
        child_accounts = conn.execute(
            'SELECT id FROM chart_of_accounts WHERE parent_account_id = ?',
            (account_id,)
        ).fetchall()
        
        if child_accounts:
            conn.close()
            return jsonify({
                'error': 'Cannot delete account with child accounts',
                'message': f'This account has {len(child_accounts)} child account(s). Please delete or reassign child accounts first.'
            }), 400
        
        # Delete the account
        conn.execute('DELETE FROM chart_of_accounts WHERE id = ? AND business_id = ?', (account_id, business_id))
        conn.commit()
        conn.close()
        
        return jsonify({'message': 'Account deleted successfully'}), 200

@app.route('/api/account-types', methods=['GET'])
def get_account_types():
    """Get all account types."""
    if USE_COSMOS_DB:
        try:
            account_types = query_items(
                'account_types',
                'SELECT c.account_type_id as id, c.code, c.name, c.category, c.normal_balance, c.created_at FROM c WHERE c.type = "account_type"',
                partition_key=None  # Cross-partition query
            )
            # Sort in Python to avoid composite index requirement
            account_types.sort(key=lambda x: (x.get('category', ''), x.get('name', '')))
            return jsonify(account_types)
        except Exception as e:
            print(f"Error getting account types: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': f'Error retrieving account types: {str(e)}'}), 500
    else:
        conn = get_db_connection()
        types = conn.execute('SELECT * FROM account_types ORDER BY category, name').fetchall()
        conn.close()
        return jsonify([dict(t) for t in types])

# ========== BANK ACCOUNTS ROUTES ==========

@app.route('/api/businesses/<int:business_id>/bank-accounts', methods=['GET'])
@require_auth
@require_user_access
def get_bank_accounts(business_id):
    """Get all bank accounts for a business."""
    if USE_COSMOS_DB:
        try:
            accounts = query_items(
                'bank_accounts',
                'SELECT c.bank_account_id as id, c.business_id, c.account_name, c.account_number, c.bank_name, c.routing_number, c.opening_balance, c.current_balance, c.account_code, c.is_active, c.created_at FROM c WHERE c.type = "bank_account" AND c.business_id = @business_id ORDER BY c.account_name',
                [{"name": "@business_id", "value": business_id}],
                partition_key=str(business_id)
            )
            return jsonify(accounts)
        except Exception as e:
            print(f"Error getting bank accounts: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': f'Error retrieving bank accounts: {str(e)}'}), 500
    else:
        conn = get_db_connection()
        accounts = conn.execute(
            'SELECT * FROM bank_accounts WHERE business_id = ? ORDER BY account_name',
            (business_id,)
        ).fetchall()
        conn.close()
        return jsonify([dict(a) for a in accounts])

@app.route('/api/businesses/<int:business_id>/bank-accounts', methods=['POST'])
@require_auth
@require_user_access
def create_bank_account(business_id):
    """Create a new bank account."""
    data = request.get_json()
    
    if USE_COSMOS_DB:
        try:
            # Get next account_id
            existing = query_items(
                'bank_accounts',
                'SELECT VALUE MAX(c.bank_account_id) FROM c WHERE c.type = "bank_account" AND c.business_id = @business_id',
                [{"name": "@business_id", "value": business_id}],
                partition_key=str(business_id)
            )
            next_id = (existing[0] if existing and existing[0] is not None else 0) + 1
            
            opening_balance = float(data.get('opening_balance', 0) or 0)
            account_doc = {
                'id': f'bank-{next_id}',
                'type': 'bank_account',
                'bank_account_id': next_id,
                'business_id': business_id,
                'account_name': data.get('account_name'),
                'account_number': data.get('account_number'),
                'bank_name': data.get('bank_name'),
                'routing_number': data.get('routing_number'),
                'opening_balance': opening_balance,
                'current_balance': opening_balance,
                'account_code': data.get('account_code'),
                'is_active': True,
                'created_at': datetime.utcnow().isoformat()
            }
            
            created = create_item('bank_accounts', account_doc, partition_key=str(business_id))
            return jsonify({
                'id': created.get('bank_account_id'),
                'business_id': created.get('business_id'),
                'account_name': created.get('account_name'),
                'account_number': created.get('account_number'),
                'bank_name': created.get('bank_name'),
                'routing_number': created.get('routing_number'),
                'opening_balance': created.get('opening_balance'),
                'current_balance': created.get('current_balance'),
                'account_code': created.get('account_code'),
                'is_active': created.get('is_active', True),
                'created_at': created.get('created_at')
            }), 201
        except Exception as e:
            print(f"Error creating bank account: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': f'Error creating bank account: {str(e)}'}), 400
    else:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO bank_accounts 
            (business_id, account_name, account_number, bank_name, routing_number, opening_balance, current_balance, account_code)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            business_id,
            data.get('account_name'),
            data.get('account_number'),
            data.get('bank_name'),
            data.get('routing_number'),
            data.get('opening_balance', 0),
            data.get('opening_balance', 0),
            data.get('account_code')
        ))
        
        account_id = cursor.lastrowid
        conn.commit()
        account = conn.execute('SELECT * FROM bank_accounts WHERE id = ?', (account_id,)).fetchone()
        conn.close()
        return jsonify(dict(account)), 201

# ========== CREDIT CARD ACCOUNTS ROUTES ==========

@app.route('/api/businesses/<int:business_id>/credit-card-accounts', methods=['GET'])
@require_auth
@require_user_access
def get_credit_card_accounts(business_id):
    """Get all credit card accounts for a business."""
    if USE_COSMOS_DB:
        try:
            accounts = query_items(
                'credit_card_accounts',
                'SELECT c.credit_card_account_id as id, c.business_id, c.account_name, c.card_number_last4, c.issuer, c.credit_limit, c.current_balance, c.account_code, c.is_active, c.created_at FROM c WHERE c.type = "credit_card_account" AND c.business_id = @business_id ORDER BY c.account_name',
                [{"name": "@business_id", "value": business_id}],
                partition_key=str(business_id)
            )
            return jsonify(accounts)
        except Exception as e:
            print(f"Error getting credit card accounts: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': f'Error retrieving credit card accounts: {str(e)}'}), 500
    else:
        conn = get_db_connection()
        accounts = conn.execute(
            'SELECT * FROM credit_card_accounts WHERE business_id = ? ORDER BY account_name',
            (business_id,)
        ).fetchall()
        conn.close()
        return jsonify([dict(a) for a in accounts])

@app.route('/api/businesses/<int:business_id>/credit-card-accounts', methods=['POST'])
@require_auth
@require_user_access
def create_credit_card_account(business_id):
    """Create a new credit card account."""
    data = request.get_json()
    
    if USE_COSMOS_DB:
        try:
            # Get next account_id
            existing = query_items(
                'credit_card_accounts',
                'SELECT VALUE MAX(c.credit_card_account_id) FROM c WHERE c.type = "credit_card_account" AND c.business_id = @business_id',
                [{"name": "@business_id", "value": business_id}],
                partition_key=str(business_id)
            )
            next_id = (existing[0] if existing and existing[0] is not None else 0) + 1
            
            account_doc = {
                'id': f'credit-card-{next_id}',
                'type': 'credit_card_account',
                'credit_card_account_id': next_id,
                'business_id': business_id,
                'account_name': data.get('account_name'),
                'card_number_last4': data.get('card_number_last4'),
                'issuer': data.get('issuer'),
                'credit_limit': float(data.get('credit_limit', 0) or 0),
                'current_balance': float(data.get('current_balance', 0) or 0),
                'account_code': data.get('account_code'),
                'is_active': True,
                'created_at': datetime.utcnow().isoformat()
            }
            
            created = create_item('credit_card_accounts', account_doc, partition_key=str(business_id))
            return jsonify({
                'id': created.get('credit_card_account_id'),
                'business_id': created.get('business_id'),
                'account_name': created.get('account_name'),
                'card_number_last4': created.get('card_number_last4'),
                'issuer': created.get('issuer'),
                'credit_limit': created.get('credit_limit'),
                'current_balance': created.get('current_balance'),
                'account_code': created.get('account_code'),
                'is_active': created.get('is_active', True),
                'created_at': created.get('created_at')
            }), 201
        except Exception as e:
            print(f"Error creating credit card account: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': f'Error creating credit card account: {str(e)}'}), 400
    else:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO credit_card_accounts 
            (business_id, account_name, card_number_last4, issuer, credit_limit, current_balance, account_code)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            business_id,
            data.get('account_name'),
            data.get('card_number_last4'),
            data.get('issuer'),
            data.get('credit_limit', 0),
            data.get('current_balance', 0),
            data.get('account_code')
        ))
        
        account_id = cursor.lastrowid
        conn.commit()
        account = conn.execute('SELECT * FROM credit_card_accounts WHERE id = ?', (account_id,)).fetchone()
        conn.close()
        return jsonify(dict(account)), 201

# ========== LOAN ACCOUNTS ROUTES ==========

@app.route('/api/businesses/<int:business_id>/loan-accounts', methods=['GET'])
@require_auth
@require_user_access
def get_loan_accounts(business_id):
    """Get all loan accounts for a business."""
    if USE_COSMOS_DB:
        try:
            accounts = query_items(
                'loan_accounts',
                'SELECT c.loan_account_id as id, c.business_id, c.account_name, c.lender_name, c.loan_number, c.principal_amount, c.current_balance, c.interest_rate, c.account_code, c.is_active, c.created_at FROM c WHERE c.type = "loan_account" AND c.business_id = @business_id ORDER BY c.account_name',
                [{"name": "@business_id", "value": business_id}],
                partition_key=str(business_id)
            )
            return jsonify(accounts)
        except Exception as e:
            print(f"Error getting loan accounts: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': f'Error retrieving loan accounts: {str(e)}'}), 500
    else:
        conn = get_db_connection()
        accounts = conn.execute(
            'SELECT * FROM loan_accounts WHERE business_id = ? ORDER BY account_name',
            (business_id,)
        ).fetchall()
        conn.close()
        return jsonify([dict(a) for a in accounts])

@app.route('/api/businesses/<int:business_id>/loan-accounts', methods=['POST'])
@require_auth
@require_user_access
def create_loan_account(business_id):
    """Create a new loan account."""
    data = request.get_json()
    
    if USE_COSMOS_DB:
        try:
            # Get next account_id
            existing = query_items(
                'loan_accounts',
                'SELECT VALUE MAX(c.loan_account_id) FROM c WHERE c.type = "loan_account" AND c.business_id = @business_id',
                [{"name": "@business_id", "value": business_id}],
                partition_key=str(business_id)
            )
            next_id = (existing[0] if existing and existing[0] is not None else 0) + 1
            
            account_doc = {
                'id': f'loan-{next_id}',
                'type': 'loan_account',
                'loan_account_id': next_id,
                'business_id': business_id,
                'account_name': data.get('account_name'),
                'lender_name': data.get('lender_name'),
                'loan_number': data.get('loan_number'),
                'principal_amount': float(data.get('principal_amount', 0) or 0),
                'current_balance': float(data.get('current_balance', 0) or 0),
                'interest_rate': float(data.get('interest_rate', 0) or 0),
                'account_code': data.get('account_code'),
                'is_active': True,
                'created_at': datetime.utcnow().isoformat()
            }
            
            created = create_item('loan_accounts', account_doc, partition_key=str(business_id))
            return jsonify({
                'id': created.get('loan_account_id'),
                'business_id': created.get('business_id'),
                'account_name': created.get('account_name'),
                'lender_name': created.get('lender_name'),
                'loan_number': created.get('loan_number'),
                'principal_amount': created.get('principal_amount'),
                'current_balance': created.get('current_balance'),
                'interest_rate': created.get('interest_rate'),
                'account_code': created.get('account_code'),
                'is_active': created.get('is_active', True),
                'created_at': created.get('created_at')
            }), 201
        except Exception as e:
            print(f"Error creating loan account: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': f'Error creating loan account: {str(e)}'}), 400
    else:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO loan_accounts 
            (business_id, account_name, lender_name, loan_number, principal_amount, current_balance, interest_rate, account_code)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            business_id,
            data.get('account_name'),
            data.get('lender_name'),
            data.get('loan_number'),
            data.get('principal_amount', 0),
            data.get('current_balance', 0),
            data.get('interest_rate', 0),
            data.get('account_code')
        ))
        
        account_id = cursor.lastrowid
        conn.commit()
        account = conn.execute('SELECT * FROM loan_accounts WHERE id = ?', (account_id,)).fetchone()
        conn.close()
        return jsonify(dict(account)), 201

# ========== TRANSACTION ROUTES ==========

@app.route('/api/businesses/<int:business_id>/transactions', methods=['GET'])
@require_auth
@require_user_access
def get_transactions(business_id):
    """Get all transactions for a business."""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    account_id = request.args.get('account_id', type=int)
    
    if USE_COSMOS_DB:
        try:
            transactions = cosmos_get_transactions(
                business_id,
                start_date=start_date,
                end_date=end_date,
                account_id=account_id
            )
            
            # Transform to match expected format
            result = []
            for txn in transactions:
                try:
                    # Use transaction_id as id for frontend compatibility
                    txn_id = txn.get('transaction_id') or txn.get('id')
                    # If id is in format "transaction-{id}", extract the numeric part
                    if isinstance(txn_id, str) and txn_id.startswith('transaction-'):
                        txn_id = int(txn_id.replace('transaction-', ''))
                    
                    txn_dict = {
                        'id': txn_id,
                        'business_id': txn.get('business_id', business_id),
                        'transaction_date': txn.get('transaction_date'),
                        'description': txn.get('description'),
                        'reference_number': txn.get('reference_number'),
                        'transaction_type': txn.get('transaction_type'),
                        'amount': float(txn.get('amount', 0) or 0),
                        'created_at': txn.get('created_at'),
                        'lines': []
                    }
                    
                    # Transform embedded lines
                    for line in txn.get('lines', []):
                        chart_of_account_id = line.get('chart_of_account_id')
                        # Debug: Log the raw chart_of_account_id value
                        if txn_dict['id'] in [1299, 1300, 1301]:  # Only log for the transactions we just updated
                            print(f"DEBUG GET: Transaction {txn_dict['id']} line chart_of_account_id: {chart_of_account_id} (type: {type(chart_of_account_id).__name__})")
                        
                        # Ensure chart_of_account_id is an integer (not a string like 'account-2-148')
                        if isinstance(chart_of_account_id, str) and chart_of_account_id.startswith('account-'):
                            # Extract numeric account_id from format 'account-{business_id}-{account_id}'
                            parts = chart_of_account_id.split('-')
                            if len(parts) >= 3:
                                try:
                                    chart_of_account_id = int(parts[2])
                                    if txn_dict['id'] in [1299, 1300, 1301]:
                                        print(f"DEBUG GET: Converted {parts} to {chart_of_account_id}")
                                except (ValueError, IndexError):
                                    pass  # Keep original value if parsing fails
                        
                        txn_dict['lines'].append({
                            'id': line.get('transaction_line_id') or line.get('id'),
                            'transaction_id': txn_dict['id'],
                            'chart_of_account_id': chart_of_account_id,
                            'debit_amount': float(line.get('debit_amount', 0) or 0),
                            'credit_amount': float(line.get('credit_amount', 0) or 0),
                            'account_code': line.get('account_code'),
                            'account_name': line.get('account_name')
                        })
                    
                    # Debug: Log the final lines for updated transactions
                    if txn_dict['id'] in [1299, 1300, 1301]:
                        print(f"DEBUG GET: Transaction {txn_dict['id']} final lines chart_of_account_ids: {[l['chart_of_account_id'] for l in txn_dict['lines']]}")
                    
                    # Filter by description if needed
                    description_filter = request.args.get('description')
                    if not description_filter or description_filter.lower() in (txn_dict.get('description') or '').lower():
                        result.append(txn_dict)
                except Exception as e:
                    print(f"Error processing transaction: {e}")
                    print(f"Transaction data: {txn}")
                    import traceback
                    traceback.print_exc()
                    continue
            
            return jsonify(result)
        except Exception as e:
            print(f"Error getting transactions for business {business_id}: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': f'Error retrieving transactions: {str(e)}'}), 500
    else:
        conn = get_db_connection()
        
        # If filtering by account, we need to join with transaction_lines
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
        
        description_filter = request.args.get('description')
        if description_filter:
            query += ' AND description LIKE ?'
            params.append(f'%{description_filter}%')
        
        query += ' ORDER BY transaction_date DESC, id DESC'
        
        transactions = conn.execute(query, params).fetchall()
        
        # Get transaction lines for each transaction
        result = []
        for txn in transactions:
            txn_dict = dict(txn)
            lines = conn.execute('''
                SELECT tl.*, coa.account_code, coa.account_name
                FROM transaction_lines tl
                JOIN chart_of_accounts coa ON tl.chart_of_account_id = coa.id
                WHERE tl.transaction_id = ?
            ''', (txn_dict['id'],)).fetchall()
            txn_dict['lines'] = [dict(l) for l in lines]
            result.append(txn_dict)
        
        conn.close()
        return jsonify(result)

@app.route('/api/businesses/<int:business_id>/transactions', methods=['POST'])
@require_auth
@require_user_access
def create_transaction(business_id):
    """Create a new transaction with double-entry bookkeeping."""
    data = request.get_json()
    
    transaction_date = data.get('transaction_date')
    description = data.get('description', '')
    reference_number = data.get('reference_number')
    lines = data.get('lines', [])
    
    if not transaction_date:
        return jsonify({'error': 'Transaction date is required'}), 400
    
    if not lines or len(lines) < 2:
        return jsonify({'error': 'At least two transaction lines are required'}), 400
    
    # Validate double-entry: debits must equal credits
    total_debits = sum(float(line.get('debit_amount', 0) or 0) for line in lines)
    total_credits = sum(float(line.get('credit_amount', 0) or 0) for line in lines)
    
    if abs(total_debits - total_credits) > 0.01:
        return jsonify({'error': f'Debits ({total_debits}) must equal credits ({total_credits})'}), 400
    
    if USE_COSMOS_DB:
        try:
            # Get next transaction_id
            existing = query_items(
                'transactions',
                'SELECT VALUE MAX(c.transaction_id) FROM c WHERE c.type = "transaction" AND c.business_id = @business_id',
                [{"name": "@business_id", "value": business_id}],
                partition_key=str(business_id)
            )
            next_id = (existing[0] if existing and existing[0] is not None else 0) + 1
            
            # Get account info for lines
            transformed_lines = []
            for idx, line in enumerate(lines):
                account_id = line.get('chart_of_account_id')
                if account_id:
                    # Get account info
                    account = get_chart_of_account(account_id, business_id)
                    if account:
                        transformed_lines.append({
                            'id': f'line-{next_id}-{idx}',
                            'transaction_line_id': idx + 1,  # Line number within transaction
                            'chart_of_account_id': account_id,
                            'debit_amount': float(line.get('debit_amount', 0) or 0),
                            'credit_amount': float(line.get('credit_amount', 0) or 0),
                            'account_code': account.get('account_code'),
                            'account_name': account.get('account_name')
                        })
                    else:
                        return jsonify({'error': f'Account {account_id} not found'}), 400
                else:
                    return jsonify({'error': 'All lines must have a chart_of_account_id'}), 400
            
            # Create transaction document with embedded lines
            transaction_doc = {
                'id': f'transaction-{next_id}',
                'type': 'transaction',
                'transaction_id': next_id,
                'business_id': business_id,
                'transaction_date': transaction_date,
                'description': description,
                'reference_number': reference_number,
                'transaction_type': data.get('transaction_type', 'ADJUSTMENT'),
                'amount': total_debits,
                'created_at': datetime.utcnow().isoformat(),
                'lines': transformed_lines
            }
            
            created = create_item('transactions', transaction_doc, partition_key=str(business_id))
            
            # Return in expected format
            result = {
                'id': created.get('transaction_id'),
                'business_id': created.get('business_id'),
                'transaction_date': created.get('transaction_date'),
                'description': created.get('description'),
                'reference_number': created.get('reference_number'),
                'transaction_type': created.get('transaction_type'),
                'amount': created.get('amount'),
                'created_at': created.get('created_at'),
                'lines': []
            }
            
            # Transform lines to expected format
            for line in created.get('lines', []):
                result['lines'].append({
                    'id': line.get('transaction_line_id'),
                    'transaction_id': created.get('transaction_id'),
                    'chart_of_account_id': line.get('chart_of_account_id'),
                    'debit_amount': line.get('debit_amount'),
                    'credit_amount': line.get('credit_amount'),
                    'account_code': line.get('account_code'),
                    'account_name': line.get('account_name')
                })
            
            return jsonify(result), 201
        except Exception as e:
            print(f"Error creating transaction: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': f'Error creating transaction: {str(e)}'}), 400
    else:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Create transaction
            cursor.execute('''
                INSERT INTO transactions 
                (business_id, transaction_date, description, reference_number, transaction_type, amount)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                business_id,
                transaction_date,
                description,
                reference_number,
                data.get('transaction_type', 'ADJUSTMENT'),
                total_debits
            ))
            
            transaction_id = cursor.lastrowid
            
            # Create transaction lines
            for line in lines:
                cursor.execute('''
                    INSERT INTO transaction_lines 
                    (transaction_id, chart_of_account_id, debit_amount, credit_amount)
                    VALUES (?, ?, ?, ?)
                ''', (
                    transaction_id,
                    line['chart_of_account_id'],
                    line.get('debit_amount', 0),
                    line.get('credit_amount', 0)
                ))
            
            conn.commit()
            
            # Fetch the complete transaction
            transaction = conn.execute('SELECT * FROM transactions WHERE id = ?', (transaction_id,)).fetchone()
            transaction_lines = conn.execute('''
                SELECT tl.*, coa.account_code, coa.account_name
                FROM transaction_lines tl
                JOIN chart_of_accounts coa ON tl.chart_of_account_id = coa.id
                WHERE tl.transaction_id = ?
            ''', (transaction_id,)).fetchall()
            
            result = dict(transaction)
            result['lines'] = [dict(l) for l in transaction_lines]
            
            conn.close()
            return jsonify(result), 201
        except Exception as e:
            conn.rollback()
            conn.close()
            return jsonify({'error': str(e)}), 400

@app.route('/api/businesses/<int:business_id>/transactions/<int:transaction_id>', methods=['PUT'])
@require_auth
@require_user_access
def update_transaction(business_id, transaction_id):
    """Update an existing transaction."""
    data = request.get_json()
    
    transaction_date = data.get('transaction_date')
    description = data.get('description', '')
    reference_number = data.get('reference_number')
    lines = data.get('lines', [])
    
    if not transaction_date:
        return jsonify({'error': 'Transaction date is required'}), 400
    
    if not lines or len(lines) < 2:
        return jsonify({'error': 'At least two transaction lines are required'}), 400
    
    # Validate double-entry: debits must equal credits
    total_debits = sum(float(line.get('debit_amount', 0) or 0) for line in lines)
    total_credits = sum(float(line.get('credit_amount', 0) or 0) for line in lines)
    
    if abs(total_debits - total_credits) > 0.01:
        return jsonify({'error': f'Debits ({total_debits}) must equal credits ({total_credits})'}), 400
    
    if USE_COSMOS_DB:
        try:
            from database_cosmos import get_transaction, get_chart_of_account, update_item
            
            # Get existing transaction
            transaction = get_transaction(transaction_id, business_id)
            if not transaction:
                return jsonify({'error': 'Transaction not found'}), 404
            
            # Ensure the transaction document has the correct id field
            if 'id' not in transaction:
                transaction['id'] = f"transaction-{transaction_id}"
            elif not transaction['id'].startswith('transaction-'):
                transaction['id'] = f"transaction-{transaction_id}"
            
            # Ensure business_id is set
            if 'business_id' not in transaction:
                transaction['business_id'] = business_id
            
            # Get account info for lines and transform them
            transformed_lines = []
            for idx, line in enumerate(lines):
                account_id = line.get('chart_of_account_id')
                if account_id:
                    # Get account info
                    account = get_chart_of_account(account_id, business_id)
                    if account:
                        transformed_lines.append({
                            'id': f'line-{transaction_id}-{idx}',
                            'transaction_line_id': idx + 1,  # Line number within transaction
                            'chart_of_account_id': int(account_id),  # Ensure it's an integer
                            'debit_amount': float(line.get('debit_amount', 0) or 0),
                            'credit_amount': float(line.get('credit_amount', 0) or 0),
                            'account_code': account.get('account_code'),
                            'account_name': account.get('account_name')
                        })
                    else:
                        return jsonify({'error': f'Account {account_id} not found'}), 400
                else:
                    return jsonify({'error': 'All lines must have a chart_of_account_id'}), 400
            
            # Update transaction document
            transaction['transaction_date'] = transaction_date
            transaction['description'] = description
            transaction['reference_number'] = reference_number
            transaction['transaction_type'] = data.get('transaction_type', transaction.get('transaction_type', 'ADJUSTMENT'))
            transaction['amount'] = total_debits
            transaction['lines'] = transformed_lines
            transaction['updated_at'] = datetime.utcnow().isoformat()
            
            # Update in Cosmos DB
            updated = update_item('transactions', transaction, partition_key=str(business_id))
            
            # Return in expected format
            result = {
                'id': updated.get('transaction_id'),
                'business_id': updated.get('business_id'),
                'transaction_date': updated.get('transaction_date'),
                'description': updated.get('description'),
                'reference_number': updated.get('reference_number'),
                'transaction_type': updated.get('transaction_type'),
                'amount': updated.get('amount'),
                'created_at': updated.get('created_at'),
                'updated_at': updated.get('updated_at'),
                'lines': []
            }
            
            # Transform lines to expected format
            for line in updated.get('lines', []):
                result['lines'].append({
                    'id': line.get('transaction_line_id'),
                    'transaction_id': updated.get('transaction_id'),
                    'chart_of_account_id': line.get('chart_of_account_id'),
                    'debit_amount': line.get('debit_amount'),
                    'credit_amount': line.get('credit_amount'),
                    'account_code': line.get('account_code'),
                    'account_name': line.get('account_name')
                })
            
            return jsonify(result)
        except Exception as e:
            print(f"Error updating transaction: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': f'Error updating transaction: {str(e)}'}), 400
    else:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Verify transaction exists and belongs to business
            transaction = conn.execute(
                'SELECT * FROM transactions WHERE id = ? AND business_id = ?',
                (transaction_id, business_id)
            ).fetchone()
            
            if not transaction:
                conn.close()
                return jsonify({'error': 'Transaction not found'}), 404
            
            # Update transaction
            cursor.execute('''
                UPDATE transactions 
                SET transaction_date = ?, description = ?, reference_number = ?, 
                    transaction_type = ?, amount = ?
                WHERE id = ? AND business_id = ?
            ''', (
                transaction_date,
                description,
                reference_number,
                data.get('transaction_type', transaction['transaction_type']),
                total_debits,
                transaction_id,
                business_id
            ))
            
            # Delete existing lines
            cursor.execute('DELETE FROM transaction_lines WHERE transaction_id = ?', (transaction_id,))
            
            # Create new transaction lines
            for line in lines:
                cursor.execute('''
                    INSERT INTO transaction_lines 
                    (transaction_id, chart_of_account_id, debit_amount, credit_amount)
                    VALUES (?, ?, ?, ?)
                ''', (
                    transaction_id,
                    line['chart_of_account_id'],
                    line.get('debit_amount', 0),
                    line.get('credit_amount', 0)
                ))
            
            conn.commit()
            
            # Fetch the complete transaction
            transaction = conn.execute('SELECT * FROM transactions WHERE id = ?', (transaction_id,)).fetchone()
            transaction_lines = conn.execute('''
                SELECT tl.*, coa.account_code, coa.account_name
                FROM transaction_lines tl
                JOIN chart_of_accounts coa ON tl.chart_of_account_id = coa.id
                WHERE tl.transaction_id = ?
            ''', (transaction_id,)).fetchall()
            
            result = dict(transaction)
            result['lines'] = [dict(l) for l in transaction_lines]
            
            conn.close()
            return jsonify(result)
        except Exception as e:
            conn.rollback()
            conn.close()
            return jsonify({'error': str(e)}), 400

@app.route('/api/businesses/<int:business_id>/transactions/<int:transaction_id>', methods=['DELETE'])
@require_auth
@require_user_access
def delete_transaction(business_id, transaction_id):
    """Delete a transaction."""
    if USE_COSMOS_DB:
        try:
            from azure.cosmos import exceptions as cosmos_exceptions
            
            # Get existing transaction to verify it exists and belongs to business
            print(f"DEBUG delete_transaction: Looking for transaction_id={transaction_id} (type: {type(transaction_id).__name__}), business_id={business_id} (type: {type(business_id).__name__})")
            transaction = get_transaction(transaction_id, business_id)
            
            # If not found, try a direct query as fallback
            if not transaction:
                print(f"DEBUG delete_transaction: get_transaction returned None, trying direct query...")
                try:
                    direct_results = query_items(
                        'transactions',
                        'SELECT * FROM c WHERE c.type = "transaction" AND c.transaction_id = @transaction_id AND c.business_id = @business_id',
                        [
                            {"name": "@transaction_id", "value": transaction_id},
                            {"name": "@business_id", "value": business_id}
                        ],
                        partition_key=int(business_id)
                    )
                    print(f"DEBUG delete_transaction: Direct query returned {len(direct_results)} results")
                    if direct_results:
                        transaction = direct_results[0]
                        print(f"DEBUG delete_transaction: Found transaction via direct query, id={transaction.get('id')}, transaction_id={transaction.get('transaction_id')}")
                    else:
                        # Try querying all transactions for this business to see what exists
                        all_txns = query_items(
                            'transactions',
                            'SELECT c.transaction_id, c.id, c.business_id FROM c WHERE c.type = "transaction" AND c.business_id = @business_id',
                            [{"name": "@business_id", "value": business_id}],
                            partition_key=business_id  # Use integer partition key
                        )
                        print(f"DEBUG delete_transaction: Found {len(all_txns)} total transactions for business {business_id}")
                        if all_txns:
                            sample_ids = [f"id={t.get('id')}, transaction_id={t.get('transaction_id')}" for t in all_txns[:5]]
                            print(f"DEBUG delete_transaction: Sample transaction IDs: {sample_ids}")
                except Exception as query_error:
                    print(f"DEBUG delete_transaction: Error in fallback query: {query_error}")
            
            if not transaction:
                print(f"DEBUG delete_transaction: Transaction {transaction_id} not found for business {business_id}")
                return jsonify({'error': 'Transaction not found'}), 404
            
            # Verify business_id matches
            txn_business_id = transaction.get('business_id')
            if txn_business_id and int(txn_business_id) != business_id:
                print(f"DEBUG delete_transaction: Business ID mismatch - transaction has {txn_business_id}, requested {business_id}")
                return jsonify({'error': 'Transaction does not belong to this business'}), 403
            
            # Get the actual document ID from the retrieved transaction
            # The 'id' field in the document should match the Cosmos DB document ID
            actual_doc_id = transaction.get('id')
            if not actual_doc_id:
                # Fallback: construct ID from transaction_id if id field is missing
                actual_doc_id = f"transaction-{transaction_id}"
                print(f"DEBUG delete_transaction: Warning - transaction document missing 'id' field, constructing: {actual_doc_id}")
            
            # For transactions container, partition key path is /business_id
            # Use integer partition key since document has integer business_id (same fix as chart_of_accounts)
            txn_business_id = transaction.get('business_id')
            if txn_business_id:
                partition_key_value = int(txn_business_id)
            else:
                partition_key_value = business_id
            
            # Ensure business_id from transaction matches
            if txn_business_id and int(txn_business_id) != business_id:
                print(f"DEBUG delete_transaction: Business ID mismatch - transaction has {txn_business_id}, requested {business_id}", flush=True)
                return jsonify({'error': 'Transaction does not belong to this business'}), 403
            
            print(f"DEBUG delete_transaction: Transaction document actual 'id' field: {actual_doc_id}", flush=True)
            print(f"DEBUG delete_transaction: Using document ID: {actual_doc_id}, partition_key: {partition_key_value} (type: {type(partition_key_value).__name__})", flush=True)
            print(f"DEBUG delete_transaction: Transaction document fields: id={transaction.get('id')}, transaction_id={transaction.get('transaction_id')}, business_id={transaction.get('business_id')} (type: {type(transaction.get('business_id')).__name__})", flush=True)
            
            # Delete the transaction (lines are embedded, so they'll be deleted too)
            # For transactions container, partition key is /business_id (integer)
            from database_cosmos import delete_item
            delete_item('transactions', actual_doc_id, partition_key=int(business_id))
            
            print(f"DEBUG delete_transaction: Successfully deleted transaction {transaction_id}")
            return jsonify({'message': 'Transaction deleted successfully'}), 200
        except cosmos_exceptions.CosmosResourceNotFoundError as e:
            print(f"ERROR delete_transaction: Transaction document not found in Cosmos DB: {e}")
            return jsonify({'error': 'Transaction not found in database'}), 404
        except cosmos_exceptions.CosmosAccessConditionFailedError as e:
            print(f"ERROR delete_transaction: Access condition failed (concurrency conflict): {e}")
            return jsonify({'error': 'Transaction was modified by another operation. Please try again.'}), 409
        except Exception as e:
            print(f"ERROR delete_transaction: Unexpected error: {e}")
            import traceback
            error_trace = traceback.format_exc()
            print(f"Full traceback:\n{error_trace}")
            return jsonify({'error': f'Error deleting transaction: {str(e)}'}), 500
    else:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Verify transaction exists and belongs to business
            transaction = conn.execute(
                'SELECT * FROM transactions WHERE id = ? AND business_id = ?',
                (transaction_id, business_id)
            ).fetchone()
            
            if not transaction:
                conn.close()
                return jsonify({'error': 'Transaction not found'}), 404
            
            # Delete transaction lines first (CASCADE should handle this, but being explicit)
            cursor.execute('DELETE FROM transaction_lines WHERE transaction_id = ?', (transaction_id,))
            
            # Delete transaction
            cursor.execute('DELETE FROM transactions WHERE id = ? AND business_id = ?', (transaction_id, business_id))
            
            if cursor.rowcount == 0:
                conn.rollback()
                conn.close()
                return jsonify({'error': 'Transaction not found'}), 404
            
            conn.commit()
            conn.close()
            return jsonify({'message': 'Transaction deleted successfully'}), 200
        except Exception as e:
            conn.rollback()
            conn.close()
            return jsonify({'error': f'Error deleting transaction: {str(e)}'}), 500

@app.route('/api/businesses/<int:business_id>/transactions/bulk-update', methods=['PUT'])
@require_auth
@require_user_access
def bulk_update_transactions(business_id):
    """Bulk update transaction lines - assign chart of account to existing transaction lines."""
    data = request.get_json()
    
    transaction_ids = data.get('transaction_ids', [])
    chart_of_account_id = data.get('chart_of_account_id')
    line_filter = data.get('line_filter', 'ALL')  # 'ALL', 'DEBIT_ONLY', 'CREDIT_ONLY', 'FIRST_LINE'
    
    if not transaction_ids:
        return jsonify({'error': 'No transaction IDs provided'}), 400
    
    if not chart_of_account_id:
        return jsonify({'error': 'Chart of account ID is required'}), 400
    
    if USE_COSMOS_DB:
        try:
            from database_cosmos import get_chart_of_account, get_transaction, update_item
            
            # Verify chart of account exists and belongs to business
            chart_account = get_chart_of_account(chart_of_account_id, business_id)
            if not chart_account:
                return jsonify({'error': 'Chart of account not found or does not belong to this business'}), 404
            
            # Get account type info
            account_type = chart_account.get('account_type', {})
            if not account_type:
                return jsonify({'error': 'Chart of account type not found'}), 400
            
            account_category = account_type.get('category')
            normal_balance = account_type.get('normal_balance')
            
            # Debug: Log account info with full structure
            print(f"DEBUG: Bulk update - account_id={chart_of_account_id}")
            print(f"DEBUG: Account name: {chart_account.get('account_name')}, code: {chart_account.get('account_code')}")
            print(f"DEBUG: Account type structure: {account_type}")
            print(f"DEBUG: Category: {account_category}, Normal balance: {normal_balance}, Line filter: {line_filter}")
            
            # Update transaction lines based on filter
            updated_count = 0
            lines_updated = 0
            errors = []
            
            for txn_id in transaction_ids:
                # Get transaction with embedded lines
                transaction = get_transaction(txn_id, business_id)
                if not transaction:
                    errors.append(f'Transaction {txn_id}: Not found or does not belong to this business')
                    continue
                
                # Debug: Print transaction keys to see what we got
                print(f"DEBUG: Transaction {txn_id} keys: {list(transaction.keys())}")
                print(f"DEBUG: Transaction {txn_id} id: {transaction.get('id')}, transaction_id: {transaction.get('transaction_id')}")
                
                # Ensure the transaction document has the correct id field for Cosmos DB
                # The id should be in format "transaction-{transaction_id}"
                # Cosmos DB SELECT * should return the id field, but let's ensure it's correct
                if 'id' not in transaction:
                    # If id is missing, construct it from transaction_id
                    transaction['id'] = f"transaction-{transaction.get('transaction_id') or txn_id}"
                    print(f"DEBUG: Set missing id to: {transaction['id']}")
                elif not transaction['id'].startswith('transaction-'):
                    # If id exists but is in wrong format, fix it
                    transaction['id'] = f"transaction-{transaction.get('transaction_id') or txn_id}"
                    print(f"DEBUG: Fixed id format to: {transaction['id']}")
                
                # Ensure business_id is set for partition key
                if 'business_id' not in transaction:
                    transaction['business_id'] = business_id
                    print(f"DEBUG: Set missing business_id to: {business_id}")
                
                lines = transaction.get('lines', [])
                if not lines or len(lines) < 2:
                    print(f"DEBUG: Transaction {txn_id} has less than 2 lines, skipping")
                    continue
                
                # Debug: Show all lines in transaction
                print(f"DEBUG: Transaction {txn_id} has {len(lines)} lines:")
                for idx, line in enumerate(lines):
                    print(f"  Line {idx}: transaction_line_id={line.get('transaction_line_id')}, "
                          f"account_id={line.get('chart_of_account_id')}, "
                          f"debit={line.get('debit_amount')}, credit={line.get('credit_amount')}")
                
                # Determine which line(s) to update based on account category and filter
                lines_to_update = []
                if line_filter == 'ALL':
                    # For ALL: Only update lines that match the account's normal balance
                    # Don't update if both lines would end up with the same account
                    for line in lines:
                        # Normalize account_id for comparison (handle both int and string formats)
                        line_account_id = line.get('chart_of_account_id')
                        if isinstance(line_account_id, str) and line_account_id.startswith('account-'):
                            # Parse string format like "account-2-148" to integer 148
                            parts = line_account_id.split('-')
                            if len(parts) >= 3:
                                try:
                                    line_account_id = int(parts[2])
                                except ValueError:
                                    pass
                        
                        # Check if this would create duplicate accounts
                        other_lines = [l for l in lines if l.get('transaction_line_id') != line.get('transaction_line_id')]
                        would_be_duplicate = any(
                            (l.get('chart_of_account_id') == chart_of_account_id) or
                            (lambda acc_id: (
                                isinstance(acc_id, str) and 
                                acc_id.startswith('account-') and 
                                len(acc_id.split('-')) >= 3 and
                                int(acc_id.split('-')[2]) == chart_of_account_id
                            ) if acc_id else False)(l.get('chart_of_account_id'))
                            for l in other_lines
                        )
                        
                        if would_be_duplicate:
                            print(f"DEBUG: Skipped line (would create duplicate): transaction_line_id={line.get('transaction_line_id')}")
                            continue  # Skip to avoid duplicate
                        
                        # Only update if it matches the account's normal balance
                        if account_category in ('REVENUE', 'EXPENSE'):
                            if account_category == 'REVENUE' and line.get('credit_amount', 0) > 0:
                                lines_to_update.append(line)
                                print(f"DEBUG: Selected line (REVENUE/credit): transaction_line_id={line.get('transaction_line_id')}, credit={line.get('credit_amount')}")
                            elif account_category == 'EXPENSE' and line.get('debit_amount', 0) > 0:
                                lines_to_update.append(line)
                                print(f"DEBUG: Selected line (EXPENSE/debit): transaction_line_id={line.get('transaction_line_id')}, debit={line.get('debit_amount')}")
                            else:
                                print(f"DEBUG: Skipped line (doesn't match category): transaction_line_id={line.get('transaction_line_id')}, debit={line.get('debit_amount')}, credit={line.get('credit_amount')}")
                        else:
                            # For asset/liability accounts, update based on normal balance
                            if normal_balance == 'DEBIT' and line.get('debit_amount', 0) > 0:
                                lines_to_update.append(line)
                                print(f"DEBUG: Selected line (DEBIT normal balance): transaction_line_id={line.get('transaction_line_id')}, debit={line.get('debit_amount')}")
                            elif normal_balance == 'CREDIT' and line.get('credit_amount', 0) > 0:
                                lines_to_update.append(line)
                                print(f"DEBUG: Selected line (CREDIT normal balance): transaction_line_id={line.get('transaction_line_id')}, credit={line.get('credit_amount')}")
                            else:
                                print(f"DEBUG: Skipped line (doesn't match normal balance): transaction_line_id={line.get('transaction_line_id')}, debit={line.get('debit_amount')}, credit={line.get('credit_amount')}, normal_balance={normal_balance}")
                elif line_filter == 'DEBIT_ONLY':
                    lines_to_update = [l for l in lines if l.get('debit_amount', 0) > 0]
                elif line_filter == 'CREDIT_ONLY':
                    lines_to_update = [l for l in lines if l.get('credit_amount', 0) > 0]
                elif line_filter == 'FIRST_LINE':
                    lines_to_update = [lines[0]] if lines else []
                
                # Prevent updating if it would create duplicate accounts
                if lines_to_update:
                    other_line_ids = [l.get('transaction_line_id') for l in lines 
                                    if l.get('transaction_line_id') not in [lu.get('transaction_line_id') for lu in lines_to_update]]
                    other_lines = [l for l in lines if l.get('transaction_line_id') in other_line_ids]
                    
                    # Check if any other line already has this account
                    has_duplicate = any(
                        l.get('chart_of_account_id') == chart_of_account_id 
                        for l in other_lines
                    )
                    
                    if has_duplicate:
                        errors.append(f'Transaction {txn_id}: Cannot update - would create duplicate accounts')
                        continue
                
                # Update each selected line in the transaction document
                if lines_to_update:
                    # Get the transaction's lines array
                    transaction_lines = transaction.get('lines', [])
                    
                    # Create a set of line identifiers to update for quick lookup
                    # We'll match by transaction_line_id if available, otherwise by amounts
                    lines_to_update_identifiers = set()
                    for line in lines_to_update:
                        line_id = line.get('transaction_line_id')
                        if line_id:
                            lines_to_update_identifiers.add(line_id)
                        else:
                            # Use tuple of amounts as identifier
                            debit = float(line.get('debit_amount', 0) or 0)
                            credit = float(line.get('credit_amount', 0) or 0)
                            lines_to_update_identifiers.add((debit, credit))
                    
                    # Debug: Print what we're looking for
                    print(f"DEBUG: Transaction {txn_id} lines_to_update_identifiers: {lines_to_update_identifiers}")
                    print(f"DEBUG: Transaction {txn_id} transaction_lines identifiers: {[(l.get('transaction_line_id'), (float(l.get('debit_amount', 0) or 0), float(l.get('credit_amount', 0) or 0))) for l in transaction_lines]}")
                    
                    # Update the lines in the transaction document
                    # Create a new list with updated lines to ensure we're not using stale references
                    updated_lines = []
                    for idx, line in enumerate(transaction_lines):
                        # Check if this line should be updated
                        line_id = line.get('transaction_line_id')
                        debit = float(line.get('debit_amount', 0) or 0)
                        credit = float(line.get('credit_amount', 0) or 0)
                        line_identifier = line_id if line_id else (debit, credit)
                        
                        # Create a copy of the line
                        updated_line = dict(line)
                        
                        # Debug: Check if this line matches
                        matches = line_identifier in lines_to_update_identifiers
                        print(f"DEBUG: Transaction {txn_id} line {idx}: identifier={line_identifier}, matches={matches}")
                        
                        if matches:
                            # Update the chart_of_account_id - ensure it's an integer
                            old_value = updated_line.get('chart_of_account_id')
                            updated_line['chart_of_account_id'] = int(chart_of_account_id)
                            # Also update account_code and account_name for display in transaction list
                            updated_line['account_code'] = chart_account.get('account_code')
                            updated_line['account_name'] = chart_account.get('account_name')
                            print(f"DEBUG: Updated line {idx} in transaction {txn_id}: {old_value} -> {chart_of_account_id}")
                            print(f"DEBUG: Updated account_code: {updated_line.get('account_code')}, account_name: {updated_line.get('account_name')}")
                            lines_updated += 1
                        
                        updated_lines.append(updated_line)
                    
                    # Explicitly set the updated lines array back on the transaction
                    transaction['lines'] = updated_lines
                    
                    # Debug: Print updated transaction before save
                    print(f"DEBUG: Updated transaction {txn_id} with {lines_updated} lines")
                    print(f"DEBUG: Transaction lines before save: {[(l.get('chart_of_account_id'), l.get('debit_amount'), l.get('credit_amount')) for l in transaction.get('lines', [])]}")
                    
                    # Save updated transaction back to Cosmos DB
                    # The id and business_id should already be set above
                    try:
                        # Create a clean transaction document with our updated lines
                        # Make sure we're using the updated lines array, not the original
                        # Use the updated_lines we created above, not transaction_lines
                        transaction_to_save = {
                            'id': transaction['id'],
                            'type': transaction.get('type', 'transaction'),
                            'transaction_id': transaction.get('transaction_id'),
                            'business_id': transaction.get('business_id'),
                            'transaction_date': transaction.get('transaction_date'),
                            'description': transaction.get('description'),
                            'reference_number': transaction.get('reference_number'),
                            'transaction_type': transaction.get('transaction_type'),
                            'amount': transaction.get('amount'),
                            'created_at': transaction.get('created_at'),
                            'lines': updated_lines  # Use the updated_lines array we created
                        }
                        # Preserve _etag and _ts if they exist (for optimistic concurrency)
                        if '_etag' in transaction:
                            transaction_to_save['_etag'] = transaction['_etag']
                        if '_ts' in transaction:
                            transaction_to_save['_ts'] = transaction['_ts']
                        
                        # Debug: Verify what we're about to save
                        print(f"DEBUG: About to save transaction {txn_id} with lines: {[(l.get('chart_of_account_id'), l.get('debit_amount'), l.get('credit_amount')) for l in transaction_to_save.get('lines', [])]}")
                        
                        updated_transaction = update_item('transactions', transaction_to_save, partition_key=str(business_id))
                        print(f"DEBUG: Transaction saved successfully, id: {updated_transaction.get('id')}")
                        # Verify the saved transaction has the updated lines
                        saved_lines = updated_transaction.get('lines', [])
                        print(f"DEBUG: Saved transaction lines: {[(l.get('chart_of_account_id'), l.get('debit_amount'), l.get('credit_amount')) for l in saved_lines]}")
                        updated_count += 1
                    except Exception as e:
                        print(f"DEBUG: Error saving transaction {txn_id}: {e}")
                        errors.append(f'Transaction {txn_id}: Error saving - {str(e)}')
                        import traceback
                        traceback.print_exc()
            
            response_message = f'Successfully updated {lines_updated} transaction line(s) in {updated_count} transaction(s)'
            if errors:
                response_message += f'. {len(errors)} transaction(s) skipped to prevent duplicate accounts.'
            
            return jsonify({
                'updated_count': updated_count,
                'lines_updated': lines_updated,
                'errors': errors[:10],  # Limit errors to first 10
                'message': response_message
            }), 200
        except Exception as e:
            print(f"Error in bulk_update_transactions (Cosmos DB): {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': f'Error updating transactions: {str(e)}'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Verify chart of account exists and belongs to business
    chart_account = conn.execute(
        'SELECT id FROM chart_of_accounts WHERE id = ? AND business_id = ?',
        (chart_of_account_id, business_id)
    ).fetchone()
    
    if not chart_account:
        conn.close()
        return jsonify({'error': 'Chart of account not found or does not belong to this business'}), 404
    
    # Verify all transactions belong to the business
    placeholders = ','.join(['?'] * len(transaction_ids))
    existing_transactions = conn.execute(
        f'SELECT id FROM transactions WHERE id IN ({placeholders}) AND business_id = ?',
        transaction_ids + [business_id]
    ).fetchall()
    
    if len(existing_transactions) != len(transaction_ids):
        conn.close()
        return jsonify({'error': 'Some transactions not found or do not belong to this business'}), 400
    
    # Get the account type to determine which line should be updated
    chart_account_info = conn.execute('''
        SELECT at.category, at.normal_balance
        FROM chart_of_accounts coa
        JOIN account_types at ON coa.account_type_id = at.id
        WHERE coa.id = ?
    ''', (chart_of_account_id,)).fetchone()
    
    if not chart_account_info:
        conn.close()
        return jsonify({'error': 'Chart of account type not found'}), 400
    
    account_category = chart_account_info['category']
    normal_balance = chart_account_info['normal_balance']
    
    # Update transaction lines based on filter
    updated_count = 0
    lines_updated = 0
    errors = []
    
    try:
        for txn_id in transaction_ids:
            # Get existing transaction lines with account info
            lines = conn.execute('''
                SELECT tl.*, coa.id as current_account_id, at.category as current_category
                FROM transaction_lines tl
                JOIN chart_of_accounts coa ON tl.chart_of_account_id = coa.id
                JOIN account_types at ON coa.account_type_id = at.id
                WHERE tl.transaction_id = ?
                ORDER BY tl.id
            ''', (txn_id,)).fetchall()
            
            if not lines or len(lines) < 2:
                continue
            
            # Determine which line(s) to update based on account category and filter
            lines_to_update = []
            if line_filter == 'ALL':
                # For ALL: Only update lines that match the account's normal balance
                # Don't update if both lines would end up with the same account
                for line in lines:
                    # Check if this would create duplicate accounts
                    other_lines = [l for l in lines if l['id'] != line['id']]
                    would_be_duplicate = any(
                        l['current_account_id'] == chart_of_account_id 
                        for l in other_lines
                    )
                    
                    if would_be_duplicate:
                        continue  # Skip to avoid duplicate
                    
                    # Only update if it matches the account's normal balance
                    if account_category in ('REVENUE', 'EXPENSE'):
                        if account_category == 'REVENUE' and line['credit_amount'] > 0:
                            lines_to_update.append(line)
                        elif account_category == 'EXPENSE' and line['debit_amount'] > 0:
                            lines_to_update.append(line)
                    else:
                        # For asset/liability accounts, update based on normal balance
                        if normal_balance == 'DEBIT' and line['debit_amount'] > 0:
                            lines_to_update.append(line)
                        elif normal_balance == 'CREDIT' and line['credit_amount'] > 0:
                            lines_to_update.append(line)
            elif line_filter == 'DEBIT_ONLY':
                lines_to_update = [l for l in lines if l['debit_amount'] > 0]
            elif line_filter == 'CREDIT_ONLY':
                lines_to_update = [l for l in lines if l['credit_amount'] > 0]
            elif line_filter == 'FIRST_LINE':
                lines_to_update = [lines[0]] if lines else []
            
            # Prevent updating if it would create duplicate accounts
            if lines_to_update:
                other_line_ids = [l['id'] for l in lines if l['id'] not in [lu['id'] for lu in lines_to_update]]
                other_lines = [l for l in lines if l['id'] in other_line_ids]
                
                # Check if any other line already has this account
                has_duplicate = any(
                    l['current_account_id'] == chart_of_account_id 
                    for l in other_lines
                )
                
                if has_duplicate:
                    errors.append(f'Transaction {txn_id}: Cannot update - would create duplicate accounts')
                    continue
            
            # Update each selected line
            for line in lines_to_update:
                cursor.execute('''
                    UPDATE transaction_lines 
                    SET chart_of_account_id = ?
                    WHERE id = ?
                ''', (chart_of_account_id, line['id']))
                lines_updated += 1
            
            if lines_to_update:
                updated_count += 1
        
        conn.commit()
        
        response_message = f'Successfully updated {lines_updated} transaction line(s) in {updated_count} transaction(s)'
        if errors:
            response_message += f'. {len(errors)} transaction(s) skipped to prevent duplicate accounts.'
        
        conn.close()
        return jsonify({
            'updated_count': updated_count,
            'lines_updated': lines_updated,
            'errors': errors[:10],  # Limit errors to first 10
            'message': response_message
        }), 200
    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({'error': str(e)}), 400

# ========== TRANSACTION TYPE MAPPINGS ROUTES ==========

@app.route('/api/transaction-type-mappings', methods=['GET'])
def get_transaction_type_mappings():
    """Get all transaction type mappings."""
    if USE_COSMOS_DB:
        try:
            mappings = query_items(
                'transaction_type_mappings',
                'SELECT c.mapping_id as id, c.csv_type, c.internal_type, c.direction, c.description, c.created_at FROM c WHERE c.type = "transaction_type_mapping"',
                partition_key=None
            )
            # Sort in Python
            mappings.sort(key=lambda x: x.get('csv_type', ''))
            return jsonify(mappings)
        except Exception as e:
            print(f"Error getting transaction type mappings: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': f'Error retrieving mappings: {str(e)}'}), 500
    else:
        conn = get_db_connection()
        mappings = conn.execute(
            'SELECT * FROM transaction_type_mappings ORDER BY csv_type'
        ).fetchall()
        conn.close()
        return jsonify([dict(m) for m in mappings])

@app.route('/api/transaction-type-mappings', methods=['POST'])
def create_transaction_type_mapping():
    """Create a new transaction type mapping."""
    data = request.get_json()
    
    csv_type = data.get('csv_type', '').upper().strip()
    internal_type = data.get('internal_type')
    direction = data.get('direction')
    description = data.get('description', '')
    
    if not csv_type or not internal_type or not direction:
        return jsonify({'error': 'csv_type, internal_type, and direction are required'}), 400
    
    if USE_COSMOS_DB:
        try:
            # Check if mapping already exists
            existing = query_items(
                'transaction_type_mappings',
                'SELECT * FROM c WHERE c.type = "transaction_type_mapping" AND c.csv_type = @csv_type',
                [{"name": "@csv_type", "value": csv_type}],
                partition_key=None
            )
            if existing:
                return jsonify({'error': 'Transaction type mapping already exists'}), 400
            
            # Get next mapping_id
            existing_mappings = query_items(
                'transaction_type_mappings',
                'SELECT VALUE MAX(c.mapping_id) FROM c WHERE c.type = "transaction_type_mapping"',
                partition_key=None
            )
            next_id = (existing_mappings[0] if existing_mappings and existing_mappings[0] is not None else 0) + 1
            
            mapping_doc = {
                'id': f'mapping-{next_id}',
                'type': 'transaction_type_mapping',
                'mapping_id': next_id,
                'csv_type': csv_type,
                'internal_type': internal_type,
                'direction': direction,
                'description': description,
                'created_at': datetime.utcnow().isoformat()
            }
            
            created = create_item('transaction_type_mappings', mapping_doc, partition_key=str(next_id))
            return jsonify({
                'id': created.get('mapping_id'),
                'csv_type': created.get('csv_type'),
                'internal_type': created.get('internal_type'),
                'direction': created.get('direction'),
                'description': created.get('description'),
                'created_at': created.get('created_at')
            }), 201
        except Exception as e:
            print(f"Error creating transaction type mapping: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': f'Error creating mapping: {str(e)}'}), 400
    else:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO transaction_type_mappings (csv_type, internal_type, direction, description)
                VALUES (?, ?, ?, ?)
            ''', (csv_type, internal_type, direction, description))
            
            mapping_id = cursor.lastrowid
            conn.commit()
            
            mapping = conn.execute(
                'SELECT * FROM transaction_type_mappings WHERE id = ?',
                (mapping_id,)
            ).fetchone()
            
            conn.close()
            return jsonify(dict(mapping)), 201
        except sqlite3.IntegrityError:
            conn.close()
            return jsonify({'error': 'Transaction type mapping already exists'}), 400

@app.route('/api/transaction-type-mappings/<int:mapping_id>', methods=['PUT'])
def update_transaction_type_mapping(mapping_id):
    """Update a transaction type mapping."""
    data = request.get_json()
    
    if USE_COSMOS_DB:
        try:
            # Get existing mapping
            mappings = query_items(
                'transaction_type_mappings',
                'SELECT * FROM c WHERE c.type = "transaction_type_mapping" AND c.mapping_id = @mapping_id',
                [{"name": "@mapping_id", "value": mapping_id}],
                partition_key=str(mapping_id)
            )
            if not mappings:
                return jsonify({'error': 'Transaction type mapping not found'}), 404
            
            mapping = mappings[0]
            
            # Update fields
            if 'internal_type' in data:
                mapping['internal_type'] = data['internal_type']
            if 'direction' in data:
                mapping['direction'] = data['direction']
            if 'description' in data:
                mapping['description'] = data['description']
            
            if not any(k in data for k in ['internal_type', 'direction', 'description']):
                return jsonify({'error': 'No fields to update'}), 400
            
            mapping['updated_at'] = datetime.utcnow().isoformat()
            
            # Update in Cosmos DB
            updated = update_item('transaction_type_mappings', mapping, partition_key=str(mapping_id))
            return jsonify({
                'id': updated.get('mapping_id'),
                'csv_type': updated.get('csv_type'),
                'internal_type': updated.get('internal_type'),
                'direction': updated.get('direction'),
                'description': updated.get('description'),
                'created_at': updated.get('created_at'),
                'updated_at': updated.get('updated_at')
            })
        except Exception as e:
            print(f"Error updating transaction type mapping: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': f'Error updating mapping: {str(e)}'}), 400
    else:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        updates = []
        params = []
        
        if 'internal_type' in data:
            updates.append('internal_type = ?')
            params.append(data['internal_type'])
        
        if 'direction' in data:
            updates.append('direction = ?')
            params.append(data['direction'])
        
        if 'description' in data:
            updates.append('description = ?')
            params.append(data['description'])
        
        if not updates:
            conn.close()
            return jsonify({'error': 'No fields to update'}), 400
        
        params.append(mapping_id)
        
        cursor.execute(
            f'UPDATE transaction_type_mappings SET {", ".join(updates)} WHERE id = ?',
            params
        )
        
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({'error': 'Transaction type mapping not found'}), 404
        
        conn.commit()
        mapping = conn.execute(
            'SELECT * FROM transaction_type_mappings WHERE id = ?',
            (mapping_id,)
        ).fetchone()
        
        conn.close()
        return jsonify(dict(mapping))

@app.route('/api/transaction-type-mappings/<int:mapping_id>', methods=['DELETE'])
def delete_transaction_type_mapping(mapping_id):
    """Delete a transaction type mapping."""
    if USE_COSMOS_DB:
        try:
            # Get existing mapping to find the document ID
            mappings = query_items(
                'transaction_type_mappings',
                'SELECT * FROM c WHERE c.type = "transaction_type_mapping" AND c.mapping_id = @mapping_id',
                [{"name": "@mapping_id", "value": mapping_id}],
                partition_key=str(mapping_id)
            )
            if not mappings:
                return jsonify({'error': 'Transaction type mapping not found'}), 404
            
            mapping = mappings[0]
            delete_item('transaction_type_mappings', mapping['id'], partition_key=str(mapping_id))
            return jsonify({'message': 'Transaction type mapping deleted successfully'}), 200
        except Exception as e:
            print(f"Error deleting transaction type mapping: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': f'Error deleting mapping: {str(e)}'}), 400
    else:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM transaction_type_mappings WHERE id = ?', (mapping_id,))
        
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({'error': 'Transaction type mapping not found'}), 404
        
        conn.commit()
        conn.close()
        return jsonify({'message': 'Transaction type mapping deleted successfully'}), 200

# ========== CSV IMPORT ROUTES ==========

@app.route('/api/businesses/<int:business_id>/transactions/import-csv', methods=['POST'])
@require_auth
@require_user_access
def import_transactions_csv(business_id):
    """Import transactions from CSV file."""
    import sys
    try:
        sys.stdout.flush()
        print(f"DEBUG import_transactions_csv: Received request for business_id={business_id}", flush=True)
        print(f"DEBUG import_transactions_csv: Files in request: {list(request.files.keys())}", flush=True)
        print(f"DEBUG import_transactions_csv: Form data keys: {list(request.form.keys())}", flush=True)
        print(f"DEBUG import_transactions_csv: Form data values: {[(k, request.form.get(k)) for k in request.form.keys()]}", flush=True)
        sys.stdout.flush()
        # Check if file is present
        if 'file' not in request.files:
            error_msg = 'No file uploaded'
            print(f"DEBUG import_transactions_csv: {error_msg}", flush=True)
            return jsonify({'error': error_msg}), 400
        
        file = request.files['file']
        if file.filename == '':
            error_msg = 'No file selected'
            print(f"DEBUG import_transactions_csv: {error_msg}", flush=True)
            return jsonify({'error': error_msg}), 400
        
        # Get additional parameters
        bank_account_id = request.form.get('bank_account_id')
        expense_account_id = request.form.get('expense_account_id')
        revenue_account_id = request.form.get('revenue_account_id')
        
        print(f"DEBUG import_transactions_csv: bank_account_id={bank_account_id}, expense_account_id={expense_account_id}, revenue_account_id={revenue_account_id}", flush=True)
        
        if not bank_account_id:
            error_msg = 'Bank account is required'
            print(f"DEBUG import_transactions_csv: {error_msg}", flush=True)
            return jsonify({'error': error_msg}), 400
        
        # Read and parse CSV
        # Use proper CSV dialect to handle quoted fields with embedded commas
        # Read file content - Flask file objects can be read directly
        try:
            # Try reading as text first (Flask may have already decoded it)
            if hasattr(file, 'read'):
                file_content = file.read()
                if isinstance(file_content, bytes):
                    # If it's bytes, decode it
                    try:
                        file_content = file_content.decode("UTF-8")
                    except UnicodeDecodeError:
                        try:
                            file_content = file_content.decode("UTF-8-sig")  # Handle BOM
                        except UnicodeDecodeError:
                            file_content = file_content.decode("latin-1")  # Fallback
            else:
                # Fallback to stream reading
                file_content = file.stream.read().decode("UTF-8")
        except Exception as e:
            return jsonify({'error': f'Error reading file: {str(e)}'}), 400
        
        # Find header row by scanning lines
        # Some CSV files have metadata lines before the header
        lines = file_content.splitlines()
        header_row_idx = None
        header_row = None
        normalized_header = None
        
        # Define format patterns and column aliases
        format1_columns = ['Details', 'Posting Date', 'Description', 'Amount', 'Type', 'Balance', 'Check or Slip #']
        format2_columns = ['Posting Date', 'Description', 'Amount', 'Balance']
        format3_columns = ['Date', 'Description', 'Credit', 'Debit', 'Balance']
        format2_aliases = {
            'Date': 'Posting Date',
            'Running Bal.': 'Balance',
            'Running Balance': 'Balance',
            'Running Bal': 'Balance'
        }
        
        # Column name normalization map (aliases -> standard names)
        column_aliases = {
            'Date': 'Posting Date',
            'Running Bal.': 'Balance',
            'Running Balance': 'Balance',
            'Running Bal': 'Balance'
        }
        
        # Scan up to first 20 lines to find header (reasonable limit)
        for idx, line in enumerate(lines[:20]):
            if not line.strip():
                continue
            
            # Parse this line as CSV to get column names
            try:
                reader = csv.reader([line], skipinitialspace=True, quotechar='"', delimiter=',')
                row = next(reader)
                # Normalize column names (strip whitespace, handle case-insensitive matching)
                normalized_row = [(col or '').strip() for col in row]
                normalized_row_lower = [col.lower() for col in normalized_row]
                
                # Check if this row matches Format 1 (case-insensitive)
                normalized_format1 = [col.strip().lower() for col in format1_columns]
                if all(col in normalized_row_lower for col in normalized_format1):
                    header_row_idx = idx
                    header_row = normalized_row
                    # Normalize header to standard names (case-insensitive alias lookup)
                    normalized_header = []
                    for col in normalized_row:
                        # Try exact match first, then case-insensitive
                        if col in column_aliases:
                            normalized_header.append(column_aliases[col])
                        else:
                            # Try case-insensitive match
                            col_lower = col.lower()
                            found = False
                            for alias_key, alias_value in column_aliases.items():
                                if alias_key.lower() == col_lower:
                                    normalized_header.append(alias_value)
                                    found = True
                                    break
                            if not found:
                                normalized_header.append(col)
                    break
                
                # Check if this row matches Format 2 (with aliases, case-insensitive)
                # First normalize aliases in the row (case-insensitive)
                normalized_row_aliases = []
                for col in normalized_row:
                    col_lower = col.lower()
                    # Check exact match first
                    if col in column_aliases:
                        normalized_row_aliases.append(column_aliases[col])
                    else:
                        # Try case-insensitive match
                        found = False
                        for alias_key, alias_value in column_aliases.items():
                            if alias_key.lower() == col_lower:
                                normalized_row_aliases.append(alias_value)
                                found = True
                                break
                        if not found:
                            normalized_row_aliases.append(col)
                
                normalized_format2 = [col.strip().lower() for col in format2_columns]
                normalized_row_aliases_lower = [col.lower() for col in normalized_row_aliases]
                if all(col in normalized_row_aliases_lower for col in normalized_format2):
                    header_row_idx = idx
                    header_row = normalized_row
                    # Normalize header to standard names
                    normalized_header = normalized_row_aliases
                    break
                
                # Check if this row matches Format 3 (case-insensitive)
                normalized_format3 = [col.strip().lower() for col in format3_columns]
                if all(col in normalized_row_lower for col in normalized_format3):
                    header_row_idx = idx
                    header_row = normalized_row
                    # For format3, normalize Date to Posting Date for consistency
                    normalized_header = []
                    for col in normalized_row:
                        if col.lower() == 'date':
                            normalized_header.append('Posting Date')
                        else:
                            normalized_header.append(col)
                    break
            except Exception:
                # Not a valid CSV row, continue
                continue
        
        if header_row_idx is None:
            error_msg = (f'CSV format not recognized. Could not find header row in first 20 lines.\n'
                        f'Format 1 requires: {", ".join(format1_columns)}\n'
                        f'Format 2 requires: {", ".join(format2_columns)} (or aliases: Date, Running Bal.)\n'
                        f'Format 3 requires: {", ".join(format3_columns)}')
            if lines:
                error_msg += f'\n\nFirst few lines of CSV:\n' + '\n'.join(lines[:5])
            print(f"DEBUG import_transactions_csv: {error_msg}", flush=True)
            sys.stdout.flush()
            return jsonify({
                'error': error_msg,
                'scanned_lines': min(20, len(lines))
            }), 400
        
        # Create CSV content starting from header row
        csv_content_from_header = '\n'.join(lines[header_row_idx:])
        stream = io.StringIO(csv_content_from_header)
        
        # Configure CSV reader to properly handle quoted fields with embedded commas
        csv_reader = csv.DictReader(
            stream, 
            skipinitialspace=True,
            quotechar='"',
            quoting=csv.QUOTE_MINIMAL,  # Only quote fields when necessary
            doublequote=True,  # Handle double quotes within quoted fields (e.g., "" inside quotes)
            escapechar=None,
            delimiter=','
        )
        
        # Normalize fieldnames using aliases (case-insensitive)
        original_fieldnames = csv_reader.fieldnames
        normalized_fieldnames = []
        for fn in original_fieldnames:
            if fn is None:
                continue  # Skip None fieldnames
            fn_stripped = fn.strip()
            fn_lower = fn_stripped.lower()
            # Try exact match first
            if fn_stripped in column_aliases:
                normalized_fieldnames.append(column_aliases[fn_stripped])
            else:
                # Try case-insensitive match
                found = False
                for alias_key, alias_value in column_aliases.items():
                    if alias_key.lower() == fn_lower:
                        normalized_fieldnames.append(alias_value)
                        found = True
                        break
                if not found:
                    normalized_fieldnames.append(fn_stripped)
        
        # Create a wrapper class to normalize fieldnames
        class NormalizedDictReader:
            def __init__(self, reader, fieldname_map):
                self.reader = reader
                self.fieldname_map = {orig: norm for orig, norm in zip(original_fieldnames, normalized_fieldnames)}
                self.fieldnames = normalized_fieldnames
            
            def __iter__(self):
                return self
            
            def __next__(self):
                row = next(self.reader)
                # Create new dict with normalized keys
                normalized_row = {}
                for orig_key, value in row.items():
                    if orig_key is None:
                        continue  # Skip None keys
                    normalized_key = self.fieldname_map.get(orig_key.strip(), orig_key.strip())
                    normalized_row[normalized_key] = value
                return normalized_row
        
        csv_reader = NormalizedDictReader(csv_reader, {orig: norm for orig, norm in zip(original_fieldnames, normalized_fieldnames)})
        
        # Detect CSV format based on normalized columns
        csv_format = None
        if all(col in csv_reader.fieldnames for col in format1_columns):
            csv_format = 'format1'  # Original format with Type field
        elif all(col in csv_reader.fieldnames for col in format2_columns):
            csv_format = 'format2'  # New format: Amount sign determines debit/credit
        elif all(col in csv_reader.fieldnames for col in format3_columns):
            csv_format = 'format3'  # Format with separate Credit and Debit columns
        else:
            # Check for Format 3 with normalized Date -> Posting Date
            # Format 3 columns after normalization: Posting Date, Description, Credit, Debit, Balance
            format3_normalized = ['Posting Date', 'Description', 'Credit', 'Debit', 'Balance']
            print(f"DEBUG: Checking Format 3 normalized. Fieldnames: {list(csv_reader.fieldnames)}, Format3 normalized: {format3_normalized}", flush=True)
            format3_match = all(col in csv_reader.fieldnames for col in format3_normalized)
            print(f"DEBUG: Format 3 normalized match: {format3_match}", flush=True)
            if format3_match:
                csv_format = 'format3'  # Format with separate Credit and Debit columns
                print(f"DEBUG: Detected Format 3 (normalized)", flush=True)
            else:
                error_msg = (f'CSV format not recognized after normalization. Required columns:\n'
                            f'Format 1: {", ".join(format1_columns)}\n'
                            f'Format 2: {", ".join(format2_columns)} (or aliases: Date, Running Bal.)\n'
                            f'Format 3: {", ".join(format3_columns)}\n\n'
                            f'Found columns: {", ".join(original_fieldnames) if original_fieldnames else "None"}\n'
                            f'Normalized columns: {", ".join(csv_reader.fieldnames) if csv_reader.fieldnames else "None"}')
                print(f"DEBUG import_transactions_csv: {error_msg}", flush=True)
                sys.stdout.flush()
                return jsonify({
                    'error': error_msg,
                    'found_columns': list(original_fieldnames) if original_fieldnames else [],
                    'normalized_columns': list(csv_reader.fieldnames) if csv_reader.fieldnames else [],
                    'header_row_index': header_row_idx + 1
                }), 400
        
        print(f"Detected CSV format: {csv_format}, header found at line {header_row_idx + 1}, skipped {header_row_idx} lines")
        
        if USE_COSMOS_DB:
            try:
                from database_cosmos import (
                    get_chart_of_accounts, get_chart_of_account,
                    query_items, create_item
                )
                from datetime import datetime
                
                # Get bank account details and find its chart of account
                bank_accounts = query_items(
                    'bank_accounts',
                    'SELECT c.bank_account_id as id, c.business_id, c.account_name, c.account_number, c.bank_name, c.routing_number, c.opening_balance, c.current_balance, c.account_code, c.is_active, c.created_at FROM c WHERE c.type = "bank_account" AND c.business_id = @business_id',
                    [{"name": "@business_id", "value": business_id}],
                    partition_key=str(business_id)
                )
                bank_account = None
                for ba in bank_accounts:
                    if str(ba.get('id')) == str(bank_account_id) or str(ba.get('bank_account_id')) == str(bank_account_id):
                        bank_account = ba
                        break
                
                if not bank_account:
                    return jsonify({'error': 'Bank account not found'}), 404
                
                # Find or create chart of account for this bank account
                bank_chart_account = None
                bank_account_code = bank_account.get('account_code')
                if bank_account_code:
                    accounts = get_chart_of_accounts(business_id)
                    for acc in accounts:
                        if acc.get('account_code') == bank_account_code:
                            bank_chart_account = acc
                            break
                
                # If no chart account exists for bank, create one
                if not bank_chart_account:
                    # Try to find a generic bank account type
                    bank_account_types = query_items(
                        'account_types',
                        'SELECT * FROM c WHERE c.type = "account_type" AND c.code = "BANK"',
                        partition_key=None
                    )
                    
                    if bank_account_types:
                        bank_account_type = bank_account_types[0]
                        base_account_code = bank_account_code or f'BANK-{bank_account_id}'
                        
                        # Generate unique account code
                        account_code = base_account_code
                        suffix = 1
                        existing_accounts = get_chart_of_accounts(business_id)
                        
                        while True:
                            if any(acc.get('account_code') == account_code for acc in existing_accounts):
                                suffix += 1
                                account_code = f'{base_account_code}-{suffix}'
                                if suffix > 100:
                                    return jsonify({'error': 'Could not create unique account code for bank account'}), 400
                            else:
                                break
                        
                        # Get next account_id
                        next_account_id = max([acc.get('id') or acc.get('account_id', 0) for acc in existing_accounts], default=0) + 1
                        
                        # Create chart of account for this bank
                        import uuid
                        account_doc = {
                            'id': str(uuid.uuid4()),  # Use UUID for document ID
                            'type': 'chart_of_account',
                            'account_id': next_account_id,
                            'business_id': business_id,
                            'account_code': account_code,
                            'account_name': bank_account.get('account_name'),
                            'account_type_id': bank_account_type.get('account_type_id'),
                            'description': '',
                            'parent_account_id': None,
                            'is_active': True,
                            'created_at': datetime.utcnow().isoformat(),
                            'account_type': {
                                'id': bank_account_type.get('account_type_id'),
                                'code': bank_account_type.get('code'),
                                'name': bank_account_type.get('name'),
                                'category': bank_account_type.get('category'),
                                'normal_balance': bank_account_type.get('normal_balance')
                            }
                        }
                        
                        bank_chart_account = create_item('chart_of_accounts', account_doc, partition_key=str(business_id))
                
                if not bank_chart_account:
                    return jsonify({'error': 'Could not find or create chart of account for bank account'}), 400
                
                # Get or create "Uncategorized" accounts for expense and revenue
                def get_or_create_uncategorized_account(category, account_type_name):
                    """Get or create an uncategorized account for the given category."""
                    account_code = f'UNCATEGORIZED_{category}'
                    accounts = get_chart_of_accounts(business_id)
                    for acc in accounts:
                        if acc.get('account_code') == account_code:
                            return acc
                    
                    # Find account type
                    account_types = query_items(
                        'account_types',
                        'SELECT * FROM c WHERE c.type = "account_type" AND c.category = @category',
                        [{"name": "@category", "value": category}],
                        partition_key=None
                    )
                    
                    if account_types:
                        account_type = account_types[0]
                        existing_accounts = get_chart_of_accounts(business_id)
                        next_account_id = max([acc.get('id') or acc.get('account_id', 0) for acc in existing_accounts], default=0) + 1
                        
                        import uuid
                        account_doc = {
                            'id': str(uuid.uuid4()),  # Use UUID for document ID
                            'type': 'chart_of_account',
                            'account_id': next_account_id,
                            'business_id': business_id,
                            'account_code': account_code,
                            'account_name': f'Uncategorized {account_type_name}',
                            'account_type_id': account_type.get('account_type_id'),
                            'description': '',
                            'parent_account_id': None,
                            'is_active': True,
                            'created_at': datetime.utcnow().isoformat(),
                            'account_type': {
                                'id': account_type.get('account_type_id'),
                                'code': account_type.get('code'),
                                'name': account_type.get('name'),
                                'category': account_type.get('category'),
                                'normal_balance': account_type.get('normal_balance')
                            }
                        }
                        
                        return create_item('chart_of_accounts', account_doc, partition_key=str(business_id))
                    return None
                
                uncategorized_expense = get_or_create_uncategorized_account('EXPENSE', 'Expense')
                uncategorized_revenue = get_or_create_uncategorized_account('REVENUE', 'Revenue')
                
                # Use provided accounts or fall back to uncategorized
                if expense_account_id:
                    expense_account = get_chart_of_account(expense_account_id, business_id)
                else:
                    expense_account = uncategorized_expense
                
                if revenue_account_id:
                    revenue_account = get_chart_of_account(revenue_account_id, business_id)
                else:
                    revenue_account = uncategorized_revenue
                
                # Helper function to get or create transaction type mapping
                def get_or_create_transaction_type_mapping(csv_type):
                    """Get or create a transaction type mapping for the CSV type."""
                    if not csv_type:
                        csv_type = ''
                    csv_type_upper = str(csv_type).upper().strip()
                    
                    # First, try to find existing mapping
                    mappings = query_items(
                        'transaction_type_mappings',
                        'SELECT * FROM c WHERE c.type = "transaction_type_mapping" AND c.csv_type = @csv_type',
                        [{"name": "@csv_type", "value": csv_type_upper}],
                        partition_key=None
                    )
                    
                    if mappings:
                        return mappings[0]
                    
                    # If not found, try to infer direction from type name
                    direction = None
                    internal_type = 'ADJUSTMENT'
                    
                    # Try to infer from keywords
                    if any(keyword in csv_type_upper for keyword in ['CREDIT', 'DEPOSIT', 'INCOME', 'RECEIVED', 'INTEREST', 'DIVIDEND']):
                        direction = 'CREDIT'
                        internal_type = 'DEPOSIT' if 'DEPOSIT' in csv_type_upper else 'INCOME' if 'INCOME' in csv_type_upper else 'PAYMENT_RECEIVED'
                    elif any(keyword in csv_type_upper for keyword in ['DEBIT', 'WITHDRAWAL', 'PAYMENT', 'CHARGE', 'FEE', 'EXPENSE']):
                        direction = 'DEBIT'
                        internal_type = 'WITHDRAWAL' if 'WITHDRAWAL' in csv_type_upper else 'EXPENSE' if 'FEE' in csv_type_upper or 'EXPENSE' in csv_type_upper else 'PAYMENT'
                    
                    # If we couldn't infer, default to DEBIT
                    if not direction:
                        direction = 'DEBIT'
                        internal_type = 'ADJUSTMENT'
                    
                    # Get next mapping_id
                    existing_mappings = query_items(
                        'transaction_type_mappings',
                        'SELECT * FROM c WHERE c.type = "transaction_type_mapping"',
                        partition_key=None
                    )
                    next_mapping_id = max([m.get('mapping_id') or m.get('id', 0) for m in existing_mappings], default=0) + 1
                    
                    # Create new mapping
                    mapping_doc = {
                        'id': f'mapping-{next_mapping_id}',
                        'type': 'transaction_type_mapping',
                        'mapping_id': next_mapping_id,
                        'csv_type': csv_type_upper,
                        'internal_type': internal_type,
                        'direction': direction,
                        'description': f'Auto-created mapping for {csv_type}',
                        'created_at': datetime.utcnow().isoformat()
                    }
                    
                    return create_item('transaction_type_mappings', mapping_doc, partition_key=str(next_mapping_id))
                
                # Parse transactions
                imported_count = 0
                skipped_count = 0
                errors = []
                
                # Get current max transaction_id for this business
                existing_transactions = query_items(
                    'transactions',
                    'SELECT VALUE MAX(c.transaction_id) FROM c WHERE c.type = "transaction" AND c.business_id = @business_id',
                    [{"name": "@business_id", "value": business_id}],
                    partition_key=str(business_id)
                )
                next_transaction_id = (existing_transactions[0] if existing_transactions and existing_transactions[0] is not None else 0) + 1
                
                # Row index starts after header row
                for row_idx, row in enumerate(csv_reader, start=header_row_idx + 2):
                    try:
                        # Parse CSV row
                        posting_date_str = (row.get('Posting Date') or row.get('Date') or '').strip()
                        if not posting_date_str:
                            errors.append(f'Row {row_idx}: Missing Date/Posting Date')
                            skipped_count += 1
                            continue
                        
                        description = (row.get('Description') or '').strip() or (row.get('Details') or '').strip()
                        
                        # Determine transaction direction and type based on CSV format
                        if csv_format == 'format3':
                            # Format 3: Separate Credit and Debit columns
                            credit_value = row.get('Credit') or row.get('credit') or ''
                            debit_value = row.get('Debit') or row.get('debit') or ''
                            
                            credit_str = str(credit_value).strip().replace(',', '').replace('$', '') if credit_value else '0'
                            debit_str = str(debit_value).strip().replace(',', '').replace('$', '') if debit_value else '0'
                            
                            # Parse credit and debit amounts
                            try:
                                credit_amount = float(credit_str) if credit_str else 0.0
                                debit_amount = float(debit_str) if debit_str else 0.0
                            except ValueError:
                                errors.append(f'Row {row_idx}: Invalid credit/debit amounts: Credit={credit_str}, Debit={debit_str}')
                                skipped_count += 1
                                continue
                            
                            # Determine direction based on which column has a value
                            if credit_amount > 0 and debit_amount == 0:
                                direction = 'CREDIT'
                                internal_type = 'DEPOSIT'
                                amount = credit_amount
                            elif debit_amount > 0 and credit_amount == 0:
                                direction = 'DEBIT'
                                internal_type = 'WITHDRAWAL'
                                amount = debit_amount
                            elif credit_amount == 0 and debit_amount == 0:
                                skipped_count += 1
                                continue
                            else:
                                errors.append(f'Row {row_idx}: Both Credit and Debit have values. Only one should have a value.')
                                skipped_count += 1
                                continue
                            check_number = None
                        elif csv_format == 'format2':
                            # Format 2: Amount sign determines debit/credit
                            amount_value = row.get('Amount') or row.get('amount') or ''
                            if not amount_value:
                                errors.append(f'Row {row_idx}: Missing Amount')
                                skipped_count += 1
                                continue
                            
                            amount_str = str(amount_value).strip().replace(',', '').replace('$', '')
                            
                            # Parse amount
                            try:
                                amount = float(amount_str)
                            except ValueError:
                                errors.append(f'Row {row_idx}: Invalid amount: {amount_str}')
                                skipped_count += 1
                                continue
                            
                            if amount < 0:
                                direction = 'DEBIT'
                                internal_type = 'WITHDRAWAL'
                                amount = abs(amount)
                            elif amount > 0:
                                direction = 'CREDIT'
                                internal_type = 'DEPOSIT'
                            else:
                                skipped_count += 1
                                continue
                            check_number = None
                        else:
                            # Format 1: Use Type field to determine direction
                            amount_value = row.get('Amount') or row.get('amount') or ''
                            if not amount_value:
                                errors.append(f'Row {row_idx}: Missing Amount')
                                skipped_count += 1
                                continue
                            
                            amount_str = str(amount_value).strip().replace(',', '').replace('$', '')
                            
                            # Parse amount
                            try:
                                amount = float(amount_str)
                            except ValueError:
                                errors.append(f'Row {row_idx}: Invalid amount: {amount_str}')
                                skipped_count += 1
                                continue
                            
                            csv_transaction_type = (row.get('Type') or '').strip()
                            check_number = (row.get('Check or Slip #') or '').strip()
                            amount = abs(amount)
                            
                            if amount == 0:
                                skipped_count += 1
                                continue
                            
                            # Get or create transaction type mapping
                            type_mapping = get_or_create_transaction_type_mapping(csv_transaction_type)
                            if not type_mapping:
                                errors.append(f'Row {row_idx}: Could not create transaction type mapping for: {csv_transaction_type}')
                                skipped_count += 1
                                continue
                            
                            direction = type_mapping.get('direction')
                            internal_type = type_mapping.get('internal_type')
                        
                        # Parse date
                        posting_date = None
                        date_formats = [
                            '%m/%d/%y', '%m/%d/%Y', '%Y-%m-%d', '%m-%d-%Y', '%d/%m/%Y', '%d/%m/%y'
                        ]
                        
                        for date_format in date_formats:
                            try:
                                posting_date = datetime.strptime(posting_date_str, date_format).date()
                                if posting_date.year < 1900:
                                    if posting_date.year < 100:
                                        if posting_date.year < 50:
                                            posting_date = posting_date.replace(year=2000 + posting_date.year)
                                        else:
                                            posting_date = posting_date.replace(year=1900 + posting_date.year)
                                break
                            except ValueError:
                                continue
                        
                        # Fallback: manual parsing
                        if not posting_date:
                            import re
                            date_match = re.match(r'^(\d{1,2})/(\d{1,2})/(\d{2,4})$', posting_date_str.strip())
                            if date_match:
                                try:
                                    month = int(date_match.group(1))
                                    day = int(date_match.group(2))
                                    year_str = date_match.group(3)
                                    
                                    if len(year_str) == 2:
                                        year = int(year_str)
                                        if year < 50:
                                            year = 2000 + year
                                        else:
                                            year = 1900 + year
                                    else:
                                        year = int(year_str)
                                    
                                    posting_date = datetime(year, month, day).date()
                                except (ValueError, AttributeError):
                                    pass
                        
                        if not posting_date:
                            errors.append(f'Row {row_idx}: Invalid date format: {posting_date_str}')
                            skipped_count += 1
                            continue
                        
                        # Determine transaction lines based on direction
                        lines = []
                        
                        if direction == 'DEBIT':
                            # Money going out: Debit expense account, Credit bank
                            if not expense_account:
                                errors.append(f'Row {row_idx}: Could not create or find expense account')
                                skipped_count += 1
                                continue
                            
                            if not bank_chart_account:
                                errors.append(f'Row {row_idx}: Could not create or find bank chart account')
                                skipped_count += 1
                                continue
                            
                            # Line 1: Debit expense account
                            lines.append({
                                'id': f'line-{next_transaction_id}-0',
                                'transaction_line_id': 1,
                                'chart_of_account_id': expense_account.get('id') or expense_account.get('account_id'),
                                'debit_amount': amount,
                                'credit_amount': 0,
                                'account_code': expense_account.get('account_code'),
                                'account_name': expense_account.get('account_name')
                            })
                            # Line 2: Credit bank account
                            lines.append({
                                'id': f'line-{next_transaction_id}-1',
                                'transaction_line_id': 2,
                                'chart_of_account_id': bank_chart_account.get('id') or bank_chart_account.get('account_id'),
                                'debit_amount': 0,
                                'credit_amount': amount,
                                'account_code': bank_chart_account.get('account_code'),
                                'account_name': bank_chart_account.get('account_name')
                            })
                        elif direction == 'CREDIT':
                            # Money coming in: Debit bank, Credit revenue account
                            if not revenue_account:
                                errors.append(f'Row {row_idx}: Could not create or find revenue account')
                                skipped_count += 1
                                continue
                            
                            if not bank_chart_account:
                                errors.append(f'Row {row_idx}: Could not create or find bank chart account')
                                skipped_count += 1
                                continue
                            
                            # Line 1: Debit bank account
                            lines.append({
                                'id': f'line-{next_transaction_id}-0',
                                'transaction_line_id': 1,
                                'chart_of_account_id': bank_chart_account.get('id') or bank_chart_account.get('account_id'),
                                'debit_amount': amount,
                                'credit_amount': 0,
                                'account_code': bank_chart_account.get('account_code'),
                                'account_name': bank_chart_account.get('account_name')
                            })
                            # Line 2: Credit revenue account
                            lines.append({
                                'id': f'line-{next_transaction_id}-1',
                                'transaction_line_id': 2,
                                'chart_of_account_id': revenue_account.get('id') or revenue_account.get('account_id'),
                                'debit_amount': 0,
                                'credit_amount': amount,
                                'account_code': revenue_account.get('account_code'),
                                'account_name': revenue_account.get('account_name')
                            })
                        else:
                            errors.append(f'Row {row_idx}: Invalid direction for transaction type')
                            skipped_count += 1
                            continue
                        
                        # Validate that transaction lines use different accounts
                        if len(lines) == 2:
                            account_ids = [line['chart_of_account_id'] for line in lines]
                            if account_ids[0] == account_ids[1]:
                                errors.append(f'Row {row_idx}: Both transaction lines use the same account (ID: {account_ids[0]}). This is invalid for double-entry bookkeeping.')
                                skipped_count += 1
                                continue
                        
                        # Create transaction document
                        transaction_doc = {
                            'id': f'transaction-{next_transaction_id}',
                            'type': 'transaction',
                            'transaction_id': next_transaction_id,
                            'business_id': business_id,
                            'transaction_date': posting_date.isoformat(),
                            'description': description or 'Imported from CSV',
                            'reference_number': check_number if check_number else None,
                            'transaction_type': internal_type,
                            'amount': amount,
                            'created_at': datetime.utcnow().isoformat(),
                            'lines': lines
                        }
                        
                        create_item('transactions', transaction_doc, partition_key=str(business_id))
                        imported_count += 1
                        next_transaction_id += 1
                        
                    except Exception as e:
                        errors.append(f'Row {row_idx}: {str(e)}')
                        skipped_count += 1
                        continue
                
                return jsonify({
                    'success': True,
                    'imported': imported_count,
                    'skipped': skipped_count,
                    'errors': errors[:10]  # Limit errors to first 10
                }), 200
            except Exception as e:
                import sys
                error_str = f"Error in import_transactions_csv (Cosmos DB): {e}"
                print(error_str, flush=True)
                import traceback
                traceback.print_exc(file=sys.stdout)
                sys.stdout.flush()
                return jsonify({'error': f'Error processing CSV: {str(e)}'}), 400
    except Exception as e:
        # Top-level exception handler for any unexpected errors
        import sys
        import traceback
        error_str = f"Unexpected error in import_transactions_csv: {e}"
        print(error_str, flush=True)
        traceback.print_exc(file=sys.stdout)
        sys.stdout.flush()
        return jsonify({'error': f'Unexpected error importing CSV: {str(e)}'}), 500
        
        conn = get_db_connection()
        
        # Get bank account details and find its chart of account
        bank_account = conn.execute(
            'SELECT * FROM bank_accounts WHERE id = ? AND business_id = ?',
            (bank_account_id, business_id)
        ).fetchone()
        
        if not bank_account:
            conn.close()
            return jsonify({'error': 'Bank account not found'}), 404
        
        # Find or create chart of account for this bank account
        bank_chart_account = None
        bank_account_dict = dict(bank_account)
        bank_account_code = bank_account_dict.get('account_code')
        if bank_account_code:
            bank_chart_account_row = conn.execute(
                'SELECT * FROM chart_of_accounts WHERE business_id = ? AND account_code = ?',
                (business_id, bank_account_code)
            ).fetchone()
            bank_chart_account = dict(bank_chart_account_row) if bank_chart_account_row else None
        
        # If no chart account exists for bank, we'll need to create transactions differently
        # For now, we'll create a generic "Bank" account if it doesn't exist
        if not bank_chart_account:
            # Try to find a generic bank account type
            bank_account_type = conn.execute(
                "SELECT id FROM account_types WHERE code = 'BANK'"
            ).fetchone()
            
            if bank_account_type:
                # Create chart of account for this bank
                cursor = conn.cursor()
                base_account_code = bank_account_code or f'BANK-{bank_account_id}'
                bank_account_type_id = bank_account_type['id']
                
                # Generate unique account code if base code is taken
                account_code = base_account_code
                suffix = 1
                while True:
                    existing_account = conn.execute(
                        'SELECT * FROM chart_of_accounts WHERE business_id = ? AND account_code = ?',
                        (business_id, account_code)
                    ).fetchone()
                    
                    if existing_account:
                        bank_chart_account = dict(existing_account)
                        break
                    
                    try:
                        cursor.execute('''
                            INSERT INTO chart_of_accounts 
                            (business_id, account_type_id, account_code, account_name)
                            VALUES (?, ?, ?, ?)
                        ''', (business_id, bank_account_type_id, account_code, bank_account_dict['account_name']))
                        bank_chart_account_id = cursor.lastrowid
                        conn.commit()
                        bank_chart_account_row = conn.execute(
                            'SELECT * FROM chart_of_accounts WHERE id = ?',
                            (bank_chart_account_id,)
                        ).fetchone()
                        bank_chart_account = dict(bank_chart_account_row) if bank_chart_account_row else None
                        break
                    except sqlite3.IntegrityError:
                        # Account was created by another process or code conflict, try with suffix
                        conn.rollback()
                        suffix += 1
                        account_code = f'{base_account_code}-{suffix}'
                        if suffix > 100:  # Safety limit
                            conn.close()
                            return jsonify({'error': 'Could not create unique account code for bank account'}), 400
        
        if not bank_chart_account:
            conn.close()
            return jsonify({'error': 'Could not find or create chart of account for bank account'}), 400
        
        # Get or create "Uncategorized" accounts for expense and revenue
        def get_or_create_uncategorized_account(category, account_type_name):
            """Get or create an uncategorized account for the given category."""
            account_code = f'UNCATEGORIZED_{category}'
            account_row = conn.execute(
                'SELECT * FROM chart_of_accounts WHERE business_id = ? AND account_code = ?',
                (business_id, account_code)
            ).fetchone()
            
            if account_row:
                return dict(account_row)
            
            # Find account type
            account_type = conn.execute(
                'SELECT id FROM account_types WHERE category = ? LIMIT 1',
                (category,)
            ).fetchone()
            
            if account_type:
                cursor = conn.cursor()
                account_type_id = account_type['id']
                
                # Check again in case of race condition
                existing_account_row = conn.execute(
                    'SELECT * FROM chart_of_accounts WHERE business_id = ? AND account_code = ?',
                    (business_id, account_code)
                ).fetchone()
                
                if existing_account_row:
                    return dict(existing_account_row)
                
                try:
                    cursor.execute('''
                        INSERT INTO chart_of_accounts 
                        (business_id, account_type_id, account_code, account_name)
                        VALUES (?, ?, ?, ?)
                    ''', (business_id, account_type_id, account_code, f'Uncategorized {account_type_name}'))
                    account_id = cursor.lastrowid
                    conn.commit()
                    account_row = conn.execute(
                        'SELECT * FROM chart_of_accounts WHERE id = ?',
                        (account_id,)
                    ).fetchone()
                    return dict(account_row) if account_row else None
                except sqlite3.IntegrityError:
                    # Account was created by another process, fetch it
                    conn.rollback()
                    account_row = conn.execute(
                        'SELECT * FROM chart_of_accounts WHERE business_id = ? AND account_code = ?',
                        (business_id, account_code)
                    ).fetchone()
                    return dict(account_row) if account_row else None
            return None
        
        uncategorized_expense = get_or_create_uncategorized_account('EXPENSE', 'Expense')
        uncategorized_revenue = get_or_create_uncategorized_account('REVENUE', 'Revenue')
        
        # Use provided accounts or fall back to uncategorized
        # Convert to dict immediately to avoid sqlite3.Row reference issues
        if expense_account_id:
            expense_account_row = conn.execute(
                'SELECT * FROM chart_of_accounts WHERE id = ? AND business_id = ?',
                (expense_account_id, business_id)
            ).fetchone()
            expense_account = dict(expense_account_row) if expense_account_row else None
        else:
            expense_account = dict(uncategorized_expense) if uncategorized_expense else None
        
        if revenue_account_id:
            revenue_account_row = conn.execute(
                'SELECT * FROM chart_of_accounts WHERE id = ? AND business_id = ?',
                (revenue_account_id, business_id)
            ).fetchone()
            revenue_account = dict(revenue_account_row) if revenue_account_row else None
        else:
            revenue_account = dict(uncategorized_revenue) if uncategorized_revenue else None
        
        # Helper function to get or create transaction type mapping
        def get_or_create_transaction_type_mapping(csv_type):
            """Get or create a transaction type mapping for the CSV type."""
            if not csv_type:
                csv_type = ''
            csv_type_upper = str(csv_type).upper().strip()
            
            # First, try to find existing mapping
            mapping = conn.execute(
                'SELECT * FROM transaction_type_mappings WHERE csv_type = ?',
                (csv_type_upper,)
            ).fetchone()
            
            if mapping:
                return dict(mapping)
            
            # If not found, try to infer direction from type name
            direction = None
            internal_type = 'ADJUSTMENT'
            
            # Try to infer from keywords
            if any(keyword in csv_type_upper for keyword in ['CREDIT', 'DEPOSIT', 'INCOME', 'RECEIVED', 'INTEREST', 'DIVIDEND']):
                direction = 'CREDIT'
                internal_type = 'DEPOSIT' if 'DEPOSIT' in csv_type_upper else 'INCOME' if 'INCOME' in csv_type_upper else 'PAYMENT_RECEIVED'
            elif any(keyword in csv_type_upper for keyword in ['DEBIT', 'WITHDRAWAL', 'PAYMENT', 'CHARGE', 'FEE', 'EXPENSE']):
                direction = 'DEBIT'
                internal_type = 'WITHDRAWAL' if 'WITHDRAWAL' in csv_type_upper else 'EXPENSE' if 'FEE' in csv_type_upper or 'EXPENSE' in csv_type_upper else 'PAYMENT'
            
            # If we couldn't infer, default to DEBIT
            if not direction:
                direction = 'DEBIT'
                internal_type = 'ADJUSTMENT'
            
            # Create new mapping
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO transaction_type_mappings (csv_type, internal_type, direction, description)
                VALUES (?, ?, ?, ?)
            ''', (csv_type_upper, internal_type, direction, f'Auto-created mapping for {csv_type}'))
            conn.commit()
            
            mapping = conn.execute(
                'SELECT * FROM transaction_type_mappings WHERE csv_type = ?',
                (csv_type_upper,)
            ).fetchone()
            
            return dict(mapping) if mapping else None
        
        # Parse transactions
        imported_count = 0
        skipped_count = 0
        errors = []
        
        # Row index starts after header row (header_row_idx + 1) + 1 for first data row
        for row_idx, row in enumerate(csv_reader, start=header_row_idx + 2):  # +2: header_row_idx (0-based) + 1 for header + 1 for first data row
            try:
                # Debug: Log raw row data for first few rows to verify parsing
                if row_idx <= 5:
                    print(f"Row {row_idx} raw data: {dict(row)}")
                
                # Parse CSV row
                posting_date_str = (row.get('Posting Date') or row.get('Date') or '').strip()
                if not posting_date_str:
                    errors.append(f'Row {row_idx}: Missing Date/Posting Date')
                    skipped_count += 1
                    continue
                    
                description = (row.get('Description') or '').strip() or (row.get('Details') or '').strip()
                
                # Debug: Check if description has comma (should be preserved if in quotes)
                if row_idx <= 5 and ',' in description:
                    print(f"Row {row_idx} description with comma preserved: {description}")
                
                # Determine transaction direction and type based on CSV format
                if csv_format == 'format3':
                    # Format 3: Separate Credit and Debit columns
                    credit_value = row.get('Credit') or row.get('credit') or ''
                    debit_value = row.get('Debit') or row.get('debit') or ''
                    
                    credit_str = str(credit_value).strip().replace(',', '').replace('$', '') if credit_value else '0'
                    debit_str = str(debit_value).strip().replace(',', '').replace('$', '') if debit_value else '0'
                    
                    # Parse credit and debit amounts
                    try:
                        credit_amount = float(credit_str) if credit_str else 0.0
                        debit_amount = float(debit_str) if debit_str else 0.0
                    except ValueError:
                        errors.append(f'Row {row_idx}: Invalid credit/debit amounts: Credit={credit_str}, Debit={debit_str}')
                        skipped_count += 1
                        continue
                    
                    # Determine direction based on which column has a value
                    if credit_amount > 0 and debit_amount == 0:
                        direction = 'CREDIT'
                        internal_type = 'DEPOSIT'
                        amount = credit_amount
                    elif debit_amount > 0 and credit_amount == 0:
                        direction = 'DEBIT'
                        internal_type = 'WITHDRAWAL'
                        amount = debit_amount
                    elif credit_amount == 0 and debit_amount == 0:
                        skipped_count += 1
                        continue
                    else:
                        errors.append(f'Row {row_idx}: Both Credit and Debit have values. Only one should have a value.')
                        skipped_count += 1
                        continue
                    check_number = None
                elif csv_format == 'format2':
                    # Format 2: Amount sign determines debit/credit
                    # Negative amount = Debit, Positive amount = Credit
                    amount_value = row.get('Amount') or row.get('amount') or ''
                    if not amount_value:
                        errors.append(f'Row {row_idx}: Missing Amount')
                        skipped_count += 1
                        continue
                    
                    amount_str = str(amount_value).strip().replace(',', '').replace('$', '')
                    
                    # Parse amount
                    try:
                        amount = float(amount_str)
                    except ValueError:
                        errors.append(f'Row {row_idx}: Invalid amount: {amount_str}')
                        skipped_count += 1
                        continue
                    
                    if amount < 0:
                        direction = 'DEBIT'
                        internal_type = 'WITHDRAWAL'
                        amount = abs(amount)  # Store as positive
                    elif amount > 0:
                        direction = 'CREDIT'
                        internal_type = 'DEPOSIT'
                    else:
                        # Zero amount, skip
                        skipped_count += 1
                        continue
                    check_number = None  # Not available in format2
                else:
                    # Format 1: Use Type field to determine direction
                    amount_value = row.get('Amount') or row.get('amount') or ''
                    if not amount_value:
                        errors.append(f'Row {row_idx}: Missing Amount')
                        skipped_count += 1
                        continue
                    
                    amount_str = str(amount_value).strip().replace(',', '').replace('$', '')
                    
                    # Parse amount
                    try:
                        amount = float(amount_str)
                    except ValueError:
                        errors.append(f'Row {row_idx}: Invalid amount: {amount_str}')
                        skipped_count += 1
                        continue
                    
                    csv_transaction_type = (row.get('Type') or '').strip()
                    check_number = (row.get('Check or Slip #') or '').strip()
                    amount = abs(amount)  # Always use positive amount
                    
                    if amount == 0:
                        skipped_count += 1
                        continue
                    
                    # Get or create transaction type mapping
                    type_mapping = get_or_create_transaction_type_mapping(csv_transaction_type)
                    if not type_mapping:
                        errors.append(f'Row {row_idx}: Could not create transaction type mapping for: {csv_transaction_type}')
                        skipped_count += 1
                        continue
                    
                    direction = type_mapping['direction']
                    internal_type = type_mapping['internal_type']
                
                # Parse date (try multiple formats including 2-digit years)
                # Python's strptime is flexible: %m and %d accept 1-2 digits, %y handles 2-digit years
                posting_date = None
                date_formats = [
                    '%m/%d/%y',      # 6/4/24 or 06/04/24 (2-digit year) - try this first for common format
                    '%m/%d/%Y',      # 6/4/2024 or 06/04/2024 (4-digit year)
                    '%Y-%m-%d',      # 2024-06-04
                    '%m-%d-%Y',      # 06-04-2024
                    '%d/%m/%Y',      # 04/06/2024
                    '%d/%m/%y',      # 04/06/24
                ]
                
                for date_format in date_formats:
                    try:
                        posting_date = datetime.strptime(posting_date_str, date_format).date()
                        # Python's %y interprets: 00-68 as 2000-2068, 69-99 as 1969-1999
                        # This is usually correct, but ensure year is reasonable
                        if posting_date.year < 1900:
                            # If somehow we got a year < 1900, adjust it
                            if posting_date.year < 100:
                                # 2-digit year that needs adjustment
                                if posting_date.year < 50:
                                    posting_date = posting_date.replace(year=2000 + posting_date.year)
                                else:
                                    posting_date = posting_date.replace(year=1900 + posting_date.year)
                        break
                    except ValueError:
                        continue
                
                # Fallback: manual parsing if strptime fails
                if not posting_date:
                    import re
                    # Match patterns like: M/D/YY, M/D/YYYY, MM/DD/YY, MM/DD/YYYY
                    date_match = re.match(r'^(\d{1,2})/(\d{1,2})/(\d{2,4})$', posting_date_str.strip())
                    if date_match:
                        try:
                            month = int(date_match.group(1))
                            day = int(date_match.group(2))
                            year_str = date_match.group(3)
                            
                            if len(year_str) == 2:
                                # 2-digit year: assume 2000-2099 for 00-99
                                year = int(year_str)
                                if year < 50:
                                    year = 2000 + year
                                else:
                                    year = 1900 + year
                            else:
                                # 4-digit year
                                year = int(year_str)
                            
                            posting_date = datetime(year, month, day).date()
                        except (ValueError, AttributeError):
                            pass
                
                if not posting_date:
                    errors.append(f'Row {row_idx}: Invalid date format: {posting_date_str}')
                    skipped_count += 1
                    continue
                
                # Determine transaction lines based on direction
                lines = []
                
                # Accounts are already converted to dicts earlier, but ensure they're dicts
                expense_account_dict = expense_account if isinstance(expense_account, dict) else (dict(expense_account) if expense_account else None)
                revenue_account_dict = revenue_account if isinstance(revenue_account, dict) else (dict(revenue_account) if revenue_account else None)
                bank_chart_account_dict = bank_chart_account if isinstance(bank_chart_account, dict) else (dict(bank_chart_account) if bank_chart_account else None)
                
                if direction == 'DEBIT':
                    # Money going out: Debit expense account, Credit bank
                    if not expense_account_dict:
                        errors.append(f'Row {row_idx}: Could not create or find expense account')
                        skipped_count += 1
                        continue
                    
                    if not bank_chart_account_dict:
                        errors.append(f'Row {row_idx}: Could not create or find bank chart account')
                        skipped_count += 1
                        continue
                    
                    # Line 1: Debit expense account
                    lines.append({
                        'chart_of_account_id': expense_account_dict['id'],
                        'debit_amount': amount,
                        'credit_amount': 0
                    })
                    # Line 2: Credit bank account
                    lines.append({
                        'chart_of_account_id': bank_chart_account_dict['id'],
                        'debit_amount': 0,
                        'credit_amount': amount
                    })
                        
                elif direction == 'CREDIT':
                    # Money coming in: Debit bank, Credit revenue account
                    if not revenue_account_dict:
                        errors.append(f'Row {row_idx}: Could not create or find revenue account')
                        skipped_count += 1
                        continue
                    
                    if not bank_chart_account_dict:
                        errors.append(f'Row {row_idx}: Could not create or find bank chart account')
                        skipped_count += 1
                        continue
                    
                    # Line 1: Debit bank account
                    lines.append({
                        'chart_of_account_id': bank_chart_account_dict['id'],
                        'debit_amount': amount,
                        'credit_amount': 0
                    })
                    # Line 2: Credit revenue account
                    lines.append({
                        'chart_of_account_id': revenue_account_dict['id'],
                        'debit_amount': 0,
                        'credit_amount': amount
                    })
                else:
                    errors.append(f'Row {row_idx}: Invalid direction for transaction type: {csv_transaction_type}')
                    skipped_count += 1
                    continue
                
                # Create transaction
                cursor = conn.cursor()
                reference = check_number if check_number else None
                
                cursor.execute('''
                    INSERT INTO transactions 
                    (business_id, transaction_date, description, reference_number, transaction_type, amount)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    business_id,
                    posting_date.isoformat(),
                    description or 'Imported from CSV',
                    reference,
                    internal_type,
                    amount
                ))
                
                transaction_id = cursor.lastrowid
                
                # Validate that transaction lines use different accounts
                if len(lines) == 2:
                    account_ids = [line['chart_of_account_id'] for line in lines]
                    if account_ids[0] == account_ids[1]:
                        errors.append(f'Row {row_idx}: Both transaction lines use the same account (ID: {account_ids[0]}). This is invalid for double-entry bookkeeping.')
                        skipped_count += 1
                        conn.rollback()
                        continue
                
                # Create transaction lines
                for line in lines:
                    cursor.execute('''
                        INSERT INTO transaction_lines 
                        (transaction_id, chart_of_account_id, debit_amount, credit_amount)
                        VALUES (?, ?, ?, ?)
                    ''', (
                        transaction_id,
                        line['chart_of_account_id'],
                        line['debit_amount'],
                        line['credit_amount']
                    ))
                
                conn.commit()
                imported_count += 1
                
            except Exception as e:
                errors.append(f'Row {row_idx}: {str(e)}')
                skipped_count += 1
                conn.rollback()
                continue
        
        conn.close()
        
        return jsonify({
            'success': True,
            'imported': imported_count,
            'skipped': skipped_count,
            'errors': errors[:10]  # Limit errors to first 10
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Error processing CSV: {str(e)}'}), 400

# ========== REPORTS ROUTES ==========

@app.route('/api/businesses/<int:business_id>/reports/profit-loss', methods=['GET'])
def get_profit_loss(business_id):
    """Get Profit & Loss report."""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    year = request.args.get('year')
    
    if year:
        start_date = f'{year}-01-01'
        end_date = f'{year}-12-31'
    
    if not start_date or not end_date:
        return jsonify({'error': 'start_date and end_date (or year) are required'}), 400
    
    if USE_COSMOS_DB:
        # Use Cosmos DB P&L function
        accounts = cosmos_get_profit_loss_accounts(business_id, start_date, end_date)
        
        # Group by account type
        revenue_by_type = {}
        expenses_by_type = {}
        
        for acc in accounts:
            account_type = acc.get('account_type', {})
            account_type_name = account_type.get('name', 'Other')
            account_type_id = account_type.get('id')
            balance = acc.get('balance', 0)
            category = account_type.get('category', '')
            
            if category == 'REVENUE':
                if account_type_id not in revenue_by_type:
                    revenue_by_type[account_type_id] = {
                        'account_type_id': account_type_id,
                        'account_type_name': account_type_name,
                        'account_type_code': account_type.get('code', ''),
                        'accounts': [],
                        'total': 0
                    }
                revenue_by_type[account_type_id]['accounts'].append({
                    'id': acc['id'],
                    'account_code': acc['account_code'],
                    'account_name': acc['account_name'],
                    'balance': balance
                })
                revenue_by_type[account_type_id]['total'] += balance
            else:  # EXPENSE
                if account_type_id not in expenses_by_type:
                    expenses_by_type[account_type_id] = {
                        'account_type_id': account_type_id,
                        'account_type_name': account_type_name,
                        'account_type_code': account_type.get('code', ''),
                        'accounts': [],
                        'total': 0
                    }
                expenses_by_type[account_type_id]['accounts'].append({
                    'id': acc['id'],
                    'account_code': acc['account_code'],
                    'account_name': acc['account_name'],
                    'balance': balance
                })
                expenses_by_type[account_type_id]['total'] += balance
        
        revenue = list(revenue_by_type.values())
        expenses = list(expenses_by_type.values())
        revenue.sort(key=lambda x: x['account_type_name'])
        expenses.sort(key=lambda x: x['account_type_name'])
        
        total_revenue = sum(r['total'] for r in revenue)
        total_expenses = sum(e['total'] for e in expenses)
        net_income = total_revenue - total_expenses
        
        return jsonify({
            'start_date': start_date,
            'end_date': end_date,
            'revenue': revenue,
            'total_revenue': total_revenue,
            'expenses': expenses,
            'total_expenses': total_expenses,
            'net_income': net_income
        })
    
    # SQLite implementation - process all businesses user has access to
    conn = get_db_connection()
    
    # Get all revenue and expense accounts across all user's businesses
    if not business_ids:
        conn.close()
        return jsonify({
            'start_date': start_date,
            'end_date': end_date,
            'revenue': [],
            'expenses': [],
            'net_income': 0,
            'total_revenue': 0,
            'total_expenses': 0
        })
    
    placeholders = ','.join(['?'] * len(business_ids))
    accounts = conn.execute(f'''
        SELECT coa.id, coa.account_code, coa.account_name, coa.business_id,
               at.category, at.normal_balance, at.id as account_type_id,
               at.code as account_type_code, at.name as account_type_name
        FROM chart_of_accounts coa
        JOIN account_types at ON coa.account_type_id = at.id
        WHERE coa.business_id IN ({placeholders})
        AND at.category IN ('REVENUE', 'EXPENSE')
        AND coa.is_active = 1
        ORDER BY at.category, at.name, coa.account_code
    ''', business_ids).fetchall()
    
    # Group accounts by account type
    revenue_by_type = {}
    expenses_by_type = {}
    
    print(f"Found {len(accounts)} revenue/expense accounts")
    
    for account in accounts:
        account_id = account['id']
        account_dict = dict(account)
        
        # Calculate total debits and credits for this account in the date range
        account_business_id = account['business_id']
        result = conn.execute('''
            SELECT 
                COALESCE(SUM(tl.debit_amount), 0) as total_debits,
                COALESCE(SUM(tl.credit_amount), 0) as total_credits,
                COUNT(DISTINCT t.id) as transaction_count,
                COUNT(*) as line_count
            FROM transaction_lines tl
            JOIN transactions t ON tl.transaction_id = t.id
            WHERE tl.chart_of_account_id = ?
            AND t.business_id = ?
            AND DATE(t.transaction_date) >= DATE(?)
            AND DATE(t.transaction_date) <= DATE(?)
        ''', (account_id, account_business_id, start_date, end_date)).fetchone()
        
        total_debits = float(result['total_debits'] or 0)
        total_credits = float(result['total_credits'] or 0)
        
        # Calculate balance based on normal balance
        if account['category'] == 'REVENUE':
            # Revenue has normal balance of CREDIT, so balance = credits - debits
            balance = total_credits - total_debits
        else:  # EXPENSE
            # Expenses have normal balance of DEBIT, so balance = debits - credits
            balance = total_debits - total_credits
        
        # Only include accounts with non-zero balance
        if abs(balance) < 0.01:
            continue
        
        account_dict['balance'] = balance
        
        # Group by account type
        account_type_name = account_dict.get('account_type_name', 'Other')
        account_type_id = account_dict.get('account_type_id')
        
        if account['category'] == 'REVENUE':
            if account_type_id not in revenue_by_type:
                revenue_by_type[account_type_id] = {
                    'account_type_id': account_type_id,
                    'account_type_name': account_type_name,
                    'account_type_code': account_dict.get('account_type_code', ''),
                    'accounts': [],
                    'total': 0
                }
            revenue_by_type[account_type_id]['accounts'].append(account_dict)
            revenue_by_type[account_type_id]['total'] += balance
        else:  # EXPENSE
            if account_type_id not in expenses_by_type:
                expenses_by_type[account_type_id] = {
                    'account_type_id': account_type_id,
                    'account_type_name': account_type_name,
                    'account_type_code': account_dict.get('account_type_code', ''),
                    'accounts': [],
                    'total': 0
                }
            expenses_by_type[account_type_id]['accounts'].append(account_dict)
            expenses_by_type[account_type_id]['total'] += balance
    
    # Convert to lists and sort
    revenue = list(revenue_by_type.values())
    expenses = list(expenses_by_type.values())
    
    # Sort revenue and expenses by account type name
    revenue.sort(key=lambda x: x['account_type_name'])
    expenses.sort(key=lambda x: x['account_type_name'])
    
    total_revenue = sum(r['total'] for r in revenue)
    total_expenses = sum(e['total'] for e in expenses)
    net_income = total_revenue - total_expenses
    
    conn.close()
    
    return jsonify({
        'start_date': start_date,
        'end_date': end_date,
        'revenue': revenue,
        'total_revenue': total_revenue,
        'expenses': expenses,
        'total_expenses': total_expenses,
        'net_income': net_income
    })

@app.route('/api/reports/combined-profit-loss', methods=['GET'])
@require_auth
@require_user_access
def get_combined_profit_loss():
    """Get combined Profit & Loss report for all businesses the user has access to."""
    print("=" * 60)
    print("DEBUG combined P&L: Function called")
    user = getattr(request, 'current_user', {})
    print(f"DEBUG combined P&L: User: {user.get('email', 'unknown')}, business_ids: {user.get('business_ids', [])}")
    
    # Get business IDs user has access to
    business_ids = user.get('business_ids', [])
    if isinstance(business_ids, str):
        try:
            business_ids = json.loads(business_ids)
        except:
            business_ids = []
    business_ids = [int(bid) for bid in business_ids if bid]
    print(f"DEBUG combined P&L: Parsed business_ids: {business_ids}")
    
    if not business_ids:
        print("DEBUG combined P&L: No business_ids, returning empty report")
        # User has no business access
        return jsonify({
            'revenue': [],
            'expenses': [],
            'net_income': 0,
            'total_revenue': 0,
            'total_expenses': 0
        })
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    year = request.args.get('year')
    print(f"DEBUG combined P&L: Date params - start_date={start_date}, end_date={end_date}, year={year}")
    
    if year:
        start_date = f'{year}-01-01'
        end_date = f'{year}-12-31'
    
    if not start_date or not end_date:
        print("DEBUG combined P&L: Missing date params, returning 400")
        return jsonify({'error': 'start_date and end_date (or year) are required'}), 400
    
    if USE_COSMOS_DB:
        try:
            print("DEBUG combined P&L: Using Cosmos DB path")
            # Get only businesses user has access to
            # Use query_items directly to get full business objects with business_id field
            all_businesses = query_items(
                'businesses',
                'SELECT * FROM c WHERE c.type = "business"',
                [],
                partition_key=None
            )
            print(f"DEBUG combined P&L: Found {len(all_businesses)} total businesses in DB")
            print(f"DEBUG combined P&L: User business_ids to match: {business_ids}")
            if all_businesses:
                print(f"DEBUG combined P&L: Sample business structure - keys: {list(all_businesses[0].keys())}, business_id: {all_businesses[0].get('business_id')}, id: {all_businesses[0].get('id')}")
            businesses = []
            for b in all_businesses:
                # Get business_id from the document (should be an integer)
                bid = b.get('business_id')
                if bid is None:
                    # Fallback: try to extract from id field if it's like "business-1"
                    bid_str = b.get('id', '')
                    if isinstance(bid_str, str) and bid_str.startswith('business-'):
                        try:
                            bid = int(bid_str.replace('business-', ''))
                        except:
                            print(f"DEBUG combined P&L: Could not parse business id from: {bid_str}")
                            continue
                    else:
                        print(f"DEBUG combined P&L: Business missing business_id and id not parseable: {b.get('id')}")
                        continue
                
                try:
                    bid = int(bid)
                except (ValueError, TypeError):
                    print(f"DEBUG combined P&L: Could not convert business id to int: {bid} (type: {type(bid)})")
                    continue
                
                print(f"DEBUG combined P&L: Checking business id {bid} (type: {type(bid)}) against {business_ids} (types: {[type(x) for x in business_ids]})")
                if bid in business_ids:
                    businesses.append(b)
                    print(f"DEBUG combined P&L: ✓ Added business {bid}: {b.get('name')}")
                else:
                    print(f"DEBUG combined P&L: ✗ Business {bid} not in user's business_ids {business_ids}")
            
            print(f"DEBUG combined P&L: Filtered to {len(businesses)} businesses user has access to")
            if not businesses:
                print("DEBUG combined P&L: No businesses found, returning empty report")
                return jsonify({
                    'revenue': [],
                    'expenses': [],
                    'net_income': 0,
                    'total_revenue': 0,
                    'total_expenses': 0
                })
            
            # Get all revenue/expense accounts across user's businesses
            all_accounts = []
            all_transactions = []
            
            for business in businesses:
                # cosmos_get_businesses() returns business_id as 'id' field
                bid = business.get('business_id') or business.get('id')
                if bid is None:
                    continue
                try:
                    business_id = int(bid)
                except (ValueError, TypeError):
                    # If id is a string like "business-1", extract the number
                    if isinstance(bid, str) and bid.startswith('business-'):
                        try:
                            business_id = int(bid.replace('business-', ''))
                        except:
                            continue
                    else:
                        continue
                    
                # Get accounts for this business
                accounts = cosmos_get_chart_of_accounts(business_id)
                # Filter to revenue/expense - handle nested account_type object
                revenue_expense = []
                for acc in accounts:
                    account_type = acc.get('account_type', {})
                    if not isinstance(account_type, dict):
                        account_type = {}
                    category = account_type.get('category')
                    if category in ('REVENUE', 'EXPENSE'):
                        # Add business_id to account for later use
                        acc['business_id'] = business_id
                        revenue_expense.append(acc)
                all_accounts.extend(revenue_expense)
                
                # Get transactions in date range
                transactions = cosmos_get_transactions(business_id, start_date=start_date, end_date=end_date)
                print(f"DEBUG combined P&L: Business {business_id}: Found {len(transactions)} transactions in date range {start_date} to {end_date}")
                all_transactions.extend(transactions)
            
            # Calculate balances
            account_balances = {}
            print(f"DEBUG combined P&L: Processing {len(all_transactions)} transactions")
            for txn in all_transactions:
                txn_business_id = txn.get('business_id')
                if not txn_business_id:
                    print(f"DEBUG combined P&L: Transaction missing business_id: {txn.get('id')}")
                    continue
                txn_business_id = int(txn_business_id)
                
                for line in txn.get('lines', []):
                    account_id = line.get('chart_of_account_id')
                    if not account_id:
                        continue
                    
                    # Handle account_id that might be in format "account-{business_id}-{account_id}"
                    if isinstance(account_id, str) and account_id.startswith('account-'):
                        parts = account_id.split('-')
                        if len(parts) >= 3:
                            try:
                                account_id = int(parts[2])
                            except:
                                print(f"DEBUG combined P&L: Could not parse account_id: {account_id}")
                                continue
                        else:
                            continue
                    
                    account_id = int(account_id)
                    key = (txn_business_id, account_id)
                    
                    if key not in account_balances:
                        account_balances[key] = {
                            'debit_total': 0.0,
                            'credit_total': 0.0
                        }
                    account_balances[key]['debit_total'] += float(line.get('debit_amount', 0) or 0)
                    account_balances[key]['credit_total'] += float(line.get('credit_amount', 0) or 0)
            
            print(f"DEBUG combined P&L: Calculated balances for {len(account_balances)} account/business combinations")
            if account_balances:
                print(f"DEBUG combined P&L: Sample balance keys: {list(account_balances.keys())[:5]}")
            
            # Build account map with balances and business info
            account_map = {}
            balance_map = {}
            # Build business_map using business_id
            business_map = {}
            for b in businesses:
                bid = b.get('business_id')
                if not bid:
                    # cosmos_get_businesses() returns {'id': business_id, ...}
                    bid = b.get('id')
                if not bid:
                    continue
                # Handle both string and int formats
                if isinstance(bid, str) and bid.startswith('business-'):
                    try:
                        bid = int(bid.replace('business-', ''))
                    except:
                        continue
                business_map[int(bid)] = b.get('name')
            
            print(f"DEBUG combined P&L: Processing {len(all_accounts)} accounts")
            print(f"DEBUG combined P&L: Account balances keys: {list(account_balances.keys())[:5] if account_balances else 'None'}")
            
            accounts_with_balances = 0
            accounts_without_balances = 0
            
            for acc in all_accounts:
                # get_chart_of_accounts returns 'id' (aliased from account_id)
                account_id = acc.get('id')
                if not account_id:
                    continue
                account_id = int(account_id)
                    
                acc_business_id = acc.get('business_id')
                if not acc_business_id:
                    continue
                acc_business_id = int(acc_business_id)
                    
                business_name = business_map.get(acc_business_id, f'Business {acc_business_id}')
                
                # Get account type info - it's a nested object
                account_type = acc.get('account_type', {})
                if not isinstance(account_type, dict):
                    account_type = {}
                    
                category = account_type.get('category')
                if not category or category not in ('REVENUE', 'EXPENSE'):
                    continue
                
                # Ensure both are integers for the key matching
                key = (acc_business_id, account_id)
                balance = 0.0
                if key in account_balances:
                    accounts_with_balances += 1
                    debit_total = account_balances[key]['debit_total']
                    credit_total = account_balances[key]['credit_total']
                    print(f"DEBUG combined P&L: ✓ Found balance for account {account_id} ({acc.get('account_code')}) in business {acc_business_id}: debits={debit_total}, credits={credit_total}, category={category}")
                    
                    if category == 'REVENUE':
                        balance = credit_total - debit_total
                    else:  # EXPENSE
                        balance = debit_total - credit_total
                else:
                    accounts_without_balances += 1
                    if accounts_without_balances <= 5:  # Only log first 5 to avoid spam
                        print(f"DEBUG combined P&L: ✗ No balance found for key ({acc_business_id}, {account_id}) - account: {acc.get('account_code')} {acc.get('account_name')}")
                
                # Include accounts with balance or for hierarchy
                acc_dict = {
                    'account_id': account_id,
                    'account_code': acc.get('account_code'),
                    'account_name': acc.get('account_name'),
                    'parent_account_id': acc.get('parent_account_id'),
                    'business_id': acc_business_id,
                    'business_name': business_name,
                    'category': category,
                    'account_type_id': account_type.get('id') or account_type.get('account_type_id'),
                    'account_type_code': account_type.get('code'),
                    'account_type_name': account_type.get('name'),
                    'balance': balance
                }
                account_map[account_id] = acc_dict
                balance_map[account_id] = balance
            
            print(f"DEBUG combined P&L: Summary - {accounts_with_balances} accounts with balances, {accounts_without_balances} accounts without balances")
            
            # Helper function to get account path
            def get_account_path(account_id, visited=None):
                """Get the path from root to this account."""
                if visited is None:
                    visited = set()
                if account_id in visited or account_id not in account_map:
                    return []
                
                visited.add(account_id)
                account = account_map[account_id]
                parent_id = account.get('parent_account_id')
                
                path = []
                if parent_id:
                    parent_path = get_account_path(parent_id, visited.copy())
                    path.extend(parent_path)
                
                path.append({
                    'account_id': account_id,
                    'account_name': account['account_name'],
                    'account_code': account['account_code']
                })
                return path
            
            # Build hierarchical structure
            revenue_structure = {}
            expense_structure = {}
            
            for account_id, account in account_map.items():
                if abs(account['balance']) < 0.01:
                    continue
                    
                category = account['category']
                account_type_id = account['account_type_id']
                balance = float(account['balance'])
                
                # Get the path
                path = get_account_path(account_id)
                if not path:
                    continue
                
                # Get account type name
                account_type_name = account['account_type_name']
                
                # Get business name
                business_name = account['business_name']
                
                # Select target structure
                target = revenue_structure if category == 'REVENUE' else expense_structure
                
                # Initialize account type level
                if account_type_id not in target:
                    target[account_type_id] = {
                        'account_type_id': account_type_id,
                        'account_type_name': account_type_name,
                        'account_type_code': account['account_type_code'],
                        'children': {},
                        'total': 0.0
                    }
                
                account_type_node = target[account_type_id]
                
                # Build hierarchy: Parent -> Child -> Grand Child -> Business
                current = account_type_node['children']
                
                # Process each level of the path
                for i, path_item in enumerate(path):
                    is_leaf = (i == len(path) - 1)
                    path_name = path_item['account_name']
                    
                    if path_name not in current:
                        current[path_name] = {
                            'account_name': path_name,
                            'account_id': path_item['account_id'],
                            'children': {},
                            'total': 0.0,
                            'is_leaf': False
                        }
                    
                    current_node = current[path_name]
                    
                    if is_leaf:
                        # This is the account with transactions - add business level
                        if 'businesses' not in current_node:
                            current_node['businesses'] = {}
                        
                        if business_name not in current_node['businesses']:
                            current_node['businesses'][business_name] = {
                                'business_name': business_name,
                                'business_id': account['business_id'],
                                'accounts': [],
                                'total': 0.0
                            }
                        
                        # Add this account to the business
                        current_node['businesses'][business_name]['accounts'].append({
                            'account_id': account_id,
                            'account_name': account['account_name'],
                            'account_code': account['account_code'],
                            'balance': balance
                        })
                        current_node['businesses'][business_name]['total'] += balance
                        current_node['total'] += balance
                        account_type_node['total'] += balance
                    else:
                        # Move to next level
                        current = current_node['children']
            
            # Convert structures to lists and calculate subtotals recursively
            def build_hierarchy_output(node, level=0):
                """Convert hierarchy dict to list with subtotals."""
                result = []
                
                # Sort children by name
                children_keys = sorted(node.get('children', {}).keys())
                
                for key in children_keys:
                    child_node = node['children'][key]
                    child_output = {
                        'account_name': child_node['account_name'],
                        'account_id': child_node.get('account_id'),
                        'total': child_node['total'],
                        'level': level
                    }
                    
                    # Add businesses if present
                    if 'businesses' in child_node:
                        child_output['businesses'] = list(child_node['businesses'].values())
                    
                    # Add children if present
                    if child_node.get('children'):
                        child_output['children'] = build_hierarchy_output(child_node, level + 1)
                    
                    result.append(child_output)
                
                return result
            
            # Build final output
            revenue_output = []
            expense_output = []
            
            for account_type_id in sorted(revenue_structure.keys()):
                node = revenue_structure[account_type_id]
                revenue_output.append({
                    'account_type_id': node['account_type_id'],
                    'account_type_name': node['account_type_name'],
                    'account_type_code': node['account_type_code'],
                    'total': node['total'],
                    'children': build_hierarchy_output(node)
                })
            
            for account_type_id in sorted(expense_structure.keys()):
                node = expense_structure[account_type_id]
                expense_output.append({
                    'account_type_id': node['account_type_id'],
                    'account_type_name': node['account_type_name'],
                    'account_type_code': node['account_type_code'],
                    'total': node['total'],
                    'children': build_hierarchy_output(node)
                })
            
            # Calculate totals
            total_revenue = sum(node['total'] for node in revenue_structure.values())
            total_expense = sum(node['total'] for node in expense_structure.values())
            net_income = total_revenue - total_expense
            
            result = {
                'revenue': revenue_output,
                'expenses': expense_output,  # Note: plural 'expenses' to match SQLite version
                'total_revenue': total_revenue,
                'total_expenses': total_expense,  # Note: plural 'total_expenses' to match SQLite version
                'net_income': net_income,
                'start_date': start_date,
                'end_date': end_date
            }
            print(f"DEBUG combined P&L: Returning result - revenue items: {len(revenue_output)}, expense items: {len(expense_output)}, total_revenue: {total_revenue}, total_expenses: {total_expense}, net_income: {net_income}")
            print("=" * 60)
            return jsonify(result)
        except Exception as e:
            print(f"Error getting combined profit loss: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': f'Error generating combined profit loss report: {str(e)}'}), 500
    
    conn = get_db_connection()
    
    # Get all revenue and expense accounts with their balances and hierarchy info
    # Fix: Use INNER JOIN to ensure we only count transaction_lines from transactions in date range
    accounts_data = conn.execute('''
        SELECT 
            coa.id as account_id,
            coa.account_code,
            coa.account_name,
            coa.parent_account_id,
            coa.business_id,
            b.name as business_name,
            at.category,
            at.id as account_type_id,
            at.code as account_type_code,
            at.name as account_type_name,
            COALESCE(SUM(CASE WHEN at.category = 'REVENUE' THEN tl.credit_amount - tl.debit_amount 
                         ELSE tl.debit_amount - tl.credit_amount END), 0) as balance
        FROM chart_of_accounts coa
        JOIN account_types at ON coa.account_type_id = at.id
        JOIN businesses b ON coa.business_id = b.id
        INNER JOIN transaction_lines tl ON tl.chart_of_account_id = coa.id
        INNER JOIN transactions t ON tl.transaction_id = t.id 
            AND t.business_id = coa.business_id
            AND DATE(t.transaction_date) >= DATE(?)
            AND DATE(t.transaction_date) <= DATE(?)
        WHERE at.category IN ('REVENUE', 'EXPENSE')
        AND coa.is_active = 1
        GROUP BY coa.id, coa.account_code, coa.account_name, coa.parent_account_id, 
                 coa.business_id, b.name, at.category, at.id, at.code, at.name
        HAVING ABS(balance) >= 0.01
    ''', (start_date, end_date)).fetchall()
    
    # Build a map of all accounts (including parents that may not have transactions)
    all_accounts_query = conn.execute('''
        SELECT coa.id, coa.account_code, coa.account_name, coa.parent_account_id,
               coa.business_id, b.name as business_name,
               at.category, at.id as account_type_id, at.code as account_type_code, at.name as account_type_name
        FROM chart_of_accounts coa
        JOIN account_types at ON coa.account_type_id = at.id
        JOIN businesses b ON coa.business_id = b.id
        WHERE at.category IN ('REVENUE', 'EXPENSE') AND coa.is_active = 1
    ''').fetchall()
    
    # Create account map with balances
    account_map = {}
    balance_map = {}
    for account in accounts_data:
        acc_dict = dict(account)
        account_id = acc_dict['account_id']
        account_map[account_id] = acc_dict
        balance_map[account_id] = float(acc_dict['balance'])
    
    # Add accounts without transactions (for hierarchy)
    for account in all_accounts_query:
        account_id = account['id']
        if account_id not in account_map:
            account_map[account_id] = dict(account)
            balance_map[account_id] = 0.0
    
    # Helper function to get account path (parent -> child -> grandchild)
    def get_account_path(account_id, visited=None):
        """Get the path from root to this account."""
        if visited is None:
            visited = set()
        if account_id in visited or account_id not in account_map:
            return []
        
        visited.add(account_id)
        account = account_map[account_id]
        parent_id = account.get('parent_account_id')
        
        path = []
        if parent_id:
            parent_path = get_account_path(parent_id, visited.copy())
            path.extend(parent_path)
        
        path.append({
            'account_id': account_id,
            'account_name': account['account_name'],
            'account_code': account['account_code']
        })
        return path
    
    # Helper function to calculate depth
    def get_depth(account_id):
        """Get the depth of the account in the hierarchy (0 = root, 1 = child, 2 = grandchild, 3+ = great grandchild)."""
        account = account_map.get(account_id)
        if not account:
            return 0
        parent_id = account.get('parent_account_id')
        if not parent_id:
            return 0
        return 1 + get_depth(parent_id)
    
    # Build hierarchical structure
    # Group by: Category -> Account Type -> Hierarchy (Parent -> Child -> Grand Child) -> Business
    revenue_structure = {}
    expense_structure = {}
    
    for account in accounts_data:
        account_id = account['account_id']
        category = account['category']
        account_type_id = account['account_type_id']
        balance = float(account['balance'])
        
        # Get the path
        path = get_account_path(account_id)
        depth = len(path) - 1  # 0-based depth
        
        # Get account type name
        account_type_name = account['account_type_name']
        
        # Get business name
        business_name = account['business_name']
        
        # Select target structure
        target = revenue_structure if category == 'REVENUE' else expense_structure
        
        # Initialize account type level
        if account_type_id not in target:
            target[account_type_id] = {
                'account_type_id': account_type_id,
                'account_type_name': account_type_name,
                'account_type_code': account['account_type_code'],
                'children': {},
                'total': 0.0
            }
        
        account_type_node = target[account_type_id]
        
        # Build hierarchy: Parent -> Child -> Grand Child -> Business
        current = account_type_node['children']
        
        # Process each level of the path
        for i, path_item in enumerate(path):
            is_leaf = (i == len(path) - 1)
            path_name = path_item['account_name']
            
            if path_name not in current:
                current[path_name] = {
                    'account_name': path_name,
                    'account_id': path_item['account_id'],
                    'children': {},
                    'total': 0.0,
                    'is_leaf': False
                }
            
            current_node = current[path_name]
            
            if is_leaf:
                # This is the account with transactions - add business level
                if 'businesses' not in current_node:
                    current_node['businesses'] = {}
                
                if business_name not in current_node['businesses']:
                    current_node['businesses'][business_name] = {
                        'business_name': business_name,
                        'business_id': account['business_id'],
                        'accounts': [],
                        'total': 0.0
                    }
                
                # Add this account to the business
                current_node['businesses'][business_name]['accounts'].append({
                    'account_id': account_id,
                    'account_name': account['account_name'],
                    'account_code': account['account_code'],
                    'balance': balance
                })
                current_node['businesses'][business_name]['total'] += balance
                current_node['total'] += balance
                account_type_node['total'] += balance
            else:
                # Move to next level
                current = current_node['children']
    
    # Convert structures to lists and calculate subtotals recursively
    def build_hierarchy_output(node, level=0):
        """Convert hierarchy dict to list with subtotals."""
        result = []
        
        # Sort children by name
        children_keys = sorted(node.get('children', {}).keys())
        
        for key in children_keys:
            child_node = node['children'][key]
            
            output_node = {
                'account_name': child_node['account_name'],
                'account_id': child_node['account_id'],
                'level': level,
                'total': 0.0  # Will be calculated below
            }
            
            # Process businesses if at leaf level
            node_own_balance = 0.0
            if 'businesses' in child_node:
                businesses_list = []
                for biz_name, biz_data in sorted(child_node['businesses'].items()):
                    businesses_list.append({
                        'business_name': biz_data['business_name'],
                        'business_id': biz_data['business_id'],
                        'accounts': biz_data['accounts'],
                        'total': biz_data['total'],
                        'level': level + 1
                    })
                    node_own_balance += biz_data['total']
                output_node['businesses'] = businesses_list
            
            # Recursively process children
            children_total = 0.0
            if child_node.get('children'):
                output_node['children'] = build_hierarchy_output(child_node, level + 1)
                children_total = sum(c['total'] for c in output_node['children'])
            
            # Total = own balance (from businesses) + children totals
            output_node['total'] = node_own_balance + children_total
            
            result.append(output_node)
        
        return result
    
    # Build final output
    revenue_output = []
    expense_output = []
    
    for account_type_id, account_type_node in sorted(revenue_structure.items(), key=lambda x: x[1]['account_type_name']):
        revenue_output.append({
            'account_type_id': account_type_id,
            'account_type_name': account_type_node['account_type_name'],
            'account_type_code': account_type_node['account_type_code'],
            'children': build_hierarchy_output(account_type_node),
            'total': account_type_node['total']
        })
    
    for account_type_id, account_type_node in sorted(expense_structure.items(), key=lambda x: x[1]['account_type_name']):
        expense_output.append({
            'account_type_id': account_type_id,
            'account_type_name': account_type_node['account_type_name'],
            'account_type_code': account_type_node['account_type_code'],
            'children': build_hierarchy_output(account_type_node),
            'total': account_type_node['total']
        })
    
    # Calculate totals directly from accounts_data to ensure accuracy
    # This avoids any issues with hierarchical subtotal calculations
    calculated_total_revenue = sum(
        float(acc['balance']) for acc in accounts_data 
        if acc['category'] == 'REVENUE'
    )
    calculated_total_expenses = sum(
        float(acc['balance']) for acc in accounts_data 
        if acc['category'] == 'EXPENSE'
    )
    
    # Use calculated totals (from actual data) instead of hierarchical sums
    total_revenue = calculated_total_revenue
    total_expenses = calculated_total_expenses
    net_income = total_revenue - total_expenses
    
    conn.close()
    
    return jsonify({
        'start_date': start_date,
        'end_date': end_date,
        'revenue': revenue_output,
        'total_revenue': total_revenue,
        'expenses': expense_output,
        'total_expenses': total_expenses,
        'net_income': net_income
    })

@app.route('/api/businesses/<int:business_id>/reports/balance-sheet', methods=['GET'])
@require_auth
@require_user_access
def get_balance_sheet(business_id):
    """Get Balance Sheet report as of a specific date."""
    if USE_COSMOS_DB:
        try:
            year = request.args.get('year')
            as_of_date = request.args.get('as_of_date')
            
            # If year is provided, set as_of_date to last day of that year
            if year:
                try:
                    year_int = int(year)
                    as_of_date = f'{year_int}-12-31'
                except ValueError:
                    return jsonify({'error': 'Invalid year parameter'}), 400
            elif not as_of_date:
                as_of_date = date.today().isoformat()
            
            print(f"Balance Sheet Query (Cosmos DB) - business_id: {business_id}, year: {year}, as_of_date: {as_of_date}")
            
            # Get all chart of accounts with ASSET, LIABILITY, or EQUITY category
            all_accounts = cosmos_get_chart_of_accounts(business_id)
            
            # Filter to balance sheet accounts (only active accounts)
            balance_sheet_accounts = []
            for acc in all_accounts:
                # Only include active accounts
                if not acc.get('is_active', True):
                    continue
                
                account_type = acc.get('account_type', {})
                if not isinstance(account_type, dict):
                    account_type = {}
                category = account_type.get('category')
                if category in ('ASSET', 'LIABILITY', 'EQUITY'):
                    balance_sheet_accounts.append(acc)
            
            print(f"DEBUG Balance Sheet: Found {len(balance_sheet_accounts)} balance sheet accounts")
            
            # Get all transactions up to as_of_date
            transactions = cosmos_get_transactions(business_id, end_date=as_of_date)
            print(f"DEBUG Balance Sheet: Found {len(transactions)} transactions up to {as_of_date}")
            
            # Calculate account balances from transaction lines
            account_balances = {}
            for txn in transactions:
                txn_date = txn.get('transaction_date', '')
                # Only process transactions on or before as_of_date
                if txn_date and txn_date > as_of_date:
                    continue
                
                for line in txn.get('lines', []):
                    account_id = line.get('chart_of_account_id')
                    if not account_id:
                        continue
                    
                    # Handle account_id that might be in format "account-{business_id}-{account_id}"
                    if isinstance(account_id, str) and account_id.startswith('account-'):
                        parts = account_id.split('-')
                        if len(parts) >= 3:
                            try:
                                account_id = int(parts[2])
                            except:
                                continue
                        else:
                            continue
                    
                    account_id = int(account_id)
                    
                    if account_id not in account_balances:
                        account_balances[account_id] = {
                            'debit_total': 0.0,
                            'credit_total': 0.0
                        }
                    account_balances[account_id]['debit_total'] += float(line.get('debit_amount', 0) or 0)
                    account_balances[account_id]['credit_total'] += float(line.get('credit_amount', 0) or 0)
            
            print(f"DEBUG Balance Sheet: Calculated balances for {len(account_balances)} accounts")
            
            # Build assets, liabilities, and equity lists
            # Only include accounts that have transactions in the selected period
            assets = []
            liabilities = []
            equity = []
            opening_balance_from_equity = 0.0  # Track opening balance from equity accounts
            
            for acc in balance_sheet_accounts:
                account_id = acc.get('id')
                if not account_id:
                    continue
                account_id = int(account_id)
                
                account_type = acc.get('account_type', {})
                if not isinstance(account_type, dict):
                    account_type = {}
                
                category = account_type.get('category')
                account_code = acc.get('account_code', '')
                account_name = acc.get('account_name', '')
                account_code_upper = account_code.upper()
                account_name_upper = account_name.upper()
                
                # Check if this is an "Opening Balance" equity account - exclude it from equity list
                # but include its balance in opening balance calculation
                is_opening_balance_account = (
                    category == 'EQUITY' and 
                    ('OPENING BALANCE' in account_name_upper or 
                     account_code_upper in ['3030', 'OB', 'OPENING'])
                )
                
                if is_opening_balance_account:
                    # Calculate balance for opening balance account (even if no transactions)
                    normal_balance = account_type.get('normal_balance', 'CREDIT')
                    debit_total = account_balances.get(account_id, {}).get('debit_total', 0.0)
                    credit_total = account_balances.get(account_id, {}).get('credit_total', 0.0)
                    
                    if normal_balance == 'DEBIT':
                        balance = debit_total - credit_total
                    else:
                        balance = credit_total - debit_total
                    
                    opening_balance_from_equity += balance
                    print(f"DEBUG Balance Sheet: Found Opening Balance equity account {account_code} - {account_name} with balance {balance}")
                    continue  # Skip adding to equity list
                
                # Only include accounts that have transactions (are in account_balances)
                if account_id not in account_balances:
                    continue
                
                normal_balance = account_type.get('normal_balance', 'DEBIT')
                
                # Calculate balance
                debit_total = account_balances.get(account_id, {}).get('debit_total', 0.0)
                credit_total = account_balances.get(account_id, {}).get('credit_total', 0.0)
                
                if normal_balance == 'DEBIT':
                    balance = debit_total - credit_total
                else:
                    balance = credit_total - debit_total
                
                account_dict = {
                    'id': account_id,
                    'account_code': acc.get('account_code'),
                    'account_name': acc.get('account_name'),
                    'balance': balance,
                    'category': category
                }
                
                if category == 'ASSET':
                    assets.append(account_dict)
                elif category == 'LIABILITY':
                    liabilities.append(account_dict)
                else:  # EQUITY (excluding opening balance accounts)
                    equity.append(account_dict)
            
            # Get bank accounts and add to assets
            # But skip if the bank account already exists as a chart of account (to avoid duplicates)
            bank_accounts = query_items(
                'bank_accounts',
                'SELECT c.bank_account_id as id, c.business_id, c.account_name, c.opening_balance, c.current_balance, c.account_code FROM c WHERE c.type = "bank_account" AND c.business_id = @business_id AND c.is_active = true',
                [{"name": "@business_id", "value": business_id}],
                partition_key=str(business_id)
            )
            
            print(f"DEBUG Balance Sheet: Found {len(bank_accounts)} bank accounts")
            
            # Create sets of account codes, IDs, and names that are already in assets (from chart of accounts)
            existing_asset_codes = {acc.get('account_code') for acc in assets if acc.get('account_code')}
            existing_asset_ids = {acc.get('id') for acc in assets if acc.get('id')}
            existing_asset_names = {acc.get('account_name') for acc in assets if acc.get('account_name')}
            
            print(f"DEBUG Balance Sheet: Existing asset codes: {existing_asset_codes}")
            print(f"DEBUG Balance Sheet: Existing asset IDs: {existing_asset_ids}")
            print(f"DEBUG Balance Sheet: Existing asset names: {existing_asset_names}")
            
            # Track bank accounts we've added to avoid duplicates
            added_bank_accounts = set()
            
            for bank in bank_accounts:
                bank_id = bank.get('id')
                bank_account_code = bank.get('account_code') or f'BANK-{bank_id}'
                bank_account_name = bank.get('account_name', '')
                
                # Create a unique key for this bank account
                bank_key = (bank_account_code, bank_account_name, bank_id)
                if bank_key in added_bank_accounts:
                    print(f"DEBUG Balance Sheet: Skipping duplicate bank account {bank_account_code} - {bank_account_name} (id={bank_id})")
                    continue
                
                # Check if a bank account with the same name already exists in assets
                # This prevents duplicates when bank accounts have different codes but same name
                if bank_account_name:
                    existing_bank_with_same_name = any(
                        acc.get('account_name') == bank_account_name and 
                        (acc.get('is_bank_account') or acc.get('account_code', '').startswith('BANK-'))
                        for acc in assets
                    )
                    if existing_bank_with_same_name:
                        print(f"DEBUG Balance Sheet: Skipping bank account {bank_account_code} - {bank_account_name} (id={bank_id}) - bank account with same name already exists in assets")
                        continue
                
                # Find the chart of account associated with this bank account
                bank_chart_account = None
                for acc in all_accounts:
                    if acc.get('account_code') == bank_account_code:
                        bank_chart_account = acc
                        break
                
                # Skip if this bank account's chart of account already exists in assets
                if bank_chart_account:
                    chart_account_id = int(bank_chart_account.get('id'))
                    if chart_account_id in existing_asset_ids:
                        print(f"DEBUG Balance Sheet: Skipping bank account {bank_account_code} (id={bank_id}) - chart of account (id={chart_account_id}) already exists in assets")
                        continue
                    if bank_account_code in existing_asset_codes:
                        print(f"DEBUG Balance Sheet: Skipping bank account {bank_account_code} (id={bank_id}) - account code already exists in assets")
                        continue
                
                # Get opening balance
                opening_balance = bank.get('opening_balance')
                if opening_balance is None:
                    opening_balance = bank.get('current_balance', 0)
                opening_balance = float(opening_balance or 0)
                balance = opening_balance
                
                if bank_chart_account:
                    chart_account_id = int(bank_chart_account.get('id'))
                    if chart_account_id in account_balances:
                        debit_total = account_balances[chart_account_id]['debit_total']
                        credit_total = account_balances[chart_account_id]['credit_total']
                        # Bank accounts are assets (normal balance DEBIT)
                        # Balance = opening balance + (debits - credits)
                        balance = opening_balance + (debit_total - credit_total)
                
                bank_account_dict = {
                    'account_code': bank_account_code,
                    'account_name': bank.get('account_name'),
                    'balance': balance,
                    'is_bank_account': True
                }
                # Add account ID if there's an associated chart of account
                if bank_chart_account:
                    bank_account_dict['id'] = int(bank_chart_account.get('id'))
                
                # Mark this bank account as added
                added_bank_accounts.add(bank_key)
                assets.append(bank_account_dict)
                print(f"DEBUG Balance Sheet: Added bank account {bank_account_code} - {bank_account_name} with balance {balance}")
            
            # Get credit card accounts and add to liabilities
            credit_card_accounts = query_items(
                'credit_card_accounts',
                'SELECT c.credit_card_account_id as id, c.business_id, c.account_name, c.current_balance, c.account_code FROM c WHERE c.type = "credit_card_account" AND c.business_id = @business_id AND c.is_active = true',
                [{"name": "@business_id", "value": business_id}],
                partition_key=str(business_id)
            )
            
            print(f"DEBUG Balance Sheet: Found {len(credit_card_accounts)} credit card accounts")
            
            for cc in credit_card_accounts:
                cc_id = cc.get('id')
                liabilities.append({
                    'account_code': cc.get('account_code') or f'CC-{cc_id}',
                    'account_name': cc.get('account_name'),
                    'balance': float(cc.get('current_balance', 0) or 0),
                    'is_credit_card': True
                })
            
            # Get loan accounts and add to liabilities
            loan_accounts = query_items(
                'loan_accounts',
                'SELECT c.loan_account_id as id, c.business_id, c.account_name, c.current_balance, c.account_code FROM c WHERE c.type = "loan_account" AND c.business_id = @business_id AND c.is_active = true',
                [{"name": "@business_id", "value": business_id}],
                partition_key=str(business_id)
            )
            
            print(f"DEBUG Balance Sheet: Found {len(loan_accounts)} loan accounts")
            
            for loan in loan_accounts:
                loan_id = loan.get('id')
                liabilities.append({
                    'account_code': loan.get('account_code') or f'LOAN-{loan_id}',
                    'account_name': loan.get('account_name'),
                    'balance': float(loan.get('current_balance', 0) or 0),
                    'is_loan': True
                })
            
            # Calculate retained earnings
            # Prior Years Net Income = Opening Balance + Net Income for all prior years
            # Current Year Net Income = Net Income from Jan 1 to as_of_date
            # Total Retained Earnings = Prior Years Net Income + Current Year Net Income
            prior_years_net_income = 0.0
            current_year_net_income = 0.0
            retained_earnings_total = 0.0
            
            try:
                # Determine the year from as_of_date if year not provided
                year_int = int(year) if year else int(as_of_date.split('-')[0])
                earliest_year = 2000  # Start from 2000
                
                # Opening balance from equity accounts (already extracted above)
                opening_balance = opening_balance_from_equity
                print(f"DEBUG Balance Sheet: Opening balance from equity accounts: {opening_balance}")
                
                # Calculate net income for all prior years (before the selected year)
                for y in range(earliest_year, year_int):
                    try:
                        # Get P&L for this year
                        pl_accounts = cosmos_get_profit_loss_accounts(business_id, f'{y}-01-01', f'{y}-12-31')
                        year_revenue = 0.0
                        year_expenses = 0.0
                        for acc in pl_accounts:
                            balance = acc.get('balance', 0.0)
                            category = acc.get('account_type', {}).get('category', '')
                            if category == 'REVENUE':
                                year_revenue += balance
                            else:  # EXPENSE
                                year_expenses += balance
                        year_net_income = year_revenue - year_expenses
                        prior_years_net_income += year_net_income
                    except Exception as e:
                        print(f"Error calculating net income for year {y}: {e}")
                        continue
                
                # Prior Years Net Income includes opening balance from equity accounts
                prior_years_net_income = opening_balance + prior_years_net_income
                print(f"DEBUG Balance Sheet: Prior years net income calculation - Opening: {opening_balance}, Prior Years P&L: {prior_years_net_income - opening_balance}, Total: {prior_years_net_income}")
                
                # Calculate net income for selected year to as_of_date
                start_date = f'{year_int}-01-01'
                pl_accounts = cosmos_get_profit_loss_accounts(business_id, start_date, as_of_date)
                current_year_revenue = 0.0
                current_year_expenses = 0.0
                for acc in pl_accounts:
                    balance = acc.get('balance', 0.0)
                    category = acc.get('account_type', {}).get('category', '')
                    if category == 'REVENUE':
                        current_year_revenue += balance
                    else:  # EXPENSE
                        current_year_expenses += balance
                current_year_net_income = current_year_revenue - current_year_expenses
                
            except Exception as e:
                print(f"Error calculating retained earnings: {e}")
                import traceback
                traceback.print_exc()
            
            retained_earnings_total = prior_years_net_income + current_year_net_income
            
            # Always add retained earnings to equity (even if zero, for display purposes)
            equity.append({
                'account_code': 'RE',
                'account_name': 'Retained Earnings',
                'balance': retained_earnings_total,
                'is_retained_earnings': True,
                'prior_years_net_income': prior_years_net_income,
                'current_year_net_income': current_year_net_income
            })
            
            # Calculate totals
            total_assets = sum(float(a.get('balance', 0)) for a in assets)
            total_liabilities = sum(float(l.get('balance', 0)) for l in liabilities)
            total_equity = sum(float(e.get('balance', 0)) for e in equity)
            total_liabilities_and_equity = total_liabilities + total_equity
            
            # Ensure totals balance - if they don't match, it's likely due to rounding or missing data
            # We'll use the calculated total_liabilities_and_equity for consistency
            print(f"DEBUG Balance Sheet: Totals - Assets: {total_assets}, Liabilities: {total_liabilities}, Equity: {total_equity}")
            print(f"DEBUG Balance Sheet: Total Liabilities + Equity: {total_liabilities_and_equity}")
            print(f"DEBUG Balance Sheet: Retained Earnings - Prior Years: {prior_years_net_income}, Current Year: {current_year_net_income}, Total: {retained_earnings_total}")
            
            # Determine year for response
            response_year = year if year else as_of_date.split('-')[0]
            
            return jsonify({
                'year': response_year,
                'as_of_date': as_of_date,
                'assets': assets,
                'total_assets': total_assets,
                'liabilities': liabilities,
                'total_liabilities': total_liabilities,
                'equity': equity,
                'total_equity': total_equity,
                'total_liabilities_and_equity': total_liabilities_and_equity,
                'retained_earnings': {
                    'prior_years_net_income': prior_years_net_income,
                    'current_year_net_income': current_year_net_income,
                    'total': retained_earnings_total
                }
            })
        except Exception as e:
            import traceback
            print(f"Error in balance sheet (Cosmos DB): {str(e)}")
            print(traceback.format_exc())
            return jsonify({'error': f'Error generating balance sheet: {str(e)}'}), 500
    
    try:
        as_of_date = request.args.get('as_of_date')
        
        if not as_of_date:
            as_of_date = date.today().isoformat()
        
        print(f"Balance Sheet Query - business_id: {business_id}, as_of_date: {as_of_date}")
        
        conn = get_db_connection()
        
        # Get all accounts by category
        accounts = conn.execute('''
        SELECT coa.id, coa.account_code, coa.account_name, at.category, at.normal_balance
        FROM chart_of_accounts coa
        JOIN account_types at ON coa.account_type_id = at.id
        WHERE coa.business_id = ? 
        AND at.category IN ('ASSET', 'LIABILITY', 'EQUITY')
        AND coa.is_active = 1
        ORDER BY at.category, coa.account_code
        ''', (business_id,)).fetchall()
        
        # Also get bank, credit card, and loan accounts
        bank_accounts = conn.execute('''
        SELECT id, account_name, current_balance, opening_balance, account_code
        FROM bank_accounts
        WHERE business_id = ? AND is_active = 1
        ''', (business_id,)).fetchall()
        
        credit_card_accounts = conn.execute('''
        SELECT id, account_name, current_balance, account_code
        FROM credit_card_accounts
        WHERE business_id = ? AND is_active = 1
        ''', (business_id,)).fetchall()
        
        loan_accounts = conn.execute('''
        SELECT id, account_name, current_balance, account_code
        FROM loan_accounts
        WHERE business_id = ? AND is_active = 1
        ''', (business_id,)).fetchall()
        
        assets = []
        liabilities = []
        equity = []
        
        # Process chart of accounts
        for account in accounts:
            account_id = account['id']
            account_dict = dict(account)
            
            # Calculate balance as of the date
            result = conn.execute('''
                SELECT 
                    COALESCE(SUM(tl.debit_amount), 0) as total_debits,
                    COALESCE(SUM(tl.credit_amount), 0) as total_credits
                FROM transaction_lines tl
                JOIN transactions t ON tl.transaction_id = t.id
                WHERE tl.chart_of_account_id = ?
                AND t.business_id = ?
                AND DATE(t.transaction_date) <= DATE(?)
            ''', (account_id, business_id, as_of_date)).fetchone()
            
            total_debits = result['total_debits'] or 0
            total_credits = result['total_credits'] or 0
            
            # Calculate balance based on normal balance
            if account['normal_balance'] == 'DEBIT':
                balance = total_debits - total_credits
            else:
                balance = total_credits - total_debits
            
            account_dict['balance'] = balance
            
            if account['category'] == 'ASSET':
                assets.append(account_dict)
            elif account['category'] == 'LIABILITY':
                liabilities.append(account_dict)
            else:  # EQUITY
                equity.append(account_dict)
        
        # Add bank accounts to assets - calculate balance from transaction lines
        for bank in bank_accounts:
            bank_dict = dict(bank)
            bank_id = bank_dict['id']
            bank_account_code = bank_dict.get('account_code') or f'BANK-{bank_id}'
            
            # Find the chart of account associated with this bank account
            # Try exact match first, then pattern match
            bank_chart_account = conn.execute('''
                SELECT id FROM chart_of_accounts 
                WHERE business_id = ? 
                AND account_code = ?
                LIMIT 1
            ''', (business_id, bank_account_code)).fetchone()
            
            # If not found, try pattern match
            if not bank_chart_account:
                bank_chart_account = conn.execute('''
                    SELECT id FROM chart_of_accounts 
                    WHERE business_id = ? 
                    AND (account_code LIKE ? OR account_code LIKE ?)
                    LIMIT 1
                ''', (business_id, f'BANK-{bank_id}-%', f'BANK-{bank_id}')).fetchone()
            
            # Get opening balance - check both opening_balance and current_balance fields
            opening_balance = bank_dict.get('opening_balance')
            if opening_balance is None:
                opening_balance = bank_dict.get('current_balance', 0)
            opening_balance = float(opening_balance or 0)
            balance = opening_balance
            
            if bank_chart_account:
                # Calculate balance from transaction lines
                result = conn.execute('''
                    SELECT 
                        COALESCE(SUM(tl.debit_amount), 0) as total_debits,
                        COALESCE(SUM(tl.credit_amount), 0) as total_credits
                    FROM transaction_lines tl
                    JOIN transactions t ON tl.transaction_id = t.id
                    WHERE tl.chart_of_account_id = ?
                    AND t.business_id = ?
                    AND DATE(t.transaction_date) <= DATE(?)
                ''', (bank_chart_account['id'], business_id, as_of_date)).fetchone()
                
                if result:
                    total_debits = float(result['total_debits'] or 0)
                    total_credits = float(result['total_credits'] or 0)
                    # Bank accounts are assets (normal balance DEBIT)
                    # Balance = opening balance + (debits - credits)
                    balance = opening_balance + (total_debits - total_credits)
            
            assets.append({
                'account_code': bank_account_code,
                'account_name': bank_dict['account_name'],
                'balance': balance,
                'is_bank_account': True
            })
    
        # Add credit card and loan accounts to liabilities
        for cc in credit_card_accounts:
            cc_dict = dict(cc)
            liabilities.append({
                'account_code': cc_dict.get('account_code') or f'CC-{cc_dict["id"]}',
                'account_name': cc_dict['account_name'],
                'balance': float(cc_dict.get('current_balance') or 0),
                'is_credit_card': True
            })
        
        for loan in loan_accounts:
            loan_dict = dict(loan)
            liabilities.append({
                'account_code': loan_dict.get('account_code') or f'LOAN-{loan_dict["id"]}',
                'account_name': loan_dict['account_name'],
                'balance': float(loan_dict.get('current_balance') or 0),
                'is_loan': True
            })
        
        total_assets = sum(float(a['balance']) for a in assets)
        total_liabilities = sum(float(l['balance']) for l in liabilities)
        total_equity = sum(float(e['balance']) for e in equity)
        
        # Calculate retained earnings from P&L if needed
        # This is a simplified version - in a full system, you'd track retained earnings separately
        
        conn.close()
        
        return jsonify({
            'as_of_date': as_of_date,
            'assets': assets,
            'total_assets': total_assets,
            'liabilities': liabilities,
            'total_liabilities': total_liabilities,
            'equity': equity,
            'total_equity': total_equity,
            'total_liabilities_and_equity': total_liabilities + total_equity
        })
    except Exception as e:
        import traceback
        print(f"Error in balance sheet: {str(e)}")
        print(traceback.format_exc())
        if 'conn' in locals():
            conn.close()
        return jsonify({'error': f'Error generating balance sheet: {str(e)}'}), 500

# ========== STATIC FILE SERVING (Single Server Mode) ==========

def register_static_routes():
    """Register routes to serve static frontend files."""
    if not SERVE_STATIC:
        return
    
    if not os.path.exists(FRONTEND_BUILD_DIR):
        print(f"WARNING: SERVE_STATIC is True but frontend build directory does not exist at {FRONTEND_BUILD_DIR}")
        return
    
    print(f"DEBUG: Registering static file routes for {FRONTEND_BUILD_DIR}")
    
    @app.route('/')
    def serve_index():
        """Serve the React frontend index.html for root path."""
        return send_from_directory(FRONTEND_BUILD_DIR, 'index.html')
    
    # Serve static assets (JS, CSS, images, etc.)
    @app.route('/assets/<path:filename>')
    def serve_assets(filename):
        """Serve static assets from the assets directory."""
        return send_from_directory(os.path.join(FRONTEND_BUILD_DIR, 'assets'), filename)
    
    # Catch-all route for React Router (must be registered last)
    @app.route('/<path:path>')
    def serve_frontend(path):
        """Serve the React frontend for all non-API routes."""
        # Don't serve API routes as static files
        if path.startswith('api/'):
            return jsonify({'error': 'Not found'}), 404
        
        # Check if it's a static file that exists
        if '.' in path and not path.endswith('/'):
            file_path = os.path.join(FRONTEND_BUILD_DIR, path)
            if os.path.exists(file_path) and os.path.isfile(file_path):
                return send_from_directory(FRONTEND_BUILD_DIR, path)
        
        # For all other routes (React Router), serve index.html
        return send_from_directory(FRONTEND_BUILD_DIR, 'index.html')

# Register static routes if in single-server mode
register_static_routes()

if __name__ == '__main__':
    # In production mode, serve static files from Flask
    # In development mode, use Vite dev server separately
    debug_mode = not SERVE_STATIC
    port = int(os.environ.get('PORT', 5001))
    
    if SERVE_STATIC:
        print("=" * 50)
        print("Running in SINGLE SERVER mode")
        print(f"Frontend build directory: {FRONTEND_BUILD_DIR}")
        if not os.path.exists(FRONTEND_BUILD_DIR):
            print(f"ERROR: Frontend build directory not found!")
            print(f"Run 'cd frontend && npm run build' to build the frontend")
            sys.exit(1)
        
        # Verify routes are registered
        static_routes = [r for r in app.url_map.iter_rules() if not r.rule.startswith('/api')]
        print(f"Registered {len(static_routes)} static file routes")
        if len(static_routes) == 0:
            print("WARNING: No static file routes registered!")
        else:
            print("Static routes:", [r.rule for r in static_routes[:3]])
        
        print(f"Server running on: http://0.0.0.0:{port}")
        print("=" * 50)
    else:
        print("=" * 50)
        print("Running in DEVELOPMENT mode (separate servers)")
        print("Backend API: http://0.0.0.0:5001")
        print("Frontend Dev Server: http://0.0.0.0:3000 (run separately)")
        print("=" * 50)
    
    app.run(debug=debug_mode, port=port, host='0.0.0.0')

