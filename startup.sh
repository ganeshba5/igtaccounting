#!/bin/bash
# Azure App Service startup script
# This file should be placed in the root of your repository

# Install dependencies if not already installed
if [ -f "azure-app-service-requirements.txt" ]; then
    pip install -r azure-app-service-requirements.txt
fi

# Set production environment
export FLASK_ENV=production
export BUILD_FRONTEND=1

# Start Flask app using Gunicorn (recommended for production)
# Gunicorn should be in azure-app-service-requirements.txt
if command -v gunicorn &> /dev/null; then
    cd backend || exit 1
    gunicorn --bind 0.0.0.0:8000 --workers 4 --timeout 120 --access-logfile - --error-logfile - app:app
else
    echo "Warning: Gunicorn not found. Using Flask development server (not recommended for production)"
    echo "Install Gunicorn: pip install gunicorn"
    cd backend || exit 1
    python -m flask run --host=0.0.0.0 --port=8000
fi

