#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["eval-hub-sdk[client] @ file:///home/rui/Sync/code/experiments/features/eval-service/poc/eval-hub-sdk"]
# ///
"""List EvalHub benchmark collections with agent discoverability metadata."""

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
    """Extract the agent metadata block from an object."""
    if hasattr(obj, "agent") and obj.agent is not None:
        a = obj.agent
        return a.model_dump() if hasattr(a, "model_dump") else vars(a)
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="List EvalHub benchmark collections")
    parser.add_argument("collection_id", nargs="?", help="Get a specific collection by ID")
    parser.add_argument(
        "--agent", action="store_true", help="Include agent discoverability metadata"
    )
    parser.add_argument(
        "--evaluates", help="Filter collections whose agent.evaluates contains this tag"
    )
    args = parser.parse_args()

    client = get_client()

    if args.collection_id:
        collection = client.collections.get(args.collection_id)
        result = collection.model_dump() if hasattr(collection, "model_dump") else vars(collection)
        print(json.dumps(result, indent=2, default=str))
        return

    collections = client.collections.list()
    result = []
    for c in collections:
        agent_meta = _extract_agent(c)

        if args.evaluates and agent_meta:
            evaluates = agent_meta.get("evaluates") or []
            if args.evaluates not in evaluates:
                continue
        elif args.evaluates and not agent_meta:
            continue

        entry = {
            "id": c.resource.id if hasattr(c, "resource") else getattr(c, "id", None),
            "name": c.name,
        }
        if hasattr(c, "description") and c.description:
            entry["description"] = c.description
        cat = getattr(c, "category", None)
        if cat:
            entry["category"] = cat

        if args.agent and agent_meta:
            entry["agent"] = agent_meta
        elif agent_meta:
            entry["summary"] = agent_meta.get("summary", "")
            entry["evaluates"] = agent_meta.get("evaluates", [])

        result.append(entry)
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
