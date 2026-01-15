#!/bin/bash
# Start the Novel Diff Viewer server

cd "$(dirname "$0")"

echo "======================================"
echo "   Novel Diff Viewer"
echo "======================================"
echo ""
echo "Starting server..."
echo "Repository: ${REPO_PATH:-/home/user/Mushussu}"
echo "Server will be available at: http://localhost:5000"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

python3 server.py
