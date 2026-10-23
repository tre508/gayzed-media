#!/usr/bin/env bash
set -euo pipefail

mode="user"
destdir=""
run_mode="source"
binary_path=""
while [ $# -gt 0 ]; do
    case "$1" in
        --system) mode="system" ;;
        --user) mode="user" ;;
        --source) run_mode="source" ;;
        --packaged) run_mode="packaged" ;;
        --binary)
            shift
            binary_path="${1:-}"
            if [ -z "$binary_path" ]; then
                echo "Missing value for --binary" >&2
                exit 2
            fi
            ;;
        --destdir)
            shift
            destdir="${1:-}"
            if [ -z "$destdir" ]; then
                echo "Missing value for --destdir" >&2
                exit 2
            fi
            ;;
        *) echo "Unknown argument: $1" >&2; exit 2 ;;
    esac
    shift
done

root_dir="$(cd "$(dirname "$0")/.." && pwd)"
app_py="$root_dir/app.py"
desktop_src="$root_dir/packaging/gayzed-media.desktop"
icons_src="$root_dir/assets/icons/hicolor"
default_binary="$root_dir/dist/DesktopMediaGUI/DesktopMediaGUI"

# #region debug-point B:install-computed-paths
source "$root_dir/.dbg/menu-feature-launch.env" 2>/dev/null || true
if [ -n "${DEBUG_SERVER_URL:-}" ]; then
    _app_exists=0
    if [ -f "$app_py" ]; then _app_exists=1; fi
    curl -sX POST "$DEBUG_SERVER_URL" -H "Content-Type: application/json" -d "{\"sessionId\":\"${DEBUG_SESSION_ID:-menu-feature-launch}\",\"runId\":\"${TRAE_RUN_ID:-pre}\",\"hypothesisId\":\"B\",\"location\":\"install_ubuntu_desktop_integration.sh:35-44\",\"msg\":\"[DEBUG] Install computed paths\",\"data\":{\"root_dir\":\"$root_dir\",\"app_py\":\"$app_py\",\"app_py_exists\":$_app_exists,\"run_mode\":\"$run_mode\",\"mode\":\"$mode\",\"destdir\":\"$destdir\"}}" >/dev/null 2>&1 || true
fi
# #endregion

if [ ! -f "$app_py" ]; then
    echo "Missing app.py at: $app_py" >&2
    exit 1
fi
if [ ! -f "$desktop_src" ]; then
    echo "Missing desktop entry at: $desktop_src" >&2
    exit 1
fi
if [ ! -d "$icons_src" ]; then
    echo "Missing icons dir at: $icons_src" >&2
    exit 1
fi

if [ -n "$destdir" ]; then
    apps_dir="$destdir/applications"
    icon_root="$destdir/icons"
    bin_dir="$destdir/bin"
else
    if [ "$mode" = "system" ]; then
        apps_dir="/usr/share/applications"
        icon_root="/usr/share/icons"
        bin_dir="/usr/local/bin"
    else
        apps_dir="$HOME/.local/share/applications"
        icon_root="$HOME/.local/share/icons"
        bin_dir="$HOME/.local/bin"
    fi
fi

mkdir -p "$apps_dir" "$icon_root" "$bin_dir"

wrapper="$bin_dir/gayzed-media"
if [ "$run_mode" = "packaged" ]; then
    if [ -z "$binary_path" ]; then
        binary_path="$default_binary"
    fi
    if [ ! -f "$binary_path" ]; then
        echo "Missing packaged binary at: $binary_path" >&2
        exit 1
    fi
    cat > "$wrapper" <<EOF
#!/usr/bin/env bash
# #region debug-point A:wrapper-launch
wrapper_dir="\$(cd "\$(dirname "\$0")" && pwd)"
for _dbg in "\$wrapper_dir/../.dbg/menu-feature-launch.env" "\$wrapper_dir/../../.dbg/menu-feature-launch.env"; do
    if [ -f "\$_dbg" ]; then
        source "\$_dbg" 2>/dev/null || true
        break
    fi
done
if [ -n "\${DEBUG_SERVER_URL:-}" ]; then
    curl -sX POST "\$DEBUG_SERVER_URL" -H "Content-Type: application/json" -d "{\"sessionId\":\"\${DEBUG_SESSION_ID:-menu-feature-launch}\",\"runId\":\"\${TRAE_RUN_ID:-pre}\",\"hypothesisId\":\"A\",\"location\":\"install_ubuntu_desktop_integration.sh:packaged-wrapper\",\"msg\":\"[DEBUG] Wrapper invoked\",\"data\":{\"wrapper\":\"\$0\",\"binary_path\":\"$binary_path\"}}" >/dev/null 2>&1 || true
fi
# #endregion
cache_dir="\${XDG_CACHE_HOME:-\$HOME/.cache}/gayzed-media"
mkdir -p "\$cache_dir" >/dev/null 2>&1 || true
log_file="\$cache_dir/launcher.log"

if [ ! -f "$binary_path" ]; then
    {
        date
        echo "Launcher failed: packaged binary missing at: $binary_path"
    } >> "\$log_file"
    if command -v notify-send >/dev/null 2>&1; then
        notify-send "Gayzed Media failed to start" "Packaged binary missing. See \$log_file"
    fi
    exit 1
fi

exec "$binary_path" "\$@" >> "\$log_file" 2>&1
EOF
else
    cat > "$wrapper" <<EOF
#!/usr/bin/env bash
# #region debug-point A:wrapper-launch
wrapper_dir="\$(cd "\$(dirname "\$0")" && pwd)"
for _dbg in "\$wrapper_dir/../.dbg/menu-feature-launch.env" "\$wrapper_dir/../../.dbg/menu-feature-launch.env"; do
    if [ -f "\$_dbg" ]; then
        source "\$_dbg" 2>/dev/null || true
        break
    fi
done
if [ -n "\${DEBUG_SERVER_URL:-}" ]; then
    _exists=0
    if [ -f "$app_py" ]; then _exists=1; fi
    curl -sX POST "\$DEBUG_SERVER_URL" -H "Content-Type: application/json" -d "{\"sessionId\":\"\${DEBUG_SESSION_ID:-menu-feature-launch}\",\"runId\":\"\${TRAE_RUN_ID:-pre}\",\"hypothesisId\":\"A\",\"location\":\"install_ubuntu_desktop_integration.sh:source-wrapper\",\"msg\":\"[DEBUG] Wrapper invoked\",\"data\":{\"wrapper\":\"\$0\",\"app_py\":\"$app_py\",\"app_py_exists\":\$_exists}}" >/dev/null 2>&1 || true
fi
# #endregion
app_py="$app_py"
cache_dir="\${XDG_CACHE_HOME:-\$HOME/.cache}/gayzed-media"
mkdir -p "\$cache_dir" >/dev/null 2>&1 || true
log_file="\$cache_dir/launcher.log"

_py=""
for cand in "$root_dir/.venv/bin/python3" "$root_dir/.venv/bin/python" "$root_dir/.venv-py311/bin/python3" "$root_dir/.venv-py311/bin/python" "$root_dir/.venv311/bin/python3" "$root_dir/.venv311/bin/python" python3.12 python3.11 python3; do
    if [ -x "\$cand" ]; then
        if "\$cand" -c "import PySide6" >/dev/null 2>&1; then _py="\$cand"; break; fi
    elif command -v "\$cand" >/dev/null 2>&1; then
        if "\$cand" -c "import PySide6" >/dev/null 2>&1; then _py="\$cand"; break; fi
    fi
done

if [ -z "\$_py" ]; then
    {
        date
        echo "Launcher failed: no compatible Python interpreter found for: $app_py"
        echo "Tried: $root_dir/.venv/bin/python3, $root_dir/.venv/bin/python, $root_dir/.venv-py311/bin/python3, $root_dir/.venv-py311/bin/python, $root_dir/.venv311/bin/python3, $root_dir/.venv311/bin/python, python3.12, python3.11, python3"
        echo "Hint: create a venv (python3.11 -m venv .venv-py311) and install requirements, or use the packaged launcher."
    } >> "\$log_file"
    if command -v notify-send >/dev/null 2>&1; then
        notify-send "Gayzed Media failed to start" "No compatible Python/PySide6 found. See \$log_file"
    fi
    exit 1
fi

exec "\$_py" "$app_py" "\$@" >> "\$log_file" 2>&1
EOF
fi
chmod 755 "$wrapper"

desktop_out="$apps_dir/gayzed-media.desktop"
exec_value="$wrapper"
icon_value="gayzed-media"

{
    echo "[Desktop Entry]"
    echo "Type=Application"
    echo "Version=1.0"
    echo "Name=Gayzed Media"
    echo "GenericName=Media Downloader"
    echo "Comment=Desktop media downloader and queue manager (yt-dlp)"
    echo "Keywords=Gayzer;Gayzed;Media;Downloader;yt-dlp;Video;Queue;"
    echo "Exec=$exec_value"
    echo "Icon=$icon_value"
    echo "Terminal=false"
    echo "Categories=AudioVideo;"
    echo "StartupNotify=true"
    echo "StartupWMClass=gayzed-media"
} > "$desktop_out"
chmod 644 "$desktop_out"

theme_dir="$icon_root/hicolor"
mkdir -p "$theme_dir"

if [ "$mode" = "user" ] && [ ! -f "$theme_dir/index.theme" ] && [ -f "/usr/share/icons/hicolor/index.theme" ]; then
    install -Dm644 "/usr/share/icons/hicolor/index.theme" "$theme_dir/index.theme"
fi

install -Dm644 \
    "$icons_src/scalable/apps/gayzed-media.svg" \
    "$theme_dir/scalable/apps/gayzed-media.svg"

for sz in 16 32 48 64 128 256 512; do
    src_png="$icons_src/${sz}x${sz}/apps/gayzed-media.png"
    if [ -f "$src_png" ]; then
        install -Dm644 \
            "$src_png" \
            "$theme_dir/${sz}x${sz}/apps/gayzed-media.png"
    fi
done

desktop-file-validate "$desktop_out" >/dev/null

update-desktop-database "$apps_dir" >/dev/null 2>&1 || true
gtk-update-icon-cache -f -t "$theme_dir" >/dev/null 2>&1 || true

echo "Installed:"
echo "  $desktop_out"
echo "  $wrapper"
echo "  $theme_dir"
