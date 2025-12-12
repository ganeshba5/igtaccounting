# User Management System

## Overview

The application now uses a user-based access control system. Only users in the `users` table/document collection can access the application, and each user can only access businesses they're assigned to.

## User Entity Structure

### Attributes

- **first_name** (TEXT, required): User's first name
- **last_name** (TEXT, required): User's last name  
- **email** (TEXT, required, unique): User's email address - must match their Microsoft SSO email
- **business_ids** (TEXT/JSON array): List of business IDs the user can access
- **created_at** (TIMESTAMP): Record creation timestamp
- **updated_at** (TIMESTAMP): Last update timestamp

### Database Schema

**SQLite:**
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    business_ids TEXT,  -- JSON array of business IDs: "[1, 2, 3]"
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

**Cosmos DB:**
```json
{
  "id": "user@example.com",  // email is used as id and partition key
  "type": "user",
  "first_name": "John",
  "last_name": "Doe",
  "email": "user@example.com",
  "business_ids": [1, 2, 3],  // Array of integers
  "created_at": "2025-12-11T...",
  "updated_at": "2025-12-11T..."
}
```

## Access Control Flow

1. **User signs in** with Microsoft SSO
2. **Backend validates token** (Microsoft authentication)
3. **Backend extracts email** from token (`preferred_username`, `email`, or `upn`)
4. **Backend checks if user exists** in `users` table
   - If not found → 403 Access Denied
   - If found → Continue
5. **For business-specific routes:**
   - Backend checks if user's `business_ids` contains the requested business_id
   - If not → 403 Access Denied
   - If yes → Allow access

## Example User Records

### SQLite Example
```sql
INSERT INTO users (first_name, last_name, email, business_ids) 
VALUES ('John', 'Doe', 'john.doe@company.com', '[1, 2]');
```

### Cosmos DB Example
```json
{
  "id": "john.doe@company.com",
  "type": "user",
  "first_name": "John",
  "last_name": "Doe",
  "email": "john.doe@company.com",
  "business_ids": [1, 2],
  "created_at": "2025-12-11T10:00:00Z",
  "updated_at": "2025-12-11T10:00:00Z"
}
```

## User Management

**Note**: User management is done **outside the application** for now (as requested). This means:

- Users must be manually inserted into the database
- Use SQL queries or Cosmos DB operations to add/update/remove users
- No API endpoints are provided for user management in the application

### Adding a User (SQLite)

```sql
INSERT INTO users (first_name, last_name, email, business_ids) 
VALUES ('Jane', 'Smith', 'jane.smith@company.com', '[1, 3, 5]');
```

### Adding a User (Cosmos DB)

Using Azure Portal Data Explorer or SDK:
```python
user_doc = {
    'id': 'jane.smith@company.com',
    'type': 'user',
    'first_name': 'Jane',
    'last_name': 'Smith',
    'email': 'jane.smith@company.com',
    'business_ids': [1, 3, 5],
    'created_at': datetime.utcnow().isoformat(),
    'updated_at': datetime.utcnow().isoformat()
}
create_item('users', user_doc, partition_key='jane.smith@company.com')
```

### Updating User Business Access

**SQLite:**
```sql
UPDATE users 
SET business_ids = '[1, 2, 3, 4]' 
WHERE email = 'john.doe@company.com';
```

**Cosmos DB:**
```python
user = get_user_by_email('john.doe@company.com')
user['business_ids'] = [1, 2, 3, 4]
user['updated_at'] = datetime.utcnow().isoformat()
update_item('users', user, partition_key='john.doe@company.com')
```

### Removing a User

**SQLite:**
```sql
DELETE FROM users WHERE email = 'user@example.com';
```

**Cosmos DB:**
```python
delete_item('users', 'user@example.com', partition_key='user@example.com')
```

## Security Features

1. **Email-based authentication**: User email from Microsoft token must match `users.email`
2. **Business-level access control**: Users can only access businesses in their `business_ids` list
3. **Automatic filtering**: `/api/businesses` endpoint only returns businesses the user has access to
4. **Route protection**: All business-specific routes check access before allowing operations

## Error Messages

### User Not Found
```
Status: 403 Forbidden
Response: {
  "error": "Access denied",
  "message": "Your email is not authorized to access this application. Please contact your administrator."
}
```

### Business Access Denied
```
Status: 403 Forbidden
Response: {
  "error": "Access denied",
  "message": "You do not have access to business {business_id}."
}
```

## Testing

1. **Add a test user:**
   ```sql
   INSERT INTO users (first_name, last_name, email, business_ids) 
   VALUES ('Test', 'User', 'your-email@domain.com', '[1]');
   ```

2. **Sign in** with that Microsoft account
3. **Verify access**: Should see only business with ID 1
4. **Try accessing business 2**: Should get 403 error

## Future Enhancements

- User management API endpoints (CRUD operations)
- Admin role for managing users
- User interface for user management
- Audit logging for user access
- Bulk user import/export

