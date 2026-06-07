#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["eval-hub-sdk[client] @ file:///home/rui/Sync/code/experiments/features/eval-service/poc/eval-hub-sdk"]
# ///
"""Get logs for an EvalHub evaluation job."""

import argparse
import json
import os
import sys

import httpx


def main() -> None:
    parser = argparse.ArgumentParser(description="Get EvalHub job logs")
    parser.add_argument("job_id", help="Job ID")
    parser.add_argument("--offset", type=int, default=0, help="Byte offset to start reading from")
    parser.add_argument("--raw", action="store_true", help="Print raw log content instead of JSON")
    args = parser.parse_args()

    base_url = os.environ.get("EVALHUB_BASE_URL", "")
    token = os.environ.get("EVALHUB_TOKEN", "")
    tenant = os.environ.get("EVALHUB_TENANT", "")
    insecure = os.environ.get("EVALHUB_INSECURE", "").lower() in ("1", "true")

    if not base_url or not token or not tenant:
        print(
            json.dumps(
                {"error": "EVALHUB_BASE_URL, EVALHUB_TOKEN, and EVALHUB_TENANT must be set"}
            ),
            file=sys.stderr,
        )
        sys.exit(1)

    url = f"{base_url.rstrip('/')}/api/v1/evaluations/jobs/{args.job_id}/logs"
    params = {}
    if args.offset:
        params["offset"] = args.offset

    try:
        response = httpx.get(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "X-Tenant": tenant,
            },
            params=params,
            verify=not insecure,
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()

        if args.raw:
            print(data.get("content", ""))
        else:
            print(json.dumps(data, indent=2))
    except httpx.HTTPStatusError as e:
        print(
            json.dumps({"error": f"HTTP {e.response.status_code}: {e.response.text}"}),
            file=sys.stderr,
        )
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
