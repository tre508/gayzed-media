#!/usr/bin/env bash
set -euo pipefail

# Navigate to the directory where the script is located
cd "$(dirname "$0")"

# Activate the virtual environment if it exists, otherwise warn
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
else
    echo "Warning: .venv/bin/activate not found. Attempting to build without it."
fi

# Build the executable using PyInstaller
pyinstaller \
    --noconfirm \
    --clean \
    --windowed \
    --name DesktopMediaGUI \
    --add-data "assets/icons/hicolor:assets/icons/hicolor" \
    app.py
