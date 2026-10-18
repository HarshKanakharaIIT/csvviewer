#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "$0")" && pwd)"
cd "$project_dir"

if [[ "$(uname -s)" != "Linux" || "$(uname -m)" != "x86_64" ]]; then
    echo "Debian packaging currently targets Linux x86_64." >&2
    exit 1
fi

if [[ ! -f "dist/CSVCompare" ]]; then
    echo "Build the standalone executable first (bash build_linux.sh)." >&2
    exit 1
fi
if [[ ! -f "assets/csvviewer.svg" ]]; then
    echo "Application icon is missing: assets/csvviewer.svg" >&2
    exit 1
fi

architecture="$(dpkg --print-architecture)"
version="$(python3 -c 'import tomllib; print(tomllib.load(open("pyproject.toml", "rb"))["project"]["version"])')"
staging_root="$(mktemp -d build/csvviewer-deb.XXXXXX)"
package_root="$staging_root/package"
trap 'rm -rf "$staging_root"' EXIT

install -d \
    "$package_root/DEBIAN" \
    "$package_root/opt/csvviewer" \
    "$package_root/usr/bin" \
    "$package_root/usr/share/applications" \
    "$package_root/usr/share/doc/csvviewer" \
    "$package_root/usr/share/icons/hicolor/scalable/apps"

install -m 0755 dist/CSVCompare "$package_root/opt/csvviewer/CSVCompare"
install -m 0644 assets/csvviewer.svg \
    "$package_root/usr/share/icons/hicolor/scalable/apps/csvviewer.svg"
install -m 0644 README.md "$package_root/usr/share/doc/csvviewer/README.md"

cat > "$package_root/usr/bin/csvviewer" <<'LAUNCHER'
#!/bin/sh
exec /opt/csvviewer/CSVCompare "$@"
LAUNCHER
chmod 0755 "$package_root/usr/bin/csvviewer"

cat > "$package_root/usr/share/applications/csvviewer.desktop" <<'DESKTOP'
[Desktop Entry]
Name=CSV Compare
Comment=Compare CSV files side by side
Exec=csvviewer
Icon=csvviewer
Type=Application
Categories=Utility;
Terminal=false
DESKTOP
chmod 0644 "$package_root/usr/share/applications/csvviewer.desktop"

cat > "$package_root/DEBIAN/control" <<CONTROL
Package: csvviewer
Version: ${version}
Section: utils
Priority: optional
Architecture: ${architecture}
Maintainer: CSV Compare maintainers
Depends: libc6 (>= 2.35), libstdc++6, libegl1, libgl1, libxcb-cursor0
Description: Desktop application for comparing CSV files
 Compare CSV data side by side, highlight differences, and save comparison
 results and history.
CONTROL
chmod 0644 "$package_root/DEBIAN/control"

mkdir -p dist
dpkg-deb --root-owner-group --build "$package_root" "dist/CSVCompare-Linux-${architecture}.deb"
echo "Created dist/CSVCompare-Linux-${architecture}.deb"
