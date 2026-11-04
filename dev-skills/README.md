# Development skills (`dev-skills/`)

Skills in this directory are **maintainer and developer workflows for the
eval-hub repositories**. They are not part of the published `evalhub` plugin, but
they follow the same [agentskills.io](https://agentskills.io) `SKILL.md` format.

## Skills

| Skill | Use it when |
| ----- | ----------- |
| `evalhub-bug-review` | Reviewing an eval-hub pull request, branch, commit range, or working-tree change for bugs. Produces a severity-ranked findings table and never edits code. |
| `fix-fvt-test` | Diagnosing and fixing a failing FVT (godog) scenario on an OpenShift AI cluster, from the JUnit report, test log, and pod logs. |
| `golang-toolchain-update` | Auditing a Go repository for CVEs and updating Go only when the target repository's go-toolset image (`ubi9`/`ubi10`) publishes the required tag. Two modes: minimal CVE remediation and latest-available upgrade. |
| `release-notes` | Drafting OpenSSF-compliant, human-readable GitHub release notes for a tag or version. |

## Using a dev skill

`make install-all` only links the four published plugin skills, so dev skills are
not installed automatically. Make one available to your agent in whichever way
your harness supports, for example:

```bash
# Claude Code: symlink the skill directory into your personal skills directory
ln -s "$PWD/dev-skills/evalhub-bug-review" "$HOME/.claude/skills/evalhub-bug-review"
```

```text
# Cursor / Codex: reference the skill file directly
@dev-skills/evalhub-bug-review/SKILL.md
```

Then invoke it by name (for example `/evalhub-bug-review`) from a checkout of the
repository the skill operates on.

## Why these live outside the plugin

`evalhub`, `evalhub-discovery`, `evalhub-eval`, and `evalhub-jobs` are the
published plugin skills. `dev-skills/` is deliberately excluded from the plugin
payload so maintainer workflows are never installed for end users.

## Linting

`skillsaw` is configured at the repository root (`.skillsaw.yaml`). Lint a skill
from its own directory:

```bash
cd dev-skills/evalhub-bug-review && uvx skillsaw lint SKILL.md
```

## Go toolchain modes

`golang-toolchain-update` replaces the earlier `golang-cve-update` and
`golang-version-update` skills, which duplicated the same go-toolset gate with
different images (`ubi9` vs `ubi10`). It resolves the image from the target
repository's container file, so one skill covers both the `ubi9` and `ubi10`
worlds:

- `cve` mode — minimal Go bump driven by `govulncheck` findings
- `latest` mode — newest available patch, or a requested major.minor

Override the image with `--image ubiX/go-toolset` or `GO_TOOLSET_IMAGE` when a
repository builds on an image that is not referenced in its container file.
