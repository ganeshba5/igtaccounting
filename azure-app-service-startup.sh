#!/bin/bash
# Azure App Service startup script for Flask backend

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Install dependencies if requirements.txt exists
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
fi

# Set production environment
export FLASK_ENV=production
export BUILD_FRONTEND=1

# Start Flask app using Gunicorn (recommended for production)
# If Gunicorn is not installed, fall back to Flask's built-in server
if command -v gunicorn &> /dev/null; then
    gunicorn --bind 0.0.0.0:8000 --workers 4 --timeout 120 --access-logfile - --error-logfile - backend.app:app
else
    echo "Warning: Gunicorn not found. Using Flask development server (not recommended for production)"
    echo "Install Gunicorn: pip install gunicorn"
    python -m flask run --host=0.0.0.0 --port=8000
fi

