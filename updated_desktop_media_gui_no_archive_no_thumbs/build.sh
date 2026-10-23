#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [ -f "../.venv/bin/activate" ]; then
    source ../.venv/bin/activate
elif [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
else
    echo "Warning: .venv/bin/activate not found. Attempting to build without it."
fi

pyinstaller --noconfirm --clean --windowed --name DesktopMediaGUI app.py
