#!/bin/bash
cd "$(dirname "$0")"

# Get and display IP address for LAN access
if command -v ipconfig &> /dev/null; then
    IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || echo "")
elif command -v hostname &> /dev/null; then
    IP=$(hostname -I | awk '{print $1}' 2>/dev/null || echo "")
else
    IP=$(ifconfig 2>/dev/null | grep "inet " | grep -v 127.0.0.1 | awk '{print $2}' | head -1)
fi

echo "=========================================="
echo "Starting Frontend Server..."
echo "=========================================="
if [ -n "$IP" ]; then
    echo "Local access: http://localhost:3000"
    echo "LAN access:   http://$IP:3000"
else
    echo "Local access: http://localhost:3000"
    echo "Run ./get_ip.sh to find your LAN IP address"
fi
echo "=========================================="
echo ""

cd frontend
npm run dev

