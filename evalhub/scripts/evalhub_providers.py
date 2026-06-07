#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["eval-hub-sdk[client] @ file:///home/rui/Sync/code/experiments/features/eval-service/poc/eval-hub-sdk"]
# ///
"""List EvalHub providers and benchmarks with agent discoverability metadata."""

import argparse
import json
import os


def get_client():
    from evalhub import SyncEvalHubClient

    return SyncEvalHubClient(
        base_url=os.environ.get("EVALHUB_BASE_URL", ""),
        auth_token=os.environ.get("EVALHUB_TOKEN"),
        tenant=os.environ.get("EVALHUB_TENANT"),
        insecure=os.environ.get("EVALHUB_INSECURE", "").lower() in ("1", "true"),
    )


def _extract_agent(obj):
    """Extract the agent metadata block from a provider or benchmark object."""
    if hasattr(obj, "agent") and obj.agent is not None:
        a = obj.agent
        return a.model_dump() if hasattr(a, "model_dump") else vars(a)
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="List EvalHub providers and benchmarks")
    parser.add_argument("provider_id", nargs="?", help="Get a specific provider by ID")
    parser.add_argument("--benchmarks", action="store_true", help="Include benchmark details")
    parser.add_argument("--provider", help="Filter benchmarks by provider ID (with --benchmarks)")
    parser.add_argument("--category", help="Filter benchmarks by category (with --benchmarks)")
    parser.add_argument(
        "--agent", action="store_true", help="Include agent discoverability metadata"
    )
    parser.add_argument(
        "--target-type",
        choices=["model", "agent", "inference_server"],
        help="Filter providers by target type (model, agent, inference_server)",
    )
    parser.add_argument(
        "--evaluates", help="Filter providers whose agent.evaluates contains this tag"
    )
    args = parser.parse_args()

    client = get_client()

    if args.provider_id:
        provider = client.providers.get(args.provider_id)
        result = provider.model_dump() if hasattr(provider, "model_dump") else vars(provider)
        print(json.dumps(result, indent=2, default=str))
        return

    if args.benchmarks:
        benchmarks = client.benchmarks.list(
            provider_id=args.provider,
            category=args.category,
        )
        result = [b.model_dump() if hasattr(b, "model_dump") else vars(b) for b in benchmarks]
        print(json.dumps(result, indent=2, default=str))
        return

    providers = client.providers.list()
    result = []
    for p in providers:
        agent_meta = _extract_agent(p)

        if args.target_type and agent_meta:
            if agent_meta.get("target_type") != args.target_type:
                continue
        elif args.target_type and not agent_meta:
            continue

        if args.evaluates and agent_meta:
            evaluates = agent_meta.get("evaluates") or []
            if args.evaluates not in evaluates:
                continue
        elif args.evaluates and not agent_meta:
            continue

        entry = {
            "id": p.resource.id if hasattr(p, "resource") else getattr(p, "id", None),
            "name": p.name,
        }
        if hasattr(p, "description") and p.description:
            entry["description"] = p.description

        if args.agent and agent_meta:
            entry["agent"] = agent_meta
        elif agent_meta:
            entry["summary"] = agent_meta.get("summary", "")
            entry["target_type"] = agent_meta.get("target_type", "")
            entry["evaluates"] = agent_meta.get("evaluates", [])

        result.append(entry)
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
