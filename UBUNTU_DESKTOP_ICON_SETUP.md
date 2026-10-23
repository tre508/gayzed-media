# Gayzed Media – Ubuntu Launcher Icon & Desktop Entry

This project ships a freedesktop.org-compliant application icon set (SVG + PNG sizes) and a `.desktop` entry template so the application shows up correctly in the Ubuntu Start Menu (GNOME Activities Overview) with a crisp icon on both standard-DPI and high-DPI displays.

## Icon Asset Layout (freedesktop.org / hicolor)

Base icon name: `gayzed-media`

- Scalable SVG:
  - `assets/icons/hicolor/scalable/apps/gayzed-media.svg`
- Raster PNG (standard sizes):
  - `assets/icons/hicolor/16x16/apps/gayzed-media.png`
  - `assets/icons/hicolor/32x32/apps/gayzed-media.png`
  - `assets/icons/hicolor/48x48/apps/gayzed-media.png`
  - `assets/icons/hicolor/64x64/apps/gayzed-media.png`
  - `assets/icons/hicolor/128x128/apps/gayzed-media.png`
  - (Optional) additional sizes like `256x256` / `512x512` can be added; the installer will skip missing sizes.

## Desktop Entry Template

- Template file in repo:
  - `packaging/gayzed-media.desktop`
- `Icon=gayzed-media` is intentionally extensionless and uses the icon theme resolver.

## Required Ubuntu Packages

These are needed for cache refresh and desktop entry validation:

```bash
sudo apt update
sudo apt install -y desktop-file-utils libgtk-3-bin
```

## Installation Options

### Option A: User Install (recommended for development)

This installs into:
- `~/.local/share/applications/`
- `~/.local/share/icons/hicolor/`
- `~/.local/bin/` (wrapper executable)

Run:

```bash
chmod +x tools/install_ubuntu_desktop_integration.sh
tools/install_ubuntu_desktop_integration.sh --user
```

Notes:
- The launcher wrapper will try to find a Python interpreter that can import `PySide6`. If it cannot, it writes a log at:
  - `~/.cache/gayzed-media/launcher.log` (or `$XDG_CACHE_HOME/gayzed-media/launcher.log`)
- For source installs, create a venv and install dependencies (example):
  - `python3.11 -m venv .venv`
  - `. .venv/bin/activate`
  - `pip install -r updated_desktop_media_gui_no_archive_no_thumbs/requirements.txt`

### Option A2: User Install (packaged binary)

If you are running the PyInstaller build from `dist/`, install a launcher that runs the packaged binary:

```bash
chmod +x tools/install_ubuntu_desktop_integration.sh
tools/install_ubuntu_desktop_integration.sh --user --packaged
```

If `~/.local/bin` is not on your `PATH`, add this to your shell profile and log out/in:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

### Option B: System Install (for shared machines)

This installs into:
- `/usr/share/applications/`
- `/usr/share/icons/hicolor/`
- `/usr/local/bin/` (wrapper executable)

Run:

```bash
sudo chmod +x tools/install_ubuntu_desktop_integration.sh
sudo tools/install_ubuntu_desktop_integration.sh --system
```

## Manual Installation (step-by-step)

### 1) Install `.desktop` file

User:
```bash
install -Dm644 packaging/gayzed-media.desktop ~/.local/share/applications/gayzed-media.desktop
```

System:
```bash
sudo install -Dm644 packaging/gayzed-media.desktop /usr/share/applications/gayzed-media.desktop
```

### 2) Install icon files

User:
```bash
mkdir -p ~/.local/share/icons/hicolor
cp -a assets/icons/hicolor/* ~/.local/share/icons/hicolor/
```

System:
```bash
sudo cp -a assets/icons/hicolor/scalable /usr/share/icons/hicolor/
sudo cp -a assets/icons/hicolor/16x16 /usr/share/icons/hicolor/
sudo cp -a assets/icons/hicolor/32x32 /usr/share/icons/hicolor/
sudo cp -a assets/icons/hicolor/48x48 /usr/share/icons/hicolor/
sudo cp -a assets/icons/hicolor/64x64 /usr/share/icons/hicolor/
sudo cp -a assets/icons/hicolor/128x128 /usr/share/icons/hicolor/
sudo cp -a assets/icons/hicolor/256x256 /usr/share/icons/hicolor/
sudo cp -a assets/icons/hicolor/512x512 /usr/share/icons/hicolor/
```

### 3) Refresh caches

User:
```bash
update-desktop-database ~/.local/share/applications || true
gtk-update-icon-cache -f -t ~/.local/share/icons/hicolor || true
```

System:
```bash
sudo update-desktop-database /usr/share/applications
sudo gtk-update-icon-cache -f -t /usr/share/icons/hicolor
```

## Verification Checklist

- Validate desktop file:
  - `desktop-file-validate ~/.local/share/applications/gayzed-media.desktop`
- Confirm the icon is resolvable:
  - `gtk-update-icon-cache -f -t ~/.local/share/icons/hicolor`
- Launch from GNOME Activities Overview:
  - Search for “Gayzed Media”
  - Verify the icon shows in:
    - Activities Overview search results
    - Dock
    - Window switcher
    - Nautilus icon previews (for `.desktop` and pinned launchers)
