#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["eval-hub-sdk[client] @ file:///home/rui/Sync/code/experiments/features/eval-service/poc/eval-hub-sdk"]
# ///
"""Validate EvalHub connection configuration and check service health."""

import json
import os
import sys


def main() -> None:
    missing = []
    for var in ("EVALHUB_BASE_URL", "EVALHUB_TOKEN", "EVALHUB_TENANT"):
        if not os.environ.get(var):
            missing.append(var)

    if missing:
        print(
            json.dumps(
                {"ok": False, "error": f"Missing environment variables: {', '.join(missing)}"}
            )
        )
        sys.exit(1)

    from evalhub import SyncEvalHubClient

    client = SyncEvalHubClient(
        base_url=os.environ["EVALHUB_BASE_URL"],
        auth_token=os.environ["EVALHUB_TOKEN"],
        tenant=os.environ["EVALHUB_TENANT"],
        insecure=os.environ.get("EVALHUB_INSECURE", "").lower() in ("1", "true"),
    )

    try:
        health = client.health()
        print(
            json.dumps(
                {
                    "ok": True,
                    "base_url": os.environ["EVALHUB_BASE_URL"],
                    "tenant": os.environ["EVALHUB_TENANT"],
                    "health": health,
                },
                indent=2,
                default=str,
            )
        )
    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
