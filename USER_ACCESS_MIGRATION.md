# User Access Control Migration - Complete

## Summary

The passphrase feature has been completely removed and replaced with a user-based access control system. Only users in the `users` table/document collection can access the application, and each user can only access businesses assigned to them.

## Changes Made

### Backend Changes

1. **Removed Passphrase Feature:**
   - Removed all passphrase-related code from `backend/app.py`
   - Removed `bcrypt` from `requirements.txt`
   - Removed `passphrase_hash` field from businesses table
   - Removed passphrase verification endpoint
   - Removed `require_business_passphrase` decorator

2. **Added User Management:**
   - Created `users` table (SQLite) with columns: `id`, `first_name`, `last_name`, `email`, `business_ids`, `created_at`, `updated_at`
   - Created `users` container (Cosmos DB) with partition key `/email`
   - Added `get_user_by_email()` function to fetch users by email
   - Added `user_has_business_access()` function to check business access
   - Added `require_user_access` decorator for route protection

3. **Updated All Business Routes:**
   - Added `@require_user_access` decorator to all business-specific routes
   - Routes now check:
     1. User exists in `users` table
     2. User has access to the requested business (if business_id is present)

4. **Updated Business Listing:**
   - `/api/businesses` now filters to show only businesses the user has access to
   - Returns empty list if user has no business access

### Frontend Changes

1. **Removed Passphrase Components:**
   - Deleted `PassphrasePrompt.jsx`
   - Deleted `PassphraseHandler.jsx`
   - Deleted `PassphraseContext.jsx`

2. **Updated Business List:**
   - Removed passphrase field from create/edit forms
   - Removed lock/unlock icons
   - Simplified business list table

3. **Updated API:**
   - Removed `verifyPassphrase` method from `api.js`

### Database Schema Changes

**SQLite:**
- Removed `passphrase_hash` column from `businesses` table
- Added `users` table

**Cosmos DB:**
- Removed `passphrase_hash` field from business documents
- Added `users` container

## User Entity Structure

```javascript
{
  id: 1,  // Auto-increment (SQLite) or email (Cosmos DB)
  first_name: "John",
  last_name: "Doe",
  email: "john.doe@company.com",  // Must match Microsoft SSO email
  business_ids: [1, 2, 3],  // Array of business IDs user can access
  created_at: "2025-12-11T...",
  updated_at: "2025-12-11T..."
}
```

## Access Control Flow

1. User signs in with Microsoft SSO
2. Backend validates Microsoft token
3. Backend extracts email from token
4. Backend checks if email exists in `users` table
   - **If not found**: Returns 403 "Access denied - Your email is not authorized"
   - **If found**: Continues
5. For business routes, backend checks if `business_id` is in user's `business_ids` list
   - **If not in list**: Returns 403 "Access denied - You do not have access to this business"
   - **If in list**: Allows access

## User Management (Outside Application)

Since user management is done outside the application, you'll need to manage users directly in the database:

### SQLite Example
```sql
-- Add user with access to businesses 1 and 2
INSERT INTO users (first_name, last_name, email, business_ids) 
VALUES ('John', 'Doe', 'john.doe@company.com', '[1, 2]');

-- Update user's business access
UPDATE users SET business_ids = '[1, 2, 3]' WHERE email = 'john.doe@company.com';

-- Remove user
DELETE FROM users WHERE email = 'john.doe@company.com';
```

### Cosmos DB Example
```python
# Add user
user_doc = {
    'id': 'john.doe@company.com',
    'type': 'user',
    'first_name': 'John',
    'last_name': 'Doe',
    'email': 'john.doe@company.com',
    'business_ids': [1, 2],
    'created_at': datetime.utcnow().isoformat(),
    'updated_at': datetime.utcnow().isoformat()
}
create_item('users', user_doc, partition_key='john.doe@company.com')
```

## Protected Routes

All these routes now require user authentication and business access:
- `GET /api/businesses` - Only returns businesses user has access to
- `POST /api/businesses` - Requires user access (no business_id check)
- `GET /api/businesses/<business_id>` - Requires access to that business
- `PUT /api/businesses/<business_id>` - Requires access to that business
- `DELETE /api/businesses/<business_id>` - Requires access to that business
- All `/api/businesses/<business_id>/*` routes - Require access to that business
- `GET /api/reports/combined-profit-loss` - Requires user access

## Next Steps

1. **Add users to database:**
   - Manually insert user records with their Microsoft SSO email
   - Set `business_ids` to the list of businesses they can access

2. **Test access control:**
   - Sign in with a user's Microsoft account
   - Verify they only see businesses in their `business_ids` list
   - Verify they cannot access businesses not in their list

3. **Monitor access:**
   - Check server logs for access denied messages
   - Review user business assignments regularly

## Notes

- **Email matching is case-sensitive** - Make sure the email in the `users` table matches exactly what Microsoft returns
- **Business IDs must be integers** - The `business_ids` array should contain integer business IDs
- **No passphrase recovery** - Users are managed externally, so there's no passphrase to recover
- **Combined P&L report** - This route requires user access but doesn't filter by business (shows all businesses user has access to)

