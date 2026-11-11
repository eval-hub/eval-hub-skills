# Go toolchain reference

Patterns for finding and updating Go version pins, plus cues for reading
govulncheck output.

## go-toolset images

The skill works with any Red Hat `go-toolset` image family:

| Image | Used by |
| --- | --- |
| `registry.access.redhat.com/ubi10/go-toolset` | current eval-hub (after the UBI10 migration) |
| `registry.access.redhat.com/ubi9/go-toolset` | older eval-hub branches and many other Go repositories |
| `registry.access.redhat.com/ubi8/go-toolset` | legacy repositories (rare) |

Resolution order used by the scripts:

1. `--image ubiX/go-toolset`
2. `GO_TOOLSET_IMAGE`
3. the first `registry.access.redhat.com/ubiX/go-toolset` reference in
   `Containerfile`, `Dockerfile`, `Containerfile.*`, or `Dockerfile.*`
4. `ubi10/go-toolset`

Tag formats:

| Tag example | Meaning |
| --- | --- |
| `1.26.4` | Go 1.26.4, floats across image rebuilds |
| `1.26.4-1782717933` | Go 1.26.4 with a specific image build ID |
| `1.26` | major.minor alias |

Only update when a tag for the exact target version exists. If the repository
pins build IDs, keep using a build-ID tag; if it pins the major.minor alias,
keep that form.

## go.mod

Active toolchain (update both when bumping Go):

```go
go 1.22.5

toolchain go1.22.5
```

Commented toolchain (intentionally disabled — **do not uncomment**):

```go
go 1.26.3

// toolchain go1.26.3
```

Rules:

- **Active `toolchain`** — update both `go` and `toolchain` to the target version.
- **Commented `// toolchain`** — keep it commented; update only the version on
  that line (e.g. `// toolchain go1.26.4`). Do not uncomment it.
- **No `toolchain` line** — update `go` only; do not add a `toolchain` directive.

After changing `go`, run `go mod tidy`.

## Other common pins

```bash
# container images, any UBI major
grep -rn 'registry\.access\.redhat\.com/ubi[0-9]*/go-toolset' .

# go.mod directives
grep -n '^go [0-9]*\.[0-9]*\|toolchain go' go.mod

# CI and build files
grep -rn 'GOTOOLCHAIN\|GOSECGOVERSION\|go-version\|GO_VERSION' .github/ Makefile .gitlab-ci.yml 2>/dev/null
```

Files often named: `.go-version`, `.tool-versions`, `Jenkinsfile`, `.tekton/*`,
`build/*.yaml`.

When a workflow uses `go-version-file: "go.mod"`, leave it unchanged — it follows
`go.mod` automatically.

## govulncheck output cues

Stdlib fix (justifies a Go bump):

```text
Vulnerability #1: GO-2024-3107
  Found in: stdlib@go1.22.2
  Fixed in: stdlib@go1.22.7
```

Module fix (dependency bump, not a Go bump):

```text
Vulnerability #2: GO-2024-3105
  Found in: golang.org/x/net@v0.17.0
  Fixed in: golang.org/x/net@v0.23.0
```

## Registry API

Tags are paginated at:

`https://registry.access.redhat.com/v2/<image>/tags/list`

where `<image>` is `ubi9/go-toolset`, `ubi10/go-toolset`, and so on. The bundled
scripts handle pagination, skip `-source` tags, and sort build suffixes
correctly. Querying manually requires following `Link: rel="next"` headers.

## When the toolset tag is missing

Do not substitute:

- a different patch version
- a major.minor alias when the fix requires a specific patch
- a different image family (`ubi8`, `ubi9` when the repo builds on `ubi10`, or
  non-Red-Hat images)

Report the gap and list nearby available tags with `list-toolset-tags.sh`.

## eval-hub profile

The eval-hub repository adds these specifics on top of the generic workflow:

| Item | Value |
| --- | --- |
| Toolset image | `registry.access.redhat.com/ubi10/go-toolset`, pinned to the major.minor tag in `Containerfile` (builder stage) |
| `go.mod` | the `go` directive carries a patch version (currently `go 1.27.3`) |
| CI pins | `.github/workflows/ci.yml` sets `GOTOOLCHAIN: go1.XX.Y` and `GOSECGOVERSION: go1.XX.Y` |
| Lint | `make fmt lint` (`go fmt`, `go vet`, `golangci-lint`); the linter is pinned by `GOLANGCI_LINT_VERSION` in `Makefile` and `version` in `.github/workflows/golangci-lint.yml`, and both must move with `go.mod` — Go 1.27 needs `v2.14.0` or newer |
| Tests | `make test` (unit tests plus a short fuzz pass) |

The policy that the Go version must exist in `go-toolset` before `go.mod` is
updated is documented in the eval-hub `CLAUDE.md`.
