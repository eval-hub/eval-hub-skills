---
name: golang-toolchain-update
description: >-
  Scans a Go repository for CVEs with govulncheck and updates the Go toolchain
  only when the required version exists on a Red Hat go-toolset image
  (ubi9/ubi10/go-toolset). Supports minimal CVE remediation and latest-available
  upgrade modes. Use when checking Go CVEs, remediating stdlib or module
  vulnerabilities, bumping go.mod, Containerfile, or CI Go versions, or
  validating Red Hat go-toolset image availability.
user-invocable: true
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Glob
  - Grep
---

# Go Toolchain Update

Audit a Go repository, choose the right Go version, and change the version pins
**only if** the target repository's Red Hat go-toolset image publishes a matching
tag.

## Hard rule

**Do not change the Go version unless the resolved go-toolset image has a tag for
the exact target version.**

Resolve the image before doing anything else. Precedence:

1. `--image ubiX/go-toolset` passed to the scripts
2. `GO_TOOLSET_IMAGE` environment variable
3. the first `registry.access.redhat.com/ubiX/go-toolset` reference in
   `Containerfile`, `Dockerfile`, or their `Containerfile.*` / `Dockerfile.*`
   variants
4. fallback: `ubi10/go-toolset`

The scripts print the resolved image and its source on stderr. Pass the same
image to every script and report it, so a mismatch between the repository's image
and the one queried is visible.

## Modes

| Mode | Pick it when | Version policy |
| --- | --- | --- |
| `cve` (default) | `govulncheck` reports findings, or the user mentions CVEs, vulnerabilities, or security fixes | **minimum** version that fixes every stdlib and toolchain finding |
| `latest` | the user asks to bump Go, check for Go updates, or refresh the toolchain | **newest** patch of the current major.minor, or the newest major.minor when requested |

If the request is ambiguous, scan first: no findings means `latest`, findings mean
`cve`.

## Workflow

Copy and track progress:

```md
Task Progress:
- [ ] Step 1: Detect the image and the current pins
- [ ] Step 2: Check for an existing open PR
- [ ] Step 3: Scan for CVEs
- [ ] Step 4: Choose the target Go version
- [ ] Step 5: Verify the toolset tag (mandatory gate)
- [ ] Step 6: Update every pin consistently
- [ ] Step 7: Handle dependencies
- [ ] Step 8: Validate
- [ ] Step 9: Report
```

### Step 1: Detect the image and the current pins

Record the go-toolset image (see the precedence above) and every place the Go
version is pinned. See [reference.md](reference.md) for the full pattern list:

- `go.mod` — the `go` directive and any `toolchain` line, noting whether it is
  **active** or **commented out** (e.g. `// toolchain go1.26.3`)
- `Containerfile`, `Dockerfile`, and variants that reference
  `registry.access.redhat.com/ubiX/go-toolset`
- CI workflows, `.go-version`, `.tool-versions`, `Makefile`, `Jenkinsfile`,
  `.tekton/*`

### Step 2: Check for an existing open PR

```bash
gh pr list --state open --search "go update OR golang OR go-toolset OR go.mod" --limit 20
```

If an open PR already bumps Go or fixes the same CVE, report its number and
**stop**. Do not open a competing PR.

### Step 3: Scan for CVEs

From the target repository root (prefix the absolute path to this skill when
working outside `dev-skills`):

```bash
scripts/scan-vulnerabilities.sh
```

`govulncheck` analyses source with the Go toolchain on `PATH`, which may not be
the builder image's Go — a newer host toolchain can miss stdlib findings that
affect the shipped image. For gate-accurate results, run the scan inside the
resolved toolset image (using `$IMAGE` from Step 1, for example
`ubi10/go-toolset`, and its major.minor tag):

```bash
podman run --rm -v "$PWD:/src:Z" -w /src \
  "registry.access.redhat.com/$IMAGE:$MAJOR_MINOR" \
  go run golang.org/x/vuln/cmd/govulncheck@latest ./...
```

Scanning a binary built in that image with `-mode=binary` is an equivalent
alternative.

Skip this step in `latest` mode unless the user asked for a security check. From
the output, capture:

- vulnerability IDs (for example `GO-2025-XXXX`) and affected packages
- the **fixed in** version for each finding
- whether the fix is in `stdlib`/`toolchain` (justifies a Go bump) or in a module
  (dependency bump only)

### Step 4: Choose the target Go version

- `cve` — take the highest `Fixed in: stdlib@goX.Y.Z` (or `toolchain@goX.Y.Z`)
  across findings and choose the **minimum** Go version that satisfies all of
  them. Module-only findings do **not** justify a Go bump.
- `latest` — take the newest patch of the current major.minor. Move to a newer
  major.minor only when the user asked for it; if they name a version that the
  image does not publish, report the gap and stop.
- If the current pin already satisfies the target and there are no module
  findings, report that no change is needed and **stop**.
- If the current pin already satisfies the target but module findings remain,
  skip Steps 5-6 (no Go pin changes) and continue at Step 7 to remediate them.

Call the chosen version `TARGET_VERSION` and use it in the remaining steps.

### Step 5: Verify the toolset tag (mandatory gate)

```bash
TAG=$(scripts/check-toolset-version.sh "$TARGET_VERSION")
STATUS=$?
if [ "$STATUS" -ne 0 ]; then
  echo "toolset gate failed for $TARGET_VERSION (exit $STATUS)" >&2
  scripts/list-toolset-tags.sh "$(echo "$TARGET_VERSION" | cut -d. -f1-2)" || true
  exit "$STATUS"
fi
echo "Matched tag: $TAG"
```

- exit `0` → tag exists (printed on stdout); keep `$TAG` for Step 6
- exit `1` → the image does not publish that version; **stop without editing**
- exit `2` → invalid input or registry error; fix and retry

Capture the status immediately after the check: printing the tag first, or piping
the check into another command, masks a non-zero exit and lets the gate be
skipped.

On exit `1`, show the nearest available tags and stop:

```bash
scripts/list-toolset-tags.sh "$(echo "$TARGET_VERSION" | cut -d. -f1-2)"
```

Never substitute a different patch version, a major.minor alias for a required
patch, or a different image family. Report the gap and let a human decide.

### Step 6: Update every pin consistently

Only after Step 5 passes.

| File kind | Action |
| --- | --- |
| `go.mod` `go` directive | set to `TARGET_VERSION` |
| `go.mod` `toolchain` | **active** line → update it; **commented** line → update the version but keep it commented; **absent** → do not add one |
| `Containerfile` / `Dockerfile` | set the image tag to the exact `TAG` returned by Step 5 when the repo pins build-ID tags; otherwise use the full `1.X.Y` when it pins patch tags, or the major.minor alias when it pins `1.X` |
| CI workflows, `.go-version`, `.tool-versions`, `Makefile` | match `TARGET_VERSION`; leave `go-version-file: "go.mod"` lines alone — they follow `go.mod` automatically |
| `golangci-lint` pin — `GOLANGCI_LINT_VERSION` in the `Makefile`, `version` in `.github/workflows/golangci-lint.yml` | bump both in the same PR to a release that can type-check `TARGET_VERSION` (see the export-data note below) |
| any other pin found in Step 1 | update it, or explain why it is intentionally unchanged |

Sweep for stragglers before reporting:

```bash
grep -rn "go-toolset:\|GOTOOLCHAIN\|GOSECGOVERSION\|GOLANGCI_LINT_VERSION\|golangci-lint\|go-version" . \
  --include='*.yml' --include='*.yaml' --include='*.json' --include='*.md' \
  --include='*.sh' --include='Makefile' --include='Containerfile' --include='Dockerfile'
```

The linter pin is the straggler this sweep finds most often. `golangci-lint`
bundles its own export-data importer, which only decodes standard-library data up
to the Go release it shipped with. A pin that lags `TARGET_VERSION` does not fail
at install time; it fails `make lint` with `cannot decode "internal/goarch",
export data version N is greater than maximum supported version M`, which reads
like a pre-existing failure rather than a missing bump. Compare the release's
bundled `golang.org/x/tools` version (or the `go` directive in its `go.mod`)
against the target, and state the chosen pin plus the oldest release that works in
the PR, so the next bump knows the floor. For reference, Go 1.27 needs `v2.14.0`
or newer.

### Step 7: Handle dependencies

- `cve` mode — bump **only** the modules that have findings
  (`go get <module>@<fixed-version>`), then `go mod tidy`. Do not refresh
  unrelated dependencies: it widens the diff and obscures the security fix.
- `latest` mode — `go mod tidy`. Run `go get -t -u ./...` only when the user
  explicitly asks for a dependency refresh.

Then confirm the dependency change did not move the Go toolchain past the gate.
`go get` raises the `go` and `toolchain` directives when a module requires a newer
Go:

```bash
git diff -- go.mod | grep -E '^[+-](go|toolchain) ' || true
```

If either directive changed, the dependency update introduced a Go version that
has not passed Step 5. Either re-run Step 5 for the new `go` version (and Step 6 if
it passes), or pin the module to a version compatible with the current Go.

### Step 8: Validate

```bash
go mod tidy
go test ./...
```

If the repository provides Make targets for linting and tests (the eval-hub
profile), use them as well:

```bash
make fmt lint
make test
```

In `cve` mode, re-run `scripts/scan-vulnerabilities.sh` and confirm it exits `0`;
if findings remain because no fixed module version exists, list them as remaining
risk instead of claiming the CVE is fixed.

### Step 9: Report

```markdown
## Go toolchain update summary

**Repository:** [path]
**Mode:** cve | latest
**go-toolset image:** [ubiX/go-toolset, with where it came from]
**Previous Go version:** [version]
**Target Go version:** [version or "none"]
**Matched toolset tag:** [tag or "not available"]

### Findings
- [GO-XXXX] [package] — fixed in [version]

### Changes
- [files updated, or "no files changed — <reason>"]

### Validation
- [go test ./... / make fmt lint / make test results]
- [govulncheck result after the change]

### Remaining issues
- [module CVEs without a fixed version, or none]
```

If the user wants a PR, use a Conventional Commit, for example:

```text
build(go): bump Go toolchain to 1.XX.Y
```

and list the updated files in the body, including the toolset tag that gated the
change.

## Scripts

| Script | Purpose |
| --- | --- |
| [scripts/scan-vulnerabilities.sh](scripts/scan-vulnerabilities.sh) | Run `govulncheck ./...`, installing govulncheck if needed. Exits `1` when findings are reported. |
| [scripts/check-toolset-version.sh](scripts/check-toolset-version.sh) | Verify the image publishes a tag for the given Go version. Exit `0` (prints the tag), `1` (missing), `2` (bad input or registry error). |
| [scripts/list-toolset-tags.sh](scripts/list-toolset-tags.sh) | List matching registry tags, newest first. Use it to show nearby versions when a tag is missing. |

Common options:

- `--image ubiX/go-toolset` — override the resolved image
- `--root DIR` — repository root used to detect the image (default `.`)

Environment:

- `GO_TOOLSET_IMAGE` — default image when no `--image` is passed
- `GOLANG_TOOLCHAIN_UPDATE_NO_CACHE=1` — bypass the 5-minute tag cache
  (`GOLANG_CVE_UPDATE_NO_CACHE=1` is still honoured)

When the target repository is not this one, invoke the scripts through the
absolute path to this skill directory, e.g.
`/path/to/eval-hub-skills/dev-skills/golang-toolchain-update/scripts/check-toolset-version.sh`.

## Additional resources

- Version pin patterns, image tag formats, govulncheck output cues, and the
  eval-hub profile: [reference.md](reference.md)


