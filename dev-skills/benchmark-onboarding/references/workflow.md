# Benchmark source, implementation, and validation workflow

## Source and support audit

For every supplied link, identify the benchmark ID, framework task name, pinned
framework version, dataset repository/subset/split, license or access gate,
custom dataset code, tokenizer, scoring type, metrics, expected direction, and
model endpoint requirements. Read the task configuration used by the pinned
framework release; a high-level README can omit loader behavior and defaults.

Build a support matrix before editing:

| Surface | What to verify |
| --- | --- |
| Source task | Task ID, config, dataset repo/subset/split, custom code, license/access |
| Contrib adapter | Provider ID, task mapping, declared parameters, requirements, container base |
| EvalHub catalog | Provider and benchmark IDs, metrics, score direction, threshold, runtime image |
| API tests | Request parameters, annotations, result assertions, offline assets |

Check both repositories and their open PRs first. The same framework may be
exposed through distinct providers (for example, the native
`lm_evaluation_harness` runtime and the contrib `lm-eval` adapter). Use the
provider the user intends to add; do not assume one provider's registration
updates the other.

If the task is already present, compare its metadata and tests against the
source. Reuse existing coverage and report any gap. Add only missing or incorrect
pieces. Do not create a benchmark PR merely to attach a report when no code or
test change is needed.

## Changes across repositories

Read repository `AGENTS.md`, `CLAUDE.md`, `CONTRIBUTING.md`, provider examples,
PR templates, and commit-message rules before editing. Keep one fresh branch per
repository, based on its current `main`; inspect the diff and check for an open
equivalent PR before publishing.

In `eval-hub-contrib`, update the adapter's provider definition, task registry
or generator inputs, dependency pins, runtime code, and adapter tests only as
required by the source task. Verify that every declared option is implemented
and that task metadata comes from the same pinned framework release used in the
image. Keep dataset scripts and `trust_remote_code` behavior explicit.

In `eval-hub`, update the matching provider/catalog entries, collection entries
when requested by the catalog design, API feature data, expected-result fields,
and asset stagers or manifests required by disconnected testing. Keep the
provider ID and benchmark ID consistent with contrib. Follow the test helpers
already in `tests/features`; do not invent a parallel schema or fixture format.

## Parameter coverage

Read the provider schema, adapter parameter handling, and upstream task config.
Create a table for every applicable parameter with its declared type/default,
supported values, test payload, and expected behavior. Include each meaningful
enum value and both sides of relevant booleans. Cover valid boundaries and
document invalid values only where the API promises validation. Use focused
cases or pairwise combinations to avoid an unbounded Cartesian product, while
still asserting every applicable parameter at least once.

Separate task options from runtime controls. A task's dataset subset, split,
few-shot count, and tokenizer can be benchmark-specific; model URL, batch size,
timeouts, offline references, and authentication may be provider/runtime
controls. Do not include generation-only fields in a log-likelihood task unless
the adapter consumes them.

## API scenarios and cluster validation

Read `eval-hub/tests/features/README.md` and nearby scenarios for the current
tags and payload helpers. Add focused connected and disconnected scenarios with
the repository's `@connected`, `@disconnected`, `@cluster`, and provider/evaluation
annotations as appropriate. Use the Jsonnet benchmark helper when available so
connected tokenizer defaults and disconnected `test_data_ref` behavior match
the test harness.

For connected runs, submit through the EvalHub API using the intended provider,
model endpoint, and an existing auth Secret reference. Confirm the request is
accepted, the job and benchmark reach a terminal successful state, the dataset
and tokenizer load, expected metrics and metadata are returned, and the sample
limit is honored.

For disconnected runs, stage the exact dataset cache and tokenizer at the
fixture location expected by the adapter. Ensure the evaluation job is subject
to the disconnected or egress-restricted path while the administrative staging
step can access its source. A physical disconnected cluster needs pre-staged
assets; an `hf_offline` flag without local assets does not prove offline support.
If an init container fails before the adapter starts, capture its logs and
Kubernetes Job state because the EvalHub API may not receive a terminal event.

When the provider exposes an offline control such as `hf_offline`, set it for
the disconnected case and assert the returned metadata reports it. For
EvalHub's benchmark FVTs, use the shared `benchmark()` helper so the offline
case receives its benchmark-scoped S3 `test_data_ref` and `/test_data/tokenizer`
path. Confirm the init container downloaded files and the adapter loaded the
dataset from the staged path with downloads disabled.

Build with the repository's image target and inspect the selected cluster node
architecture (`kubernetes.io/arch`). Rebuild for the target platform if the
local Podman host produced a different architecture. Use a unique test image
tag, verify its digest, deploy through the established test workflow, and
record the actual image running in the evaluation pod. Do not overwrite shared
`latest` or production tags.

## Reporting and PRs

Use [report-template.md](report-template.md). Preserve test timestamps, provider
and benchmark IDs, image digest/platform, request parameter matrix, dataset and
tokenizer source, API/Kubernetes states, and sanitized relevant log excerpts.
For failures, separate benchmark defects from missing credentials, missing
offline fixtures, model endpoint problems, and test infrastructure failures;
state the evidence and confidence for each cause.

Include the Markdown report in the contrib PR body. Link the same report and
contrib PR from the eval-hub PR. If a repository has no required change, do not
open a duplicate PR; explain that in the report. Never include bearer tokens,
model keys, Hugging Face tokens, or Secret contents.
