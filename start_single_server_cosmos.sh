#!/bin/bash
cd "$(dirname "$0")"

# Check for required Cosmos DB environment variables
if [ -z "$COSMOS_ENDPOINT" ] || [ -z "$COSMOS_KEY" ]; then
    echo "❌ Error: Cosmos DB environment variables not set!"
    echo ""
    echo "Please set the following environment variables:"
    echo "  export COSMOS_ENDPOINT='https://your-account.documents.azure.com:443/'"
    echo "  export COSMOS_KEY='your-primary-key'"
    echo "  export DATABASE_NAME='accounting-db'  # Optional"
    echo ""
    exit 1
fi

# Enable Cosmos DB mode
export USE_COSMOS_DB=1

# Build frontend and serve from backend (production mode)
export BUILD_FRONTEND=1
export FLASK_ENV=production

echo "=========================================="
echo "Building Frontend..."
echo "=========================================="

# Build frontend
cd frontend
if [ ! -d "node_modules" ]; then
    echo "Installing frontend dependencies..."
    npm install
fi

echo "Building production bundle..."
npm run build

if [ $? -ne 0 ]; then
    echo "❌ Frontend build failed!"
    exit 1
fi

cd ..

echo ""
echo "=========================================="
echo "Starting Single Server (Cosmos DB Mode)..."
echo "=========================================="
echo "Database: Azure Cosmos DB"
echo "Endpoint: $COSMOS_ENDPOINT"
echo "Server: Single server mode (backend serves frontend)"
echo "=========================================="
echo ""

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

cd backend
python3 app.py

