# Development skills (`dev-skills/`)

Skills in this directory are **maintainer and developer workflows for the
eval-hub repositories**. They follow the same [agentskills.io](https://agentskills.io)
`SKILL.md` format and are published as **separate, opt-in marketplace plugins**,
so installing `evalhub` does not install them for end users.

## Skills

| Skill | Plugin | Use it when |
| ----- | ------ | ----------- |
| `evalhub-bug-review` | `evalhub-bug-review@evalhub` | Reviewing an eval-hub or eval-hub-contrib pull request, branch, commit range, or working-tree change for bugs. Produces a severity-ranked findings table and never edits code. |
| [`benchmark-onboarding`](#benchmark-onboarding) | `benchmark-onboarding@evalhub` | Onboarding a benchmark from upstream task links through catalog changes, connected/disconnected API tests, image validation, a QA report, and PRs. |
| `fix-fvt-test` | `fix-fvt-test@evalhub` | Diagnosing and fixing a failing FVT (godog) scenario on an OpenShift AI cluster, from the JUnit report, test log, and pod logs. |
| `golang-toolchain-update` | `golang-toolchain-update@evalhub` | Auditing a Go repository for CVEs and updating Go only when the target repository's go-toolset image (`ubi9`/`ubi10`) publishes the required tag. Two modes: minimal CVE remediation and latest-available upgrade. |
| `release-notes` | `release-notes@evalhub` | Drafting OpenSSF-compliant, human-readable GitHub release notes for a tag or version. |

## Using a dev skill

### Claude Code (recommended)

Register the marketplace once:

```text
/plugin marketplace add eval-hub/eval-hub-skills
```

Then install the skills you want with **project scope**, so the plugin is
recorded as enabled for everyone working in this repository:

```shell
claude plugin install evalhub-bug-review@evalhub --scope project
```

Inside a session, `/plugin install <skill>@evalhub` opens the plugin panel, where
you can review what it adds and choose **Install for all collaborators on this
repository (project scope)**.

A committed `.claude/settings.json` declares the marketplace and **enables** the
plugins for everyone:

```json
{
  "extraKnownMarketplaces": {
    "evalhub": { "source": { "source": "github", "repo": "eval-hub/eval-hub-skills" } }
  },
  "enabledPlugins": {
    "evalhub-bug-review@evalhub": true,
    "fix-fvt-test@evalhub": true,
    "golang-toolchain-update@evalhub": true,
    "release-notes@evalhub": true
  }
}
```

Enabling is not downloading: the plugin files live in each machine's plugin
cache, so each collaborator installs them once (`--scope project`, as above).
Claude Code also clones a declared marketplace and downloads its enabled plugins
in the background once a session starts, so the explicit install matters when you
want the skill immediately after cloning, when you are offline, or when you want
to review what a plugin adds before it runs.

### Other harnesses

`make install-all` only links the four `evalhub*` skills, so dev skills are not
installed automatically. Symlink the ones you need, or attach the skill file:

```bash
# Claude Code / any harness that reads ~/.claude/skills
ln -s "$PWD/dev-skills/evalhub-bug-review" "$HOME/.claude/skills/evalhub-bug-review"
```

```text
# Cursor / Codex: reference the skill file directly
@dev-skills/evalhub-bug-review/SKILL.md
```

Then invoke it by name (for example `/evalhub-bug-review`) from a checkout of the
repository the skill operates on.

## Benchmark onboarding

Set up a [local test profile](benchmark-onboarding/references/environment.md)
once, then give the skill the benchmark, provider, and upstream task URL.

```text
Use benchmark-onboarding.
Benchmark: DROP
Provider: inspect
Upstream URL: https://github.com/UKGovernmentBEIS/inspect_evals/blob/v0.26.0/src/inspect_evals/drop/drop.py
```

The skill discovers task options from the pinned framework and adapter.
It reports confirmed blockers during preflight. For a viable task, it
provisions missing test resources, runs connected and disconnected API
scenarios, and opens the required PRs with the QA report. Ask for preflight
only when you want a feasibility check. You can also attach the
[skill file](benchmark-onboarding/SKILL.md) directly.

Sign in to GitHub, OpenShift, and the test registry in advance. The tool host
can still require approval for an action.

## Why these are separate plugins

`evalhub`, `evalhub-discovery`, `evalhub-eval`, and `evalhub-jobs` are the
default plugin skills. Each `dev-skills/` skill is published as its own plugin so
maintainer workflows are installed only by people who ask for them, and so they
can be enabled per project rather than globally.

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
