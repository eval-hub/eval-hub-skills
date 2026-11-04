#!/usr/bin/env bash
# Verify a Go version exists as a tag on a Red Hat go-toolset image.
# Usage: check-toolset-version.sh <version> [--image ubiX/go-toolset] [--root DIR]
# Exit 0 when a matching tag exists (prints one matching tag), 1 when it does
# not, 2 on invalid input or registry error.
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$script_dir/check-toolset-version.py" "$@"
