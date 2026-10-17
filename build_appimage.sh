#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "$0")" && pwd)"
cd "$project_dir"

if [[ "$(uname -s)" != "Linux" || "$(uname -m)" != "x86_64" ]]; then
    echo "AppImage packaging currently targets Linux x86_64." >&2
    exit 1
fi

binary="dist/CSVCompare"
app_dir="build/CSVCompare.AppDir"
tool="build/tools/appimagetool-x86_64.AppImage"
output="dist/CSVCompare-Linux-x86_64.AppImage"
staged_output="build/CSVCompare-Linux-x86_64.AppImage"
icon="assets/csvviewer.svg"
tool_url="https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage"
tool_sha256="95cbe7cce9717fce90c484e34052ee7c7f1d7635b33c12525b4776826a7d29b6"

if [[ ! -f "$binary" ]]; then
    echo "Build the PyInstaller executable first (bash build_linux.sh)." >&2
    exit 1
fi
if [[ ! -f "$icon" ]]; then
    echo "Application icon is missing: $icon" >&2
    exit 1
fi

mkdir -p "$(dirname "$tool")" "$app_dir/usr/bin" \
    "$app_dir/usr/share/applications" \
    "$app_dir/usr/share/icons/hicolor/scalable/apps"

if [[ ! -f "$tool" ]] || ! echo "$tool_sha256  $tool" | sha256sum --check --status; then
    curl --fail --location --retry 3 "$tool_url" --output "$tool"
fi
echo "$tool_sha256  $tool" | sha256sum --check
chmod +x "$tool"

install -m 0755 "$binary" "$app_dir/usr/bin/CSVCompare"
cat > "$app_dir/AppRun" <<'APPRUN'
#!/bin/sh
HERE="$(dirname "$(readlink -f "$0")")"
exec "$HERE/usr/bin/CSVCompare" "$@"
APPRUN
chmod +x "$app_dir/AppRun"

cat > "$app_dir/csvviewer.desktop" <<'DESKTOP'
[Desktop Entry]
Name=CSV Compare
Comment=Compare CSV files side by side
Exec=CSVCompare
Icon=csvviewer
Type=Application
Categories=Utility;
Terminal=false
DESKTOP
cp "$app_dir/csvviewer.desktop" "$app_dir/usr/share/applications/csvviewer.desktop"
cp "$icon" "$app_dir/csvviewer.svg"
cp "$icon" dist/csvviewer.svg
cp "$icon" \
    "$app_dir/usr/share/icons/hicolor/scalable/apps/csvviewer.svg"

ARCH=x86_64 "$tool" --appimage-extract-and-run "$app_dir" "$staged_output"
chmod +x "$staged_output"
mv -f "$staged_output" "$output"
echo "Created $output"
