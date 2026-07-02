# eval-hub-skills

[![Lint](https://github.com/ruivieira/eval-hub-skills/actions/workflows/lint.yml/badge.svg)](https://github.com/ruivieira/eval-hub-skills/actions/workflows/lint.yml)
[![Test](https://github.com/ruivieira/eval-hub-skills/actions/workflows/test.yml/badge.svg)](https://github.com/ruivieira/eval-hub-skills/actions/workflows/test.yml)
[![Validate](https://github.com/ruivieira/eval-hub-skills/actions/workflows/validate.yml/badge.svg)](https://github.com/ruivieira/eval-hub-skills/actions/workflows/validate.yml)

Agent Skills for EvalHub, following the [agentskills.io](https://agentskills.io) open format.

These skills enable AI coding agents (Claude Code, Copilot, Codex, etc.) to discover and execute EvalHub model evaluations during development sessions.

## Skills

| Skill | Description |
| ----- | ----------- |
| `evalhub` | Full skill — discovery, evaluation, job lifecycle, and EDD workflows |
| `evalhub-discovery` | Discover providers, benchmarks, and collections; read agent metadata |
| `evalhub-eval` | Submit evaluation jobs against benchmarks or collections |
| `evalhub-jobs` | Monitor, wait on, cancel, and fetch logs for evaluation jobs |

## Installation

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (scripts use PEP 723 inline metadata for auto-dependency resolution)
- Network access to an EvalHub service
- `EVALHUB_BASE_URL`, `EVALHUB_TOKEN`, `EVALHUB_TENANT` environment variables

### Install via Claude Code plugin (recommended)

```bash
/plugin marketplace add eval-hub/eval-hub-skills
/plugin install evalhub@evalhub
```

The skill is then available as `/evalhub:evalhub` in any Claude Code session.

### Install locally (development)

Clone the repo and symlink the skills into `~/.claude/skills/`:

```bash
git clone https://github.com/eval-hub/eval-hub-skills
cd eval-hub-skills
make install-all   # installs all four skills
```

To install only the primary skill:

```bash
make install
```

Changes to the skill source are reflected immediately without reinstalling.

### Connect to an MCP server on a cluster

If EvalHub exposes an MCP server on your cluster, you can register it directly with Claude Code using the `claude mcp add` CLI command. EvalHub's MCP requires a bearer token and an `x-tenant` header (the namespace):

```bash
claude mcp add evalhub "$EVALHUB_BASE_URL/mcp" \
  --transport http \
  --header "Authorization: Bearer $EVALHUB_TOKEN" \
  --header "x-tenant: $EVALHUB_TENANT"
```

This writes the server into your local Claude Code config (`.claude/settings.json`). Use `--scope user` to register it globally across all projects instead.

> **Note:** OpenShift tokens expire. If you get 401 errors, refresh with `export EVALHUB_TOKEN="$(oc whoami -t)"` and re-run the command.

### Uninstall

```bash
make uninstall-all   # remove all skills
make uninstall       # remove primary skill only
```

### Update

```bash
make update-all
```

### Validate

```bash
make check
```

## Configuration

Set these environment variables before using the skill:

```bash
export EVALHUB_BASE_URL="https://evalhub.apps.cluster.example.com"
export EVALHUB_TOKEN="$(oc whoami -t)"
export EVALHUB_TENANT="eval-test"
```

Optionally, for clusters with self-signed certificates:

```bash
export EVALHUB_INSECURE=true
```

## Usage

Once installed, the skill is automatically discovered by Claude Code. Ask naturally in any session.

### Example: discover what providers are available

> **You:** What evaluation providers are available?

The skill fetches live metadata from the API and summarises each provider:

```md
Available providers:

- AgentDojo — Test agent resilience to prompt injection across realistic tool-use
  scenarios. Targets: agent. Evaluates: agent-safety, prompt-injection,
  tool-use-security.

- LM Evaluation Harness — Comprehensive evaluation framework with 180 benchmarks
  covering math, science, coding, safety, reasoning, and more.

- Garak — LLM vulnerability scanner and red-teaming framework.

- GuideLLM — Performance benchmarking for LLM inference servers.

- SWE-bench — Software engineering benchmark using real-world GitHub issues.

- Lighteval — Lightweight LLM evaluation from Hugging Face.
```

---

### Example: find providers for a specific use case

> **You:** Which providers can evaluate my agent for prompt injection?

```json
[
  {
    "id": "agentdojo",
    "name": "AgentDojo",
    "summary": "Test agent resilience to prompt injection across realistic tool-use scenarios",
    "target_type": "agent",
    "evaluates": ["agent-safety", "prompt-injection", "tool-use-security"]
  }
]
```

> **Claude:** AgentDojo is the right fit here. It runs your agent through realistic
> tool-use scenarios (workspace, Slack, banking, travel) and measures both utility
> (task completion) and security (injection resistance). The model must support
> tool/function calling via an OpenAI-compatible API.

---

### Example: list available evaluation collections

> **You:** What evaluation suites are available?

```json
[
  {
    "id": "standard-llm-evals-v1",
    "name": "Standard LLM Evaluation Suite v1",
    "category": "general"
  },
  {
    "id": "reasoning-v1",
    "name": "Reasoning v1",
    "category": "reasoning"
  },
  {
    "id": "coding-v1",
    "name": "Coding v1",
    "category": "code"
  },
  {
    "id": "instruction-following-v1",
    "name": "Instruction Following v1",
    "category": "instruction_following"
  },
  {
    "id": "long-context-v1",
    "name": "Long Context v1",
    "category": "long_context"
  },
  {
    "id": "toxicity-and-ethical-principles",
    "name": "Toxicity and Ethical Principles",
    "category": "safety"
  }
]
```

---

### Example: submit an evaluation job

> **You:** Run the standard LLM eval suite against my model at
> `http://vllm-svc:8000/v1` (model name: `mistral-7b-instruct`).

```json
{
  "resource": {
    "id": "eval-mistral-7b-instruct-a3f2c1",
    "created_at": "2026-06-07T14:23:11Z"
  },
  "name": "eval-mistral-7b-instruct",
  "state": "pending"
}
```

> **Claude:** Job submitted. ID: `eval-mistral-7b-instruct-a3f2c1`. The standard
> suite covers instruction following, reasoning, math, coding, and long-context tasks.
> It runs multiple benchmarks with 3 seeds each — expect it to take 30–60 minutes.
> Say "check the status" or "wait for it to finish" when you're ready.

---

### Example: check job status

> **You:** What's the status of my eval jobs?

```json
[
  {
    "id": "eval-mistral-7b-instruct-a3f2c1",
    "name": "eval-mistral-7b-instruct",
    "state": "running",
    "created_at": "2026-06-07T14:23:11Z"
  }
]
```

---

### Example: EDD — measure impact before and after a change

> **You:** I'm about to refactor my model's safety guardrails. What should I
> run before and after to measure the impact?
>
> **Claude:** I'd suggest this before/after plan using the live providers:
>
> **Before:** Run `toxicity-and-ethical-principles` (covers toxic content,
> truthfulness, and HHH alignment) and `garak` (vulnerability scan for known
> attack patterns) to establish a baseline.
>
> **After:** Run the same two suites. Diff the scores — a regression in
> `toxigen` or `truthfulqa_mc1` means the refactor weakened a safety property.
>
> Want me to kick off the baseline run now?

## Development skills

These skills are for use during the development of `eval-hub` components.

| Skill | Description |
| ----- | ----------- |
| `golang-cve-update` | Scans Go repositories for vulnerabilities. |

### golang-cve-update

**`golang-cve-update`** (`dev-skills/golang-cve-update/`) scans Go repositories for vulnerabilities with `govulncheck`, determines the minimum fixed Go version, and updates version pins in `go.mod`, container files, and CI only when a matching tag exists on `registry.access.redhat.com/ubi9/go-toolset`. If Red Hat has not published the required image yet, the skill reports the gap and leaves version files unchanged.

#### Installation

```shell
/plugin marketplace add eval-hub/eval-hub-skills
/plugin install golang-cve-update@evalhub
```

#### Using from another repository

The skill runs against whichever repository you have open in Claude Code — you do not
need `eval-hub-skills` checked out in that project.

1. Install the plugin (once), as above.
2. Open Claude Code in the target Go repository:

   ```bash
   cd /path/to/your-go-project
   claude
   ```

3. Invoke the skill explicitly or by intent:

   ```text
   /golang-cve-update:golang-cve-update
   ```

   Or ask naturally, for example:

   ```text
   Scan this Go repo for CVEs and bump the Go version only if ubi9/go-toolset has a matching tag.
   ```

Claude follows the workflow in `dev-skills/golang-cve-update/SKILL.md`: detect version
pins, run `govulncheck`, determine the target Go version, verify the Red Hat
go-toolset tag exists, then update files in **your** repository only when the gate
passes.

When running bundled scripts from another repository, use the skill's absolute path
(not a relative `scripts/...` path). For a local clone of this repo:

```bash
/path/to/eval-hub-skills/dev-skills/golang-cve-update/scripts/scan-vulnerabilities.sh
/path/to/eval-hub-skills/dev-skills/golang-cve-update/scripts/check-toolset-version.sh 1.26.4
```

`scan-vulnerabilities.sh` defaults to the current directory; run it from the target
repo root or pass the repo path as an argument.

**Prerequisites in the target repo:** Go installed, network access to
`registry.access.redhat.com`, and a scannable Go project (typically with `go.mod`).

## License

Apache-2.0
