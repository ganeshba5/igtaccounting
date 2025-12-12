#!/usr/bin/env python3
"""
Script to add users to the database from the command line.

Usage:
    # SQLite
    python add_user.py --first-name "John" --last-name "Doe" --email "john.doe@company.com" --business-ids 1,2,3

    # Cosmos DB
    export USE_COSMOS_DB=1
    export COSMOS_ENDPOINT="https://your-account.documents.azure.com:443/"
    export COSMOS_KEY="your-key"
    python add_user.py --first-name "John" --last-name "Doe" --email "john.doe@company.com" --business-ids 1,2,3

    # Update existing user's business access
    python add_user.py --email "john.doe@company.com" --business-ids 1,2,3,4 --update

    # List all users
    python add_user.py --list

    # Show user details
    python add_user.py --email "john.doe@company.com" --show
"""

import os
import sys
import argparse
import json
from datetime import datetime, timezone

# Add backend directory to Python path
backend_dir = os.path.join(os.path.dirname(__file__), 'backend')
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Check if using Cosmos DB
USE_COSMOS_DB = os.environ.get('USE_COSMOS_DB') == '1'

if USE_COSMOS_DB:
    from database_cosmos import get_item, create_item, update_item, query_items, get_container, init_database as cosmos_init_database
else:
    import sqlite3
    from database import get_db_connection, init_database


def get_user_by_email(email):
    """Get user by email address."""
    if USE_COSMOS_DB:
        try:
            user = get_item('users', email, partition_key=email)
            if user and user.get('type') == 'user':
                return user
        except Exception as e:
            # Container might not exist yet
            if 'NotFound' in str(type(e).__name__) or 'Resource Not Found' in str(e):
                return None
            pass
        
        # Fallback: query by email
        try:
            users = query_items(
                'users',
                'SELECT * FROM c WHERE c.type = "user" AND c.email = @email',
                [{"name": "@email", "value": email}],
                partition_key=email
            )
            return users[0] if users else None
        except Exception as e:
            # Container might not exist yet
            if 'NotFound' in str(type(e).__name__) or 'Resource Not Found' in str(e):
                return None
            raise
    else:
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        conn.close()
        return dict(user) if user else None


def create_user(first_name, last_name, email, business_ids):
    """Create a new user."""
    if USE_COSMOS_DB:
        # Initialize database/containers if needed
        try:
            cosmos_init_database()
        except Exception as e:
            # Container might already exist, that's fine
            pass
        
        user_doc = {
            'id': email,  # Use email as id and partition key
            'type': 'user',
            'first_name': first_name,
            'last_name': last_name,
            'email': email,
            'business_ids': business_ids,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'updated_at': datetime.now(timezone.utc).isoformat()
        }
        
        try:
            created = create_item('users', user_doc, partition_key=email)
            print(f"✅ User created successfully!")
            print(f"   Email: {created['email']}")
            print(f"   Name: {created['first_name']} {created['last_name']}")
            print(f"   Business IDs: {created['business_ids']}")
            return created
        except Exception as e:
            print(f"❌ Error creating user: {e}")
            sys.exit(1)
    else:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Convert business_ids list to JSON string
        business_ids_json = json.dumps(business_ids)
        
        try:
            cursor.execute(
                'INSERT INTO users (first_name, last_name, email, business_ids) VALUES (?, ?, ?, ?)',
                (first_name, last_name, email, business_ids_json)
            )
            conn.commit()
            user_id = cursor.lastrowid
            
            user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
            conn.close()
            
            print(f"✅ User created successfully!")
            print(f"   ID: {user['id']}")
            print(f"   Email: {user['email']}")
            print(f"   Name: {user['first_name']} {user['last_name']}")
            print(f"   Business IDs: {json.loads(user['business_ids'])}")
            return dict(user)
        except sqlite3.IntegrityError as e:
            print(f"❌ Error: User with email '{email}' already exists")
            conn.close()
            sys.exit(1)
        except Exception as e:
            print(f"❌ Error creating user: {e}")
            conn.close()
            sys.exit(1)


def update_user(email, business_ids=None, first_name=None, last_name=None):
    """Update an existing user."""
    user = get_user_by_email(email)
    if not user:
        print(f"❌ User with email '{email}' not found")
        sys.exit(1)
    
    if USE_COSMOS_DB:
        if business_ids is not None:
            user['business_ids'] = business_ids
        if first_name is not None:
            user['first_name'] = first_name
        if last_name is not None:
            user['last_name'] = last_name
        user['updated_at'] = datetime.now(timezone.utc).isoformat()
        
        try:
            updated = update_item('users', user, partition_key=email)
            print(f"✅ User updated successfully!")
            print(f"   Email: {updated['email']}")
            print(f"   Name: {updated['first_name']} {updated['last_name']}")
            print(f"   Business IDs: {updated['business_ids']}")
            return updated
        except Exception as e:
            print(f"❌ Error updating user: {e}")
            sys.exit(1)
    else:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        updates = []
        values = []
        
        if business_ids is not None:
            updates.append('business_ids = ?')
            values.append(json.dumps(business_ids))
        if first_name is not None:
            updates.append('first_name = ?')
            values.append(first_name)
        if last_name is not None:
            updates.append('last_name = ?')
            values.append(last_name)
        
        if not updates:
            print("❌ No updates specified")
            conn.close()
            sys.exit(1)
        
        updates.append('updated_at = CURRENT_TIMESTAMP')
        values.append(email)
        
        query = f'UPDATE users SET {", ".join(updates)} WHERE email = ?'
        cursor.execute(query, values)
        
        if cursor.rowcount == 0:
            print(f"❌ User with email '{email}' not found")
            conn.close()
            sys.exit(1)
        
        conn.commit()
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        conn.close()
        
        print(f"✅ User updated successfully!")
        print(f"   ID: {user['id']}")
        print(f"   Email: {user['email']}")
        print(f"   Name: {user['first_name']} {user['last_name']}")
        print(f"   Business IDs: {json.loads(user['business_ids'])}")
        return dict(user)


def list_users():
    """List all users."""
    if USE_COSMOS_DB:
        try:
            # Note: Users container is partitioned by email, so we need to query without partition key
            # This requires a cross-partition query which is handled by not specifying partition_key
            users = query_items(
                'users',
                'SELECT * FROM c WHERE c.type = "user" ORDER BY c.email',
                [],
                partition_key=None  # Cross-partition query
            )
        except Exception as e:
            # Container might not exist yet
            if 'NotFound' in str(type(e).__name__) or 'Resource Not Found' in str(e):
                print("No users container found. Initialize database first or create a user.")
                users = []
            else:
                raise
    else:
        conn = get_db_connection()
        users = conn.execute('SELECT * FROM users ORDER BY email').fetchall()
        conn.close()
        users = [dict(u) for u in users]
    
    if not users:
        print("No users found in database")
        return
    
    print(f"\n📋 Found {len(users)} user(s):\n")
    print(f"{'Email':<40} {'Name':<30} {'Business IDs':<20}")
    print("-" * 90)
    
    for user in users:
        email = user.get('email', 'N/A')
        first_name = user.get('first_name', '')
        last_name = user.get('last_name', '')
        name = f"{first_name} {last_name}".strip()
        
        business_ids = user.get('business_ids', [])
        if isinstance(business_ids, str):
            try:
                business_ids = json.loads(business_ids)
            except:
                business_ids = []
        business_ids_str = ', '.join(map(str, business_ids)) if business_ids else 'None'
        
        print(f"{email:<40} {name:<30} {business_ids_str:<20}")


def show_user(email):
    """Show details of a specific user."""
    user = get_user_by_email(email)
    if not user:
        print(f"❌ User with email '{email}' not found")
        sys.exit(1)
    
    print(f"\n👤 User Details:\n")
    print(f"   Email: {user.get('email')}")
    print(f"   First Name: {user.get('first_name')}")
    print(f"   Last Name: {user.get('last_name')}")
    
    business_ids = user.get('business_ids', [])
    if isinstance(business_ids, str):
        try:
            business_ids = json.loads(business_ids)
        except:
            business_ids = []
    
    print(f"   Business IDs: {business_ids}")
    print(f"   Created: {user.get('created_at', 'N/A')}")
    print(f"   Updated: {user.get('updated_at', 'N/A')}")


def parse_business_ids(business_ids_str):
    """Parse business IDs from comma-separated string."""
    if not business_ids_str:
        return []
    try:
        return [int(bid.strip()) for bid in business_ids_str.split(',') if bid.strip()]
    except ValueError:
        print(f"❌ Error: Invalid business IDs format. Use comma-separated integers (e.g., '1,2,3')")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description='Manage users in the accounting application database',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument('--first-name', help='User first name')
    parser.add_argument('--last-name', help='User last name')
    parser.add_argument('--email', help='User email (must match Microsoft SSO email)')
    parser.add_argument('--business-ids', help='Comma-separated list of business IDs (e.g., "1,2,3")')
    parser.add_argument('--update', action='store_true', help='Update existing user instead of creating')
    parser.add_argument('--list', action='store_true', help='List all users')
    parser.add_argument('--show', action='store_true', help='Show user details')
    
    args = parser.parse_args()
    
    # Check database type
    db_type = "Cosmos DB" if USE_COSMOS_DB else "SQLite"
    print(f"📊 Using {db_type} database\n")
    
    # Initialize database/containers if needed
    if USE_COSMOS_DB:
        try:
            cosmos_init_database()
            print("✅ Database initialized (containers created if needed)\n")
        except Exception as e:
            print(f"⚠️  Note: {e}\n")
    else:
        # Initialize SQLite database (creates tables if needed)
        init_database()
    
    if args.list:
        list_users()
        return
    
    if args.show:
        if not args.email:
            print("❌ Error: --email is required with --show")
            sys.exit(1)
        show_user(args.email)
        return
    
    if not args.email:
        print("❌ Error: --email is required (except when using --list)")
        sys.exit(1)
    
    if args.update:
        
        business_ids = None
        if args.business_ids:
            business_ids = parse_business_ids(args.business_ids)
        
        update_user(
            email=args.email,
            business_ids=business_ids,
            first_name=args.first_name,
            last_name=args.last_name
        )
    else:
        # Create new user
        if not args.first_name or not args.last_name:
            print("❌ Error: --first-name and --last-name are required for creating a user")
            sys.exit(1)
        
        business_ids = parse_business_ids(args.business_ids) if args.business_ids else []
        
        # Check if user already exists
        existing = get_user_by_email(args.email)
        if existing:
            print(f"⚠️  User with email '{args.email}' already exists")
            print("   Use --update flag to update existing user")
            sys.exit(1)
        
        create_user(args.first_name, args.last_name, args.email, business_ids)


if __name__ == '__main__':
    main()

