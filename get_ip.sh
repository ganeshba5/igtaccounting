#!/bin/bash
# Get the local IP address for LAN access

# Try to get IP address (works on macOS and Linux)
if command -v ipconfig &> /dev/null; then
    # macOS
    IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || echo "")
elif command -v hostname &> /dev/null; then
    # Linux alternative
    IP=$(hostname -I | awk '{print $1}' 2>/dev/null || echo "")
else
    # Fallback to ifconfig
    IP=$(ifconfig 2>/dev/null | grep "inet " | grep -v 127.0.0.1 | awk '{print $2}' | head -1)
fi

if [ -z "$IP" ]; then
    echo "Could not determine IP address. Please check your network settings."
    exit 1
fi

echo "=========================================="
echo "Local IP Address: $IP"
echo "=========================================="
echo ""
echo "Access the application from other devices on your LAN:"
echo "  Frontend: http://$IP:3000"
echo "  Backend API: http://$IP:5001"
echo ""
echo "Make sure both servers are running:"
echo "  - Backend: ./start_backend.sh"
echo "  - Frontend: ./start_frontend.sh"
echo "=========================================="

