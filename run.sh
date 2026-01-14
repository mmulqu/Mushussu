#!/bin/bash
source ~/.venv/thoth/bin/activate
cd /mnt/c/Users/Mike/PycharmProjects/Thoth

while true; do
    python bot.py
    EXIT_CODE=$?
    echo "Bot exited with code $EXIT_CODE"
    if [ $EXIT_CODE -eq 42 ]; then
        echo "Restart requested, restarting in 2 seconds..."
        sleep 2
    else
        echo "Normal exit, stopping."
        break
    fi
done