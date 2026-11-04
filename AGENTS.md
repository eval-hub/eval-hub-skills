# AGENTS.md

Guidance for AI agents working on the eval-hub-skills plugin itself.

## Repository Layout

```
eval-hub-skills/
├── evalhub/                  # Primary skill (discovery + eval + jobs + EDD)
│   ├── SKILL.md              # Monolithic skill (kept for backward compat)
│   ├── scripts/              # All Python scripts — shared across all sub-skills
│   │   ├── evalhub_check.py
│   │   ├── evalhub_collections.py
│   │   ├── evalhub_eval.py
│   │   ├── evalhub_logs.py
│   │   ├── evalhub_providers.py
│   │   ├── evalhub_status.py
│   │   └── state.py
│   ├── references/           # API.md, EDD.md — referenced from SKILL.md files
│   └── assets/               # eval-job-template.json
├── evalhub-discovery/        # Sub-skill: provider/benchmark/collection discovery
│   └── SKILL.md
├── evalhub-eval/             # Sub-skill: job submission
│   └── SKILL.md
├── evalhub-jobs/             # Sub-skill: status, logs, cancel, polling
│   └── SKILL.md
├── eval/                     # Evaluation scenarios (input + expected pairs)
├── tests/                    # Unit tests (pytest, no live service required)
├── Makefile                  # lint, test, install-all, update-all
├── .skillsaw.yaml            # Skill linter config (context budget thresholds)
├── .mcp.json                 # MCP server registration (EVALHUB_MCP_URL)
└── .claude/
    ├── settings.json         # Committed: scoped Bash permissions + SessionStart hook
    └── settings.local.json   # Gitignored: env-specific MCP URL override
```

## Build Commands

```bash
make lint          # ruff + shellcheck + skillsaw
make test          # pytest (no live service)
make install-all   # symlink all skills into ~/.claude/skills/
make update-all    # re-link all skills after directory changes
make check         # validate skill structure
```

## Script Conventions

All scripts follow these invariants — keep them consistent:

- **PEP 723 inline metadata**: every script starts with `# /// script` + `requires-python` + `dependencies`
- **`get_client()` function**: each script defines its own `get_client()` that reads env vars directly
- **JSON output to stdout**: all scripts print a single JSON value (object or array) to stdout
- **Errors to stderr, exit 1**: error conditions print to stderr and exit with code 1
- **`2>/dev/null` for SDK scripts**: every SKILL.md example that invokes a bundled EvalHub SDK script (`evalhub/scripts/*.py`) includes this suffix to hide SDK diagnostics. Do not add it to shell tools such as `git`, `gh`, or `podman`, where it would hide real errors.
- **argparse**: all scripts use argparse for CLI args
- **No inline SDK imports at module level**: `from evalhub import ...` goes inside functions to allow `get_client()` to resolve after uv installs deps

## Adding a New Script

1. Copy the header from an existing script (`evalhub_check.py` is the simplest template)
2. Name it `evalhub_<noun>.py` — noun describes the resource type, not the action
3. Add `get_client()` with the standard env var block
4. Output JSON to stdout via `json.dumps(..., indent=2, default=str)`
5. Add a test in `tests/test_<noun>.py` using `unittest.mock.patch`
6. Add the script to the relevant SKILL.md with usage examples

## Extending SKILL.md Files

- Keep each sub-skill SKILL.md under 150 lines (enforced by `.skillsaw.yaml` at error threshold 8000 chars)
- Shared env var prerequisites go in sub-skill SKILL.md front-matter sections — don't reference AGENTS.md from SKILL.md
- When adding a new MCP resource or tool, update both the relevant sub-skill SKILL.md and the main `evalhub/SKILL.md`

## Environment Variables

| Variable | Purpose |
|----------|---------|
| `EVALHUB_BASE_URL` | EvalHub REST API base URL |
| `EVALHUB_TOKEN` | Bearer auth token |
| `EVALHUB_TENANT` | Kubernetes namespace / tenant |
| `EVALHUB_INSECURE` | Set to `1` or `true` to skip TLS verification |
| `EVALHUB_MCP_URL` | MCP server HTTP URL (optional; enables MCP mode) |

## Commit Conventions

Use [Conventional Commits](https://www.conventionalcommits.org/):
`feat(evalhub): ...`, `fix(scripts): ...`, `docs(skill): ...`

## SDK Dependency

Scripts depend on `eval-hub-sdk` via a local path reference in the PEP 723 header. When the SDK path changes, update all `# dependencies = [...]` blocks in every script.
