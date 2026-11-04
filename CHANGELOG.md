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

### Changed
- `settings.local.json` simplified (permissions moved to committed `settings.json`)
- `golang-cve-update` renamed to `golang-toolchain-update`: the go-toolset image is resolved from the target repository (or `--image` / `GO_TOOLSET_IMAGE`) instead of being hardcoded to `ubi9`, and a `latest` mode was added. The marketplace plugin name changed accordingly, so existing plugin installs must be reinstalled
- `make lint`, CI, and pre-commit now cover `dev-skills/`
- `dev-skills/README.md` and the README development-skills section now document the plugin install path (plus project-level `extraKnownMarketplaces` / `enabledPlugins`) instead of describing dev skills as unpublished
- install docs now note that Claude Code also clones a declared marketplace and downloads enabled plugins in the background, so the explicit project-scope install is the immediate/offline path
- `dev-skills/evalhub-bug-review` now reviews cross-repo adapter and catalog coupling: a PR body note such as "deploy its images together with these catalog changes" is verified against the referenced `eval-hub-contrib` PR's merge state, the adapter code on contrib's default branch, and the provider YAML it still declares

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
