#!/bin/bash

# Auto-restart wrapper for Mushussu
# Usage: bash run.sh

while true; do
    python bot.py
    exit_code=$?

    if [ $exit_code -eq 42 ]; then
        echo "🔄 Restart requested (exit code 42), restarting in 2 seconds..."
        sleep 2
    else
        echo "🛑 Bot stopped with exit code $exit_code"
        break
    fi
done
