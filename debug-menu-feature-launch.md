[OPEN]

# Debug Session: menu-feature-launch

## Symptom
- Target feature fails to launch when accessed from the application's main menu.

## Expected
- Clicking the menu item navigates to / initializes the target feature reliably.

## Actual
- Menu click occurs but the target feature does not appear / initialize (details TBD by runtime evidence).

## Scope
- Entry point: main menu item → routing / handler → feature initialization.

## Hypotheses (falsifiable)
1. The menu item click handler is not bound (or is bound to a stale reference), so the launch trigger never fires.
2. The handler fires, but the route/feature key is misconfigured (wrong route name/path), so navigation is a no-op or redirected.
3. The route loads, but feature bootstrap throws during initialization (uncaught exception), preventing render/mount.
4. Required resources/permissions (e.g., dynamic import chunk, file permission, API permission) fail at runtime, causing initialization to abort.
5. A guard (auth/feature-flag/platform check) blocks launch from the menu path only (e.g., desktop vs mobile / device type condition).

## Evidence Plan
- Instrument: menu click → router dispatch → route resolve → feature module load → feature init success/failure.
- Collect: console/runtime errors, network failures, permission errors, and navigation state transitions.

## Evidence (collected)
- Pre: installer computes `app_py=/home/treshen/Apps/gayzed-media/app.py` but file missing (`app_py_exists=0`), causing install failure and/or broken launcher wrappers.
  - Log: `.dbg/trae-debug-log-menu-feature-launch.ndjson` runId `pre`, hypothesisId `B`.
- Post: `app_py` exists and installer completes after skipping missing icon sizes.
  - Log: `.dbg/trae-debug-log-menu-feature-launch.ndjson` runId `post-fix`, hypothesisId `B`.
- Post: launching wrapper fails on this environment due to missing `PySide6` in all probed Python interpreters; failure is now captured in `~/.cache/gayzed-media/launcher.log` instead of being silent from GNOME.
- User environment: `~/.local/bin/gayzed-media` is a stale packaged wrapper still pointing to an old external-drive path (`/run/media/.../dist/DesktopMediaGUI/DesktopMediaGUI`), causing immediate failure ("No such file or directory").

## Confirmed Root Causes
1. Desktop integration script expected repo-root `app.py`, but actual entrypoint lived under `updated_desktop_media_gui_no_archive_no_thumbs/app.py`, making installs fail.
2. Desktop integration script hard-required icon sizes (256/512) that are not present in `assets/icons/hicolor`, making installs fail mid-way.
3. Source launcher relied on a Python runtime with `PySide6` available; when missing, GNOME launch silently fails (now logged).
4. System had a stale packaged wrapper pointing to a non-existent binary path, so the GNOME launch entrypoint was broken even before Python was considered.
