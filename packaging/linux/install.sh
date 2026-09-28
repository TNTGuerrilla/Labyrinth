#!/bin/sh
# Installs Labyrinth for the current user: the program in ~/.local/bin, plus an app-menu
# entry and icon. Run from the unpacked release folder: ./install.sh (or ./install.sh --uninstall).
set -eu

APP_ID=com.bydesigninteractive.labyrinth
here=$(cd "$(dirname "$0")" && pwd)
data=${XDG_DATA_HOME:-$HOME/.local/share}
bin_dir=$HOME/.local/bin
bin=$bin_dir/labyrinth
icon=$data/icons/hicolor/256x256/apps/$APP_ID.png
desktop=$data/applications/$APP_ID.desktop

refresh() {
    command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database -q "$data/applications" || true
    command -v gtk-update-icon-cache >/dev/null 2>&1 && gtk-update-icon-cache -q -t "$data/icons/hicolor" || true
}

if [ "${1:-}" = "--uninstall" ]; then
    rm -f "$bin" "$icon" "$desktop"
    refresh
    echo "Removed Labyrinth. Settings remain in ${XDG_CONFIG_HOME:-$HOME/.config}/Labyrinth."
    exit 0
fi

mkdir -p "$bin_dir" "$(dirname "$icon")" "$(dirname "$desktop")"
install -m 755 "$here/Labyrinth" "$bin"
install -m 644 "$here/$APP_ID.png" "$icon"
# The menu entry runs the program by its full path, so ~/.local/bin need not be on PATH.
sed "s|^Exec=.*|Exec=$bin|" "$here/$APP_ID.desktop" > "$desktop"
chmod 644 "$desktop"
refresh
echo "Installed Labyrinth. Find it in your app menu, or run $bin"
