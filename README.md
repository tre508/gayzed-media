# Gayzed Media

**A desktop media downloader and queue manager — built with [PySide6](https://doc.qt.io/qtforpython/) and powered by [yt-dlp](https://github.com/yt-dlp/yt-dlp).**

Paste links, queue them up, and watch them download in parallel with live progress, speed, ETA and preview thumbnails. Everything you fetch is logged to a local SQLite history that never leaves your machine.

![Gayzed Media queue view — progress, speed, ETA, previews and file paths](Screenshot%20From%202026-09-16%2011-37-13%20%28Edit%29.png)

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Qt](https://img.shields.io/badge/UI-PySide6%20%2F%20Qt%206-41cd52)
![Engine](https://img.shields.io/badge/engine-yt--dlp-red)
![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20Windows%20%7C%20macOS-lightgrey)

---

## Highlights

- **Bulk queueing** — paste one URL per line, or paste a wall of mixed text and let the URL extractor find the links.
- **Parallel downloads** — tunable concurrency (1–16 workers, default 3) running on a `QThreadPool`, so the UI never freezes.
- **Live telemetry per item** — status, progress bar, retry count, resolved title, speed, ETA, final file path and error.
- **Preview thumbnails** — pulled from the freedesktop thumbnail cache (with `Thumb::URI` / `Thumb::MTime` validation so stale images are rejected) and falling back to a native GNOME thumbnailer. Click any preview to open it large.
- **Local history** — every finished, failed or cancelled job is written to SQLite and shown in a browsable **History** tab with previews.
- **Cookies & headers** — import cookies straight from Firefox, Chrome or Chromium and add custom HTTP headers for sites that need them.
- **Resilient by default** — configurable retries with linear backoff, resumable partial downloads, and short `<video-id>.<ext>` filenames so long titles can never hit a "file name too long" error.
- **Neon dark theme** — a custom Qt stylesheet with gradient accents, designed for long sessions.
- **Native Linux integration** — freedesktop icon set, `.desktop` entry, and an installer script for user- or system-wide launcher installation.

## Features in detail

### Queue tab

| Control | What it does |
| --- | --- |
| **Add to queue** | Extracts every unique `http(s)` URL from the input box, de-duplicates against the current queue, and adds the rest. |
| **Import file** | Loads URLs out of a text, CSV or Markdown file (anything containing links). |
| **Save queue URLs** | Exports the URLs currently in the queue to a plain-text file. |
| **Clear input** | Empties the paste box. |
| **Start queue** | Spawns one `DownloadWorker` per queued item, up to the parallel limit. |
| **Rename selected** | Renames a completed file on disk (filename sanitised for the OS). |
| **Cancel selected** | Flags running items; the download hook raises `DownloadCancelled` at the next progress tick. |
| **Remove selected** | Drops rows from the queue table and the in-memory item map. |
| **Clear completed/failed** | Tidies the queue while keeping history intact. |

### Download settings

- **Output folder** — any directory you can write to; the picker opens at `/` so mounted external drives (`/media`, `/mnt`, `/run/media`) are immediately visible. If the saved folder is missing (drive unmounted), the app warns you instead of silently failing.
- **Format selector** — `bv*+ba/b` (default, best video + best audio with fallback), `bestvideo+bestaudio/best`, `best`, `ba/bestaudio`.
- **Rate limit** — human-friendly strings such as `5M` or `750K`, parsed to bytes/second.
- **Retries / backoff** — number of extra attempts and the linear wait between them (`backoff × attempt`).
- **Extras** — write subtitles; prompt for a rename (with live preview) as soon as a download completes.

### Cookies and headers

- **Cookies from browser:** `none` (default), `firefox`, `chrome`, `chromium`.
- **Custom headers:** one `Key: Value` pair per line — handy for `Referer` or a specific `User-Agent`.

### History tab

Completed, failed and cancelled jobs are persisted with timestamp, status, title, URL, output path and error. Previews are loaded asynchronously for rows whose file still exists, so the tab stays responsive with long histories (the last 200 records are listed).

---

## Requirements

- **Python 3.10+** (3.11/3.12 recommended)
- **ffmpeg** on `PATH` — required by yt-dlp to merge separate video and audio streams
- A desktop session (X11 or Wayland) capable of running Qt 6

Python packages (see [`requirements.txt`](requirements.txt)):

| Package | Purpose |
| --- | --- |
| `PySide6` | Qt 6 GUI toolkit |
| `yt-dlp[default,curl-cffi]` | Download engine, with curl-cffi for stubborn hosts |
| `pyinstaller` | Standalone binary builds |

## Installation

### 1. System packages

**Debian / Ubuntu / Zorin OS**

```bash
sudo apt update
sudo apt install -y ffmpeg python3-pip python3-venv
# optional, for Start-menu integration:
sudo apt install -y desktop-file-utils libgtk-3-bin
```

**Fedora**

```bash
sudo dnf install ffmpeg python3-pip
```

**Windows** — install [ffmpeg](https://ffmpeg.org/download.html) and make sure `ffmpeg.exe` is on `PATH`, then use the Python commands below.

### 2. Clone and create a virtual environment

```bash
git clone https://github.com/tre508/gayzed-media.git
cd gayzed-media

python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Run it

```bash
python3 app.py
```

`app.py` is a thin launcher that loads the real application module from
`updated_desktop_media_gui_no_archive_no_thumbs/app.py`. You can also run that module directly:

```bash
python3 updated_desktop_media_gui_no_archive_no_thumbs/app.py
```

> If PySide6 cannot be imported, the launcher exits with a message telling you to activate your venv and install `requirements.txt` — this is intentional, so a wrong interpreter fails loudly.

A step-by-step "fresh machine" walkthrough (including config bootstrap) lives in [`SETUP_GUIDE.md`](SETUP_GUIDE.md).

## Configuration

Settings are read once at startup and written back when the window closes.

| File | Location |
| --- | --- |
| Settings | `~/.config/desktop-media-gui/settings.json` (honours `XDG_CONFIG_HOME`) |
| Download history | `~/.config/desktop-media-gui/history.sqlite3` |
| Launcher log (desktop entry) | `~/.cache/gayzed-media/launcher.log` |

`settings.example.json` is a starting template. Copy it into place before first launch if you prefer to pre-seed values:

```bash
mkdir -p ~/.config/desktop-media-gui
cp settings.example.json ~/.config/desktop-media-gui/settings.json
```

### Settings keys

| Key | Default | Description |
| --- | --- | --- |
| `output_dir` | `~/Videos/latest` | Destination folder for downloads |
| `parallel` | `3` | Maximum concurrent download workers (1–16) |
| `format` | `bv*+ba/b` | yt-dlp format selector |
| `rate_limit` | `""` | Bandwidth cap, e.g. `5M`; empty means unlimited |
| `write_subtitles` | `false` | Save subtitles when the source provides them |
| `prompt_rename_after_download` | `false` | Ask for a friendly filename on completion |
| `retry_count` | `2` | Extra attempts per item |
| `retry_backoff` | `3` | Seconds multiplied by attempt number between retries |
| `cookie_browser` | `"none"` | `none`, `firefox`, `chrome` or `chromium` |
| `headers` | `""` | Raw header block (`Key: Value` per line) |

Every setting is also editable in the UI, so hand-editing the JSON is optional. The file is rewritten on exit; unknown keys (such as the legacy `write_thumbnail`) are ignored.

---

## Building a standalone binary

[`build.sh`](build.sh) wraps PyInstaller and bundles the icon set:

```bash
chmod +x build.sh
./build.sh
```

The result is a windowed (no console) build at:

```
dist/DesktopMediaGUI/DesktopMediaGUI
```

It activates `.venv` automatically when present, and warns if it cannot find one. `DesktopMediaGUI.spec` is a minimal spec you can extend for your own pipeline (e.g. `--onefile`, code signing).

## Ubuntu / GNOME desktop integration

The repo ships a freedesktop-compliant icon set (SVG plus 16–128 px PNGs) and a `.desktop` entry, so the app resolves correctly in the Activities overview, dock and window switcher.

```bash
chmod +x tools/install_ubuntu_desktop_integration.sh

# Source checkout, installed for the current user (recommended for development)
tools/install_ubuntu_desktop_integration.sh --user

# Launcher for the PyInstaller build in dist/
tools/install_ubuntu_desktop_integration.sh --user --packaged

# System-wide (shared machines)
sudo tools/install_ubuntu_desktop_integration.sh --system
```

Other flags: `--source` / `--packaged` to force the launcher target, `--binary /path/to/executable` to point at a custom build, and `--destdir DIR` for staged installs (packaging/CI).

The user install places a wrapper in `~/.local/bin`; make sure that directory is on your `PATH`:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

If the wrapper cannot find a Python interpreter that imports `PySide6`, it logs the reason to `~/.cache/gayzed-media/launcher.log`. Full manual steps, cache refreshes and a verification checklist are in [`UBUNTU_DESKTOP_ICON_SETUP.md`](UBUNTU_DESKTOP_ICON_SETUP.md).

## Project structure

```
gayzed-media/
├── app.py                                   # Thin launcher → the real application module
├── updated_desktop_media_gui_no_archive_no_thumbs/
│   ├── app.py                               # MainWindow: queue, history, previews (entrypoint)
│   ├── downloader.py                        # DownloadWorker: yt-dlp + Qt signals
│   ├── models.py                            # QueueItem / DownloadResult dataclasses
│   ├── storage.py                           # Config paths + SQLite HistoryStore
│   ├── utils.py                             # URL extraction, byte/speed/ETA formatting, JSON I/O
│   ├── theme.py                             # Neon gradient Qt stylesheet
│   ├── ubuntu_native_thumbnail_helper.py    # GNOME DesktopThumbnailFactory bridge
│   ├── desktop_media_gui.py                 # Original single-file starter (reference)
│   └── requirements.txt
├── assets/
│   ├── gayzedicon.ico                       # Windows icon
│   └── icons/hicolor/                       # 16, 32, 48, 64, 128, 256, 512 px + scalable SVG
├── packaging/gayzed-media.desktop           # Desktop entry template
├── tools/
│   ├── install_ubuntu_desktop_integration.sh
│   └── generate_icon_set.py                 # Regenerates the hicolor icon set
├── test_clear_input_on_add_static.py        # AST-based regression test
├── build.sh · DesktopMediaGUI.spec          # PyInstaller build paths
├── requirements.txt · settings.example.json
├── SETUP_GUIDE.md · UBUNTU_DESKTOP_ICON_SETUP.md
└── debug-*.md                               # Notes from past debugging sessions
```

> The root-level `downloader.py`, `models.py`, `storage.py`, `utils.py` and `theme.py` are earlier copies of the modules now living in the package folder. The launcher puts the package folder on `sys.path`, so the versions used at runtime are the ones under `updated_desktop_media_gui_no_archive_no_thumbs/`.


## How it works

1. **UI thread** — `MainWindow` owns the queue table, the settings form and the history table.
2. **Dispatch** — `start_queue()` validates the output folder, then creates one `DownloadWorker` (`QRunnable`) per queued item, wires its signals and hands it to a global `QThreadPool` whose thread count follows the "Parallel downloads" spinner.
3. **Worker** — `DownloadWorker.run()` calls `yt_dlp.YoutubeDL.extract_info()`. A progress hook emits structured updates, checks for cancellation and raises `yt_dlp.utils.DownloadCancelled` when the user cancels. Failures are retried with linear backoff before emitting `failed`.
4. **Signals** — `status`, `meta`, `progress`, `finished`, `failed` and `log` are Qt signals, so widgets are only ever touched from the UI thread.
5. **Persistence** — completions, failures and cancellations are appended to SQLite through `HistoryStore`, then the History tab is refreshed.
6. **Thumbnails** — `ThumbnailTask` runs on a separate 2-thread pool. It first looks in the freedesktop thumbnail cache (`~/.cache/thumbnails/{normal,large,x-large}`), validating `Thumb::URI` and `Thumb::MTime` against the real file, then falls back to the bundled GNOME helper. Misses are retried up to 12 times, 1.5 s apart, so previews appear as soon as the OS finishes generating them.

## Testing

A dependency-free regression test checks — via AST inspection — that `add_urls_from_input()` clears the paste box only *after* the URLs have been queued:

```bash
python3 -m unittest test_clear_input_on_add_static -v
```

Known state: the test for the active module passes, but `test_app_py` and `test_desktop_media_gui_py` are stale — they still expect GUI code in the root `app.py` (now a launcher) and in a root-level `desktop_media_gui.py` (never committed). Those two cases fail until the test is pointed at `updated_desktop_media_gui_no_archive_no_thumbs/` only.

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| `PySide6 is not installed in the current environment` | Activate the venv and run `pip install -r requirements.txt`. |
| Downloads finish as separate video/audio files, or merging fails | Install `ffmpeg` and confirm `ffmpeg -version` works in the same shell. |
| "Output folder unavailable" on start | The target drive is not mounted. Reconnect it or pick another folder — the app refuses to start rather than writing nowhere. |
| Preview thumbnails stay blank | The OS thumbnailer cannot decode that file. Install the desktop thumbnailer libraries (PyGObject + GNOME Desktop) and make sure codecs for the format are present; previews also appear after the file manager generates them once. |
| App missing from GNOME Activities | Run the integration script, then `update-desktop-database ~/.local/share/applications`, and check `~/.local/bin` is on `PATH`. |
| A site fails with a login wall or bot check | Try cookies from a browser (`firefox`/`chrome`/`chromium`) and/or custom `Referer` / `User-Agent` headers. |
| Downloaded files have cryptic names | By design: files are saved as `<video-id>.<ext>` to avoid filesystem name-length limits. Use **Rename selected** or enable **Prompt rename after download**. |
| Extraction errors after a site redesign | Update the engine: `pip install -U "yt-dlp[default,curl-cffi]"`. |

## Limitations

- **No DRM circumvention, anti-bot solving or page instrumentation.** The app is a friendly front end for URLs yt-dlp already supports; protected content fails with the engine's own error.
- Site support tracks yt-dlp releases, so keeping the dependency current matters more than app updates.
- Everything is local and single-user: settings and history live in your `XDG_CONFIG_HOME`, with no telemetry, accounts or cloud sync.
- Automatic subtitles are disabled (`writeautomaticsub = False`); only subtitles supplied by the source are written when "Write subtitles" is enabled.

## Documentation

- [`SETUP_GUIDE.md`](SETUP_GUIDE.md) — setting the project up on a fresh machine.
- [`UBUNTU_DESKTOP_ICON_SETUP.md`](UBUNTU_DESKTOP_ICON_SETUP.md) — launcher, icons, manual installation and verification.
- [`debug-menu-feature-launch.md`](debug-menu-feature-launch.md) and [`debug-thumbnail-preview-bug.md`](debug-thumbnail-preview-bug.md) — write-ups of past debugging sessions.

## Credits

Built on [yt-dlp](https://github.com/yt-dlp/yt-dlp) and [Qt for Python (PySide6)](https://doc.qt.io/qtforpython/). Icons are generated with `tools/generate_icon_set.py`.

## License

No license file is included in this repository yet, so all rights are reserved by the author. If you would like to reuse the code, please open an issue to discuss licensing.
