#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "$0")" && pwd)"
cd "$project_dir"

if [[ "$(uname -s)" != "Linux" || "$(uname -m)" != "x86_64" ]]; then
    echo "This build script currently targets Linux x86_64." >&2
    exit 1
fi

python3 build_binary.py

python3 package_binary.py
