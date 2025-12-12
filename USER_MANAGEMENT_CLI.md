# User Management - Command Line Guide

## Quick Start

A Python script `add_user.py` is provided to manage users from the command line.

## Prerequisites

1. **For SQLite**: No additional setup needed
2. **For Cosmos DB**: Set environment variables:
   ```bash
   export USE_COSMOS_DB=1
   export COSMOS_ENDPOINT="https://your-account.documents.azure.com:443/"
   export COSMOS_KEY="your-primary-key"
   export DATABASE_NAME="accounting-db"  # Optional, defaults to 'accounting-db'
   ```

## Usage Examples

### Create a New User

**SQLite:**
```bash
python add_user.py \
  --first-name "John" \
  --last-name "Doe" \
  --email "john.doe@company.com" \
  --business-ids "1,2,3"
```

**Cosmos DB:**
```bash
export USE_COSMOS_DB=1
export COSMOS_ENDPOINT="https://your-account.documents.azure.com:443/"
export COSMOS_KEY="your-key"

python add_user.py \
  --first-name "John" \
  --last-name "Doe" \
  --email "john.doe@company.com" \
  --business-ids "1,2,3"
```

### Update User's Business Access

```bash
python add_user.py \
  --email "john.doe@company.com" \
  --business-ids "1,2,3,4" \
  --update
```

### Update User's Name

```bash
python add_user.py \
  --email "john.doe@company.com" \
  --first-name "Jane" \
  --last-name "Smith" \
  --update
```

### List All Users

```bash
python add_user.py --list
```

Output:
```
📋 Found 3 user(s):

Email                                     Name                          Business IDs      
------------------------------------------------------------------------------------------
john.doe@company.com                      John Doe                      1, 2, 3          
jane.smith@company.com                    Jane Smith                    1, 4              
admin@company.com                          Admin User                    1, 2, 3, 4, 5    
```

### Show User Details

```bash
python add_user.py --email "john.doe@company.com" --show
```

Output:
```
👤 User Details:

   Email: john.doe@company.com
   First Name: John
   Last Name: Doe
   Business IDs: [1, 2, 3]
   Created: 2025-12-11T10:00:00Z
   Updated: 2025-12-11T10:00:00Z
```

## Command Reference

### Create User
```bash
python add_user.py \
  --first-name "First Name" \
  --last-name "Last Name" \
  --email "user@example.com" \
  --business-ids "1,2,3"
```

**Required flags:**
- `--first-name`: User's first name
- `--last-name`: User's last name
- `--email`: User's email (must match Microsoft SSO email)
- `--business-ids`: Comma-separated list of business IDs (optional, defaults to empty list)

### Update User
```bash
python add_user.py \
  --email "user@example.com" \
  --business-ids "1,2,3,4" \
  --update
```

**Optional flags:**
- `--business-ids`: Update business access list
- `--first-name`: Update first name
- `--last-name`: Update last name

### List Users
```bash
python add_user.py --list
```

### Show User
```bash
python add_user.py --email "user@example.com" --show
```

## Important Notes

1. **Email Must Match Microsoft SSO**: The email you use must exactly match the email in the user's Microsoft account used for SSO login.

2. **Business IDs**: 
   - Must be comma-separated integers (e.g., `"1,2,3"`)
   - User will only have access to businesses in this list
   - Empty list means user can authenticate but has no business access

3. **Case Sensitivity**: Email matching is case-sensitive. Make sure the email matches exactly what Microsoft returns.

4. **Existing Users**: If you try to create a user that already exists, you'll get an error. Use `--update` to modify existing users.

## Examples

### Example 1: Add User with Access to Multiple Businesses
```bash
python add_user.py \
  --first-name "Alice" \
  --last-name "Johnson" \
  --email "alice.johnson@company.com" \
  --business-ids "1,2,5,7"
```

### Example 2: Add User with No Business Access (Admin/Viewer)
```bash
python add_user.py \
  --first-name "Admin" \
  --last-name "User" \
  --email "admin@company.com"
  # No --business-ids means empty list
```

### Example 3: Grant Additional Business Access
```bash
# User currently has access to businesses 1, 2, 3
# Add business 4 to their access
python add_user.py \
  --email "john.doe@company.com" \
  --business-ids "1,2,3,4" \
  --update
```

### Example 4: Remove Business Access
```bash
# User currently has access to businesses 1, 2, 3, 4
# Remove business 4 from their access
python add_user.py \
  --email "john.doe@company.com" \
  --business-ids "1,2,3" \
  --update
```

## Troubleshooting

### Error: "User with email 'xxx' already exists"
- Use `--update` flag to update existing user
- Or check existing user with `--show` flag

### Error: "User with email 'xxx' not found" (when updating)
- Check email spelling
- Use `--list` to see all users
- Make sure you're using the correct email

### Error: "Invalid business IDs format"
- Use comma-separated integers: `"1,2,3"`
- Don't use spaces or brackets: `"[1, 2, 3]"` ❌
- Use: `"1,2,3"` ✅

### Error: "No module named 'database_cosmos'"
- Make sure you're in the project root directory
- For Cosmos DB, ensure `USE_COSMOS_DB=1` is set
- Check that `database_cosmos.py` exists in `backend/` directory

## Direct Database Access

If you prefer to work directly with the database:

### SQLite
```bash
sqlite3 accounting.db

# Insert user
INSERT INTO users (first_name, last_name, email, business_ids) 
VALUES ('John', 'Doe', 'john.doe@company.com', '[1, 2, 3]');

# Update user
UPDATE users 
SET business_ids = '[1, 2, 3, 4]' 
WHERE email = 'john.doe@company.com';

# List users
SELECT * FROM users;
```

### Cosmos DB
Use Azure Portal Data Explorer or Azure CLI to manage users directly.

