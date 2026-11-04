#!/usr/bin/env bash
# Scan a Go repository for known vulnerabilities using govulncheck.
# Usage: scan-vulnerabilities.sh [repo-root]
# Prints human-readable results and exits 1 when vulnerabilities are found.
set -euo pipefail

repo_root="${1:-.}"
cd "$repo_root"

if ! command -v govulncheck >/dev/null 2>&1; then
  echo "Installing govulncheck..." >&2
  export PATH="${GOPATH:-$HOME/go}/bin:${PATH}"
  if command -v go >/dev/null 2>&1; then
    go install golang.org/x/vuln/cmd/govulncheck@latest
  else
    echo "govulncheck not found and go is not installed" >&2
    exit 2
  fi
fi

echo "=== govulncheck ./... ==="
set +e
govulncheck ./...
exit_code=$?
set -e

if [[ $exit_code -eq 0 ]]; then
  echo "No vulnerabilities reported."
else
  echo "Vulnerabilities reported (govulncheck exit $exit_code)."
fi

exit $exit_code
