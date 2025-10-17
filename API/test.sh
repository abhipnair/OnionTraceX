#!/bin/bash
# Tor Service Verification Script

echo "=========================================="
echo "TOR SERVICE DIAGNOSTIC CHECK"
echo "=========================================="
echo ""

# Check if Tor service is active
echo "1. Checking Tor service status..."
systemctl is-active tor.service
echo ""

# Check for Tor instance services
echo "2. Checking for Tor instances..."
systemctl list-units "tor@*" --no-pager
echo ""

# Check if port 9050 is listening
echo "3. Checking if SOCKS port 9050 is listening..."
if sudo ss -tlnp | grep -q ":9050"; then
    echo "✓ Port 9050 is OPEN and listening"
    sudo ss -tlnp | grep ":9050"
else
    echo "✗ Port 9050 is NOT listening"
    echo "  Tor may not be running properly"
fi
echo ""

# Check if port 9051 is listening (Control port)
echo "4. Checking if Control port 9051 is listening..."
if sudo ss -tlnp | grep -q ":9051"; then
    echo "✓ Port 9051 is OPEN and listening"
    sudo ss -tlnp | grep ":9051"
else
    echo "✗ Port 9051 is NOT listening (optional - may not be configured)"
fi
echo ""

# Check Tor processes
echo "5. Checking Tor processes..."
if ps aux | grep -v grep | grep -q "tor"; then
    echo "✓ Tor process found:"
    ps aux | grep -v grep | grep "tor" | head -5
else
    echo "✗ No Tor process running"
fi
echo ""

# Check Tor logs
echo "6. Recent Tor logs (last 10 lines)..."
if [ -f "/var/log/tor/log" ]; then
    sudo tail -10 /var/log/tor/log
elif [ -f "/var/log/tor/notices.log" ]; then
    sudo tail -10 /var/log/tor/notices.log
else
    echo "Checking journalctl for Tor logs..."
    sudo journalctl -u tor@default -n 10 --no-pager
fi
echo ""

# Test connection with curl
echo "7. Testing Tor connection with curl..."
if command -v curl &> /dev/null; then
    echo "Attempting to connect through Tor..."
    timeout 30 curl --socks5-hostname 127.0.0.1:9050 https://check.torproject.org/api/ip 2>&1
    if [ $? -eq 0 ]; then
        echo "✓ Successfully connected through Tor!"
    else
        echo "✗ Failed to connect through Tor"
    fi
else
    echo "curl not found, skipping connection test"
fi
echo ""

echo "=========================================="
echo "DIAGNOSTIC CHECK COMPLETE"
echo "=========================================="
