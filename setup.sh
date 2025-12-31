#!/bin/bash
# Thoth Agent Setup Script
# Run this after cloning the repo

set -e

echo "=== Thoth Agent Setup ==="
echo

# Check for Python
if ! command -v python &> /dev/null; then
    echo "❌ Python not found. Please install Python 3.10+"
    exit 1
fi

PYTHON_VERSION=$(python -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "✓ Python $PYTHON_VERSION"

# Check for Node.js (required for Claude Code CLI)
if ! command -v node &> /dev/null; then
    echo "❌ Node.js not found. Please install Node.js 18+"
    echo "  curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -"
    echo "  sudo apt-get install -y nodejs"
    exit 1
fi

NODE_VERSION=$(node --version)
echo "✓ Node.js $NODE_VERSION"

# Install Python dependencies
echo
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Install Claude Code CLI
echo
echo "Installing Claude Code CLI..."
if ! command -v claude &> /dev/null; then
    npm install -g @anthropic-ai/claude-code
fi
echo "✓ Claude Code CLI installed"

# Create logs directory
mkdir -p logs

# Check for API key
echo
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "⚠️  ANTHROPIC_API_KEY not set"
    echo "   Set it with: export ANTHROPIC_API_KEY=your-key"
    echo "   Or add to ~/.bashrc for persistence"
else
    echo "✓ ANTHROPIC_API_KEY is set"
fi

echo
echo "=== Setup Complete ==="
echo
echo "To test the agent:"
echo "  python bot.py cli"
echo
echo "To run the server:"
echo "  python bot.py"
echo
echo "To install as a system service:"
echo "  1. Edit thoth.service (update username, paths, API key)"
echo "  2. sudo cp thoth.service /etc/systemd/system/"
echo "  3. sudo systemctl daemon-reload"
echo "  4. sudo systemctl enable thoth"
echo "  5. sudo systemctl start thoth"
echo
echo "To set up perch time cron:"
echo "  crontab -e"
echo "  Add: 0 */2 * * * curl -s -X POST http://localhost:8787/perch"
