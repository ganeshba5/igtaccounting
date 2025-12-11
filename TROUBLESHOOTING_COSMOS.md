# Cosmos DB Troubleshooting Guide

## Common Errors and Solutions

### Error: "Incorrect padding" or "binascii.Error: Incorrect padding"

**Cause**: The `COSMOS_KEY` environment variable has formatting issues (extra spaces, quotes, or missing padding).

**Solution**:

1. **Check your key in Azure Portal**:
   - Go to Azure Portal → Your Cosmos DB account
   - Click "Keys" in the left menu
   - Copy the **PRIMARY KEY** (click the copy icon, don't manually select)

2. **Set the key properly**:
   ```bash
   # Remove any quotes or extra spaces
   export COSMOS_KEY="your-key-here-without-quotes-or-spaces"
   ```

3. **Verify the key**:
   ```bash
   echo $COSMOS_KEY
   # Should show the key without leading/trailing spaces
   ```

4. **Common issues**:
   - ❌ `export COSMOS_KEY=" 'your-key' "` (extra quotes/spaces)
   - ✅ `export COSMOS_KEY=your-actual-key-here`
   - ❌ Key copied with line breaks
   - ✅ Key should be one continuous string

### Error: "COSMOS_ENDPOINT and COSMOS_KEY must be set"

**Solution**:
```bash
export COSMOS_ENDPOINT="https://your-account.documents.azure.com:443/"
export COSMOS_KEY="your-primary-key"
export USE_COSMOS_DB=1
```

### Error: "Invalid COSMOS_KEY format"

**Cause**: The key is not a valid base64 string.

**Solution**:
1. Copy the key directly from Azure Portal (use copy button)
2. Don't manually type or modify the key
3. Ensure no spaces or special characters were added

### Error: Connection timeout or "Resource not found"

**Causes**:
- Wrong endpoint URL
- Wrong key
- Network/firewall issues
- Cosmos DB account doesn't exist

**Solution**:
1. Verify endpoint format: `https://account-name.documents.azure.com:443/`
2. Verify you're using the correct region/endpoint
3. Check Azure Portal that the account is active
4. Verify network connectivity

## Testing Your Connection

### Test 1: Verify Environment Variables
```bash
echo "Endpoint: $COSMOS_ENDPOINT"
echo "Key: ${COSMOS_KEY:0:10}..." # Show first 10 chars only
echo "Use Cosmos: $USE_COSMOS_DB"
```

### Test 2: Test Connection with Python
```python
from azure.cosmos import CosmosClient
import os

endpoint = os.environ.get('COSMOS_ENDPOINT', '').strip().strip('"').strip("'")
key = os.environ.get('COSMOS_KEY', '').strip().strip('"').strip("'")

# Clean key
key = key.replace('\n', '').replace('\r', '').replace(' ', '')
missing_padding = len(key) % 4
if missing_padding:
    key += '=' * (4 - missing_padding)

try:
    client = CosmosClient(endpoint, key)
    databases = list(client.list_databases())
    print(f"✅ Connection successful! Found {len(databases)} databases.")
except Exception as e:
    print(f"❌ Connection failed: {e}")
```

### Test 3: Test with Migration Script
```bash
python3 migrate_to_cosmos.py
```

## Best Practices

1. **Use a `.env` file** (but don't commit it):
   ```bash
   # .env
   COSMOS_ENDPOINT=https://your-account.documents.azure.com:443/
   COSMOS_KEY=your-key-here
   USE_COSMOS_DB=1
   ```

2. **Load .env in your script**:
   ```python
   from dotenv import load_dotenv
   load_dotenv()
   ```

3. **Never commit keys to git**:
   - Add `.env` to `.gitignore`
   - Use environment variables in production
   - Use Azure Key Vault for production

4. **Validate before running**:
   ```bash
   if [ -z "$COSMOS_ENDPOINT" ] || [ -z "$COSMOS_KEY" ]; then
       echo "Error: Cosmos DB credentials not set"
       exit 1
   fi
   ```

## Getting Help

If issues persist:

1. Check Azure Portal that your Cosmos DB account is active
2. Verify the account name and region
3. Check that you have the correct subscription
4. Review Azure Cosmos DB logs in Azure Portal
5. Test with Azure CLI:
   ```bash
   az cosmosdb show --name your-account-name --resource-group your-rg
   ```

