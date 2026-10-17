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
tool_url="https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage"
tool_sha256="95cbe7cce9717fce90c484e34052ee7c7f1d7635b33c12525b4776826a7d29b6"

if [[ ! -f "$binary" ]]; then
    echo "Build the PyInstaller executable first (bash build_linux.sh)." >&2
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

cat > "$app_dir/csvviewer.svg" <<'SVG'
<svg xmlns="http://www.w3.org/2000/svg" width="128" height="128" viewBox="0 0 128 128">
  <rect x="12" y="12" width="104" height="104" rx="16" fill="#f4f6f8"/>
  <path d="M30 34h68v60H30z" fill="#fff" stroke="#536273" stroke-width="5"/>
  <path d="M30 53h68M30 73h68M53 34v60M76 34v60" fill="none" stroke="#9aa7b4" stroke-width="4"/>
  <path d="m37 63 5 5 10-11" fill="none" stroke="#218838" stroke-linecap="round" stroke-linejoin="round" stroke-width="5"/>
  <path d="m83 84 10-10m0 10L83 74" fill="none" stroke="#c73535" stroke-linecap="round" stroke-width="5"/>
</svg>
SVG
cp "$app_dir/csvviewer.svg" \
    "$app_dir/usr/share/icons/hicolor/scalable/apps/csvviewer.svg"

ARCH=x86_64 "$tool" --appimage-extract-and-run "$app_dir" "$output"
chmod +x "$output"
echo "Created $output"
