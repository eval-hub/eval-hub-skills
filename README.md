# eval-hub-skills

Agent Skills for EvalHub, following the [agentskills.io](https://agentskills.io) open format.

These skills enable AI coding agents (Claude Code, Copilot, Codex, etc.) to discover and execute EvalHub model evaluations during development sessions.

## Skills

| Skill | Description |
|-------|-------------|
| `eval-hub` | Evaluate AI/ML models, run benchmarks, manage evaluation jobs, follow EDD workflows |

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

Clone the repo and symlink the skill into `~/.claude/skills/`:

```bash
git clone https://github.com/eval-hub/eval-hub-skills
cd eval-hub-skills
make install
```

Changes to the skill source are reflected immediately without reinstalling.

### Uninstall

```bash
make uninstall
```

### Update

```bash
make update
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

Once installed, the skill is automatically discovered by Claude Code. Ask naturally:

- "Evaluate my model for safety"
- "List available evaluation providers"
- "What benchmarks are available for safety testing?"
- "Run a safety scan on my model"
- "Check the status of my evaluation job"
- "What providers target agentic systems?"

## License

Apache-2.0
