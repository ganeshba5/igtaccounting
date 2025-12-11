#!/bin/bash
cd "$(dirname "$0")"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Check for required Cosmos DB environment variables
if [ -z "$COSMOS_ENDPOINT" ] || [ -z "$COSMOS_KEY" ]; then
    echo "❌ Error: Cosmos DB environment variables not set!"
    echo ""
    echo "Please set the following environment variables:"
    echo "  export COSMOS_ENDPOINT='https://your-account.documents.azure.com:443/'"
    echo "  export COSMOS_KEY='your-primary-key'"
    echo "  export DATABASE_NAME='accounting-db'  # Optional, defaults to 'accounting-db'"
    echo ""
    echo "Get these values from: Azure Portal → Cosmos DB account → Keys"
    exit 1
fi

# Check for placeholder values
if [[ "$COSMOS_ENDPOINT" == *"your-endpoint"* ]] || [[ "$COSMOS_ENDPOINT" == *"your-account"* ]] || \
   [[ "$COSMOS_KEY" == *"your-key"* ]] || [[ "$COSMOS_KEY" == *"your-primary-key"* ]]; then
    echo "❌ Error: Placeholder values detected!"
    echo ""
    echo "Please set REAL values from Azure Portal:"
    echo "  1. Go to Azure Portal → Your Cosmos DB account"
    echo "  2. Click 'Keys' in the left menu"
    echo "  3. Copy the URI (for COSMOS_ENDPOINT)"
    echo "  4. Copy the PRIMARY KEY (for COSMOS_KEY)"
    echo ""
    echo "Then set them:"
    echo "  export COSMOS_ENDPOINT='https://YOUR-ACTUAL-ACCOUNT.documents.azure.com:443/'"
    echo "  export COSMOS_KEY='YOUR-ACTUAL-PRIMARY-KEY'"
    echo ""
    exit 1
fi

# Enable Cosmos DB mode
export USE_COSMOS_DB=1

# Get and display IP address for LAN access
if command -v ipconfig &> /dev/null; then
    IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || echo "")
elif command -v hostname &> /dev/null; then
    IP=$(hostname -I | awk '{print $1}' 2>/dev/null || echo "")
else
    IP=$(ifconfig 2>/dev/null | grep "inet " | grep -v 127.0.0.1 | awk '{print $2}' | head -1)
fi

echo "=========================================="
echo "Starting Backend Server with Cosmos DB..."
echo "=========================================="
echo "Database: Azure Cosmos DB"
echo "Endpoint: $COSMOS_ENDPOINT"
if [ -n "$IP" ]; then
    echo "Local access: http://localhost:5001"
    echo "LAN access:   http://$IP:5001"
else
    echo "Local access: http://localhost:5001"
    echo "Run ./get_ip.sh to find your LAN IP address"
fi
echo "=========================================="
echo ""

cd backend
python3 app.py

