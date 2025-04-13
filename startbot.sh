#!/bin/bash
set -e

cd /home/container

# === CONFIG SECTION ===
AUTO_RESTART=true     # Set to false to disable full script restart
RESTART_DELAY=10      # Delay before restart
PYTHON_FILE="bot.py"  # Entry point
# =======================

while true; do
    echo "==============================="
    echo "[*] Running Discord bot setup..."
    echo "==============================="

    # Create venv if missing
    if [ ! -d "venv" ]; then
        echo "[*] Creating virtual environment..."
        python -m venv venv
    fi

    # Activate venv
    echo "[*] Activating virtual environment..."
    source venv/bin/activate

    # Install requirements
    if [ -f "requirements.txt" ]; then
        echo "[*] Installing Python packages from requirements.txt..."
        pip install --upgrade pip
        pip install -r requirements.txt
    else
        echo "[!] No requirements.txt found, skipping package install."
    fi

    # Run the bot
    echo "[*] Starting $PYTHON_FILE..."
    python "$PYTHON_FILE"

    if [ "$AUTO_RESTART" != "true" ]; then
        echo "[*] Auto-restart disabled. Exiting."
        break
    fi

    echo "[!] Bot exited. Restarting full workflow in $RESTART_DELAY seconds..."
    sleep "$RESTART_DELAY"
done
