# Changelog

## [0.2.0] — unreleased

### Added
- Three focused sub-skills: `evalhub-discovery`, `evalhub-eval`, `evalhub-jobs`
- `evalhub/scripts/state.py` — key-value state persistence for long-running jobs (survives context compression)
- `AGENTS.md` — guidance for AI agents working on the plugin itself
- `.skillsaw.yaml` — skillsaw linter config with context budget thresholds
- `.claude/settings.json` — committed scoped permissions and `SessionStart` recovery hook
- `.mcp.json` — EvalHub MCP server registration via `EVALHUB_MCP_URL`
- MCP mode section in `evalhub/SKILL.md` with tool and resource mapping tables
- `--dry-run` flag on `evalhub_eval.py` — inspect request JSON without submitting
- `eval/` directory with 10 evaluation scenarios (input + expected pairs)
- Makefile targets: `install-all`, `uninstall-all`, `update-all`
- skillsaw added to `make lint`
- `dev-skills/golang-toolchain-update` — CVE-aware Go toolchain update with go-toolset image auto-detection (`ubi9`/`ubi10`), `cve` and `latest` modes, and unit tests
- `evalhub-bug-review`, `fix-fvt-test`, and `release-notes` published as opt-in marketplace plugins, joining `golang-toolchain-update`, so every `dev-skills/` skill can be installed with `/plugin install <skill>@evalhub`
- `dev-skills/evalhub-bug-review/checklists-contrib.md` — §13–§22 probes for `eval-hub-contrib`: the `FrameworkAdapter`/JobPhase contract, `provider.yaml` catalog drift, credential roles and offline assets, subprocess lifecycle, results/artifacts/MLflow, dependencies and Containerfile, tests and CI wiring, cross-repo coupling, the high-yield quick scan and the repository's own conventions

### Changed
- `settings.local.json` simplified (permissions moved to committed `settings.json`)
- `golang-cve-update` renamed to `golang-toolchain-update`: the go-toolset image is resolved from the target repository (or `--image` / `GO_TOOLSET_IMAGE`) instead of being hardcoded to `ubi9`, and a `latest` mode was added. The marketplace plugin name changed accordingly, so existing plugin installs must be reinstalled
- `make lint`, CI, and pre-commit now cover `dev-skills/`
- `dev-skills/README.md` and the README development-skills section now document the plugin install path (plus project-level `extraKnownMarketplaces` / `enabledPlugins`) instead of describing dev skills as unpublished
- install docs now note that Claude Code also clones a declared marketplace and downloads enabled plugins in the background, so the explicit project-scope install is the immediate/offline path
- `dev-skills/evalhub-bug-review` now reviews cross-repo adapter and catalog coupling: a PR body note such as "deploy its images together with these catalog changes" is verified against the referenced `eval-hub-contrib` PR's merge state, the adapter code on contrib's default branch, and the provider YAML it still declares. The adapter probes fetch the catalog before grepping it, so an HTTP error or transport failure is reported as an unverified contract instead of catalog drift
- `dev-skills/evalhub-bug-review/SKILL.md` is back under the 150-line limit: step detail lives in `checklists.md`, and the severity rubric and rating rules moved to `report-template.md`
- `dev-skills/golang-toolchain-update` now moves the `golangci-lint` pin with `go.mod`: Step 6 covers `GOLANGCI_LINT_VERSION` in the `Makefile` and `version` in `.github/workflows/golangci-lint.yml`, and the straggler sweep greps for both. A linter that lags the target Go version fails `make lint` with an export-data error that reads as pre-existing, which is how eval-hub shipped a Go bump without the matching linter bump
- `dev-skills/golang-toolchain-update` picks that pin from the binary and the release notes instead of from release metadata: a release's `go.mod` directive only bounds the toolchain that can build it, and its bundled `golang.org/x/tools` version says nothing about export-data support, so Step 6 checks `golangci-lint version` on the binary that CI actually runs (it reports `built with goX.Y.Z`) and the compatibility notes for the target Go release before recording the pin and the oldest supported release
- `dev-skills/evalhub-bug-review` no longer claims `"/review-bugbot"` as a trigger, so it stops competing with the harness's own `/review-bugbot` for the same request; the body still cites it as the workflow it adapts. Step 5 now verifies formatting read-only with `gofmt -l` plus `git diff --stat` instead of `make fmt`, which rewrote files and contradicted the skill's no-mutation guarantee
- `dev-skills/evalhub-bug-review` reviews `eval-hub-contrib` as well as `eval-hub`: Step 0 picks the repository from the PR URL or the tree, then Steps 1, 2, 4, 5, 6 and 7 take the contrib half — `.venv/`/`__pycache__/` diffs are ignorable and lockfile-only bumps stay in scope for the dependency checks, `provider.yaml` → `main.py` → tests → image → CI → docs is the review order, `make test-<adapter>` is not run just to see output (an existing adapter venv is reused and a suite with no venv is reported **not run**), and commitizen's `<type>(<adapter>)` scope plus the repository's own `Assisted-by:`/`Signed-off-by:` trailers replace `make fmt lint` and `make -s assisted-by-trailer`. Declared-but-unimplemented `provider.yaml` entries, out-of-order JobPhase emissions and env-var credential fallbacks are named as the recurring adapter defects. The marketplace plugin is bumped to 0.2.0, but a bump alone does not refresh an existing cache: 0.1.0 installs must update the marketplace and then the plugin, and reload plugins or start a new session before the new content is loaded. Automatic updates only apply when plugin auto-update is enabled
- `dev-skills/evalhub-bug-review` now leaves the reviewed checkout as it found it: both §12 catalog probes delete the `mktemp` file they download into (the §20 probe already did), Step 5b runs an adapter suite with `PYTHONDONTWRITEBYTECODE=1` and `-p no:cacheprovider` so `pytest` no longer leaves `.pytest_cache/` or `__pycache__/` in the adapter tree, and Step 5 captures a `git status --porcelain --ignored` baseline before the probes and diffs it afterwards (plain `git status` omits ignored paths), removing only the caches the review created instead of pre-existing ones. Step 5a also records that `make lint` installs golangci-lint under `bin/tools/` and `make verify-api-docs` runs `npm i @redocly/cli` when `node_modules/` is missing (which can rewrite the tracked `package-lock.json`), and Step 7 documents the commands that retract a posted review: `DELETE .../pulls/comments/<id>` for a comment, and `PUT .../reviews/<id>/dismissals` with its required `message` body field for a submitted review

### Removed
- `golang-version-update` skill and its `fetch-go-toolset-tags.sh` script (merged into `golang-toolchain-update`)

## [0.1.0] — initial release

### Added
- `evalhub` skill with `SKILL.md` covering discovery, evaluation, and job lifecycle
- Python scripts: `evalhub_check.py`, `evalhub_collections.py`, `evalhub_eval.py`, `evalhub_logs.py`, `evalhub_providers.py`, `evalhub_status.py`
- References: `API.md`, `EDD.md`
- Assets: `eval-job-template.json`
- Makefile: `lint`, `test`, `install`, `uninstall`, `update`, `check`
- Unit tests (no live service required)
- CI: ruff, shellcheck
