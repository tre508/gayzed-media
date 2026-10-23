# Gayzed Media - New Device Setup Guide

This guide provides step-by-step instructions to set up the Gayzed Media project on a new device, ensuring uninterrupted development.

## Prerequisites

Ensure your new device has the following installed:
- **Operating System:** Linux (Zorin OS / Ubuntu-based recommended), Windows, or macOS.
- **Python:** Python 3.10+ (Python 3.12 recommended).
- **System Packages:** `ffmpeg` (essential for `yt-dlp` to merge audio and video formats).

## Setup Instructions

### 1. Transfer the Project
Copy or clone the `gayzed-media` project folder to your new device. You can place it anywhere, for example in `~/Projects/gayzed-media`.

### 2. Install System Dependencies (Linux/Zorin OS)
Open a terminal and install `ffmpeg` and Python virtual environment tools:
```bash
sudo apt update
sudo apt install -y ffmpeg python3-pip python3-venv desktop-file-utils libgtk-3-bin
```

### 3. Create a Virtual Environment
Navigate to the project directory and create a clean Python virtual environment:
```bash
cd ~/Projects/gayzed-media
python3 -m venv .venv
source .venv/bin/activate
```
*(On Windows, use `.venv\Scripts\activate`)*

### 4. Install Project Dependencies
With the virtual environment active, install the required Python packages:
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 5. Configuration & Environment Setup
The application persists settings in `~/.config/desktop-media-gui/settings.json`.
1. A template file is provided as `settings.example.json`.
2. You can manually copy it to the configuration directory:
```bash
mkdir -p ~/.config/desktop-media-gui
cp settings.example.json ~/.config/desktop-media-gui/settings.json
```
3. Edit the `output_dir` in the JSON file to point to an existing valid directory on your new device (e.g., `~/Videos/latest`).

### 6. Run the Application
You can launch the development version of the application by running:
```bash
python3 app.py
```
*(Alternatively, you can run the original starter script with `python3 desktop_media_gui.py`)*

### 6b. Optional: Ubuntu Start Menu Integration (Launcher + Icon)
Follow [UBUNTU_DESKTOP_ICON_SETUP.md](file:///run/media/treshen/Expansion/storage%20backup/gayzed-media/UBUNTU_DESKTOP_ICON_SETUP.md) to install the `.desktop` entry and icon set so the app appears in GNOME Activities Overview.

### 7. Build for Production
To build a standalone executable using PyInstaller:
```bash
chmod +x build.sh
./build.sh
```
The compiled executable will be located in the `dist/` directory.
