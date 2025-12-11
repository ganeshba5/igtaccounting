# Quick Fix: Business Not Found Error

## Issue
When clicking on a business, getting "Business not found" error.

## Cause
The `get_business` function in Cosmos DB mode was using the wrong partition key. Businesses container uses `/id` as partition key, but we were querying by `business_id`.

## Fix Applied
Updated `cosmos_get_business()` to use cross-partition query when looking up by `business_id`.

## Action Required
**Restart the backend server** for changes to take effect:

```bash
# Stop the current server (Ctrl+C)
# Then restart:
./start_backend_cosmos.sh
```

## Testing
After restart, test:
```bash
curl http://localhost:5001/api/businesses/1
```

Should return the business details.

