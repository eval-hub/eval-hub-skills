#!/usr/bin/env bash
# List available go-toolset tags for a Go major.minor or full version.
# Usage: list-toolset-tags.sh [version-prefix] [--image ubiX/go-toolset] [--root DIR]
# Prints matching tags newest first on stdout; reports the resolved image on stderr.
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$script_dir/list-toolset-tags.py" "$@"
