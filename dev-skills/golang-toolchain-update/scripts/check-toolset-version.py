#!/usr/bin/env python3
"""Verify a Go version tag exists on a Red Hat go-toolset image."""

from __future__ import annotations

import argparse
import re
import sys
import urllib.error

from registry_utils import fetch_all_tags, find_matching_tag, resolve_image_with_source


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Exit 0 when the go-toolset image publishes a tag for the Go version.",
        epilog="Image precedence: --image, GO_TOOLSET_IMAGE, container file, ubi10/go-toolset.",
    )
    parser.add_argument("version", help="Go version, e.g. 1.26.4")
    parser.add_argument("--image", help="go-toolset image, e.g. ubi10/go-toolset")
    parser.add_argument(
        "--root", default=".", help="repository root used to detect the image (default: .)"
    )
    args = parser.parse_args()

    if not re.fullmatch(r"[0-9]+\.[0-9]+(\.[0-9]+)?", args.version):
        print(f"Invalid Go version format: {args.version}", file=sys.stderr)
        return 2

    try:
        image, source = resolve_image_with_source(args.image, args.root)
        tags = fetch_all_tags(image)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except urllib.error.URLError as exc:
        print(f"Failed to query registry: {exc}", file=sys.stderr)
        return 2

    print(f"image: {image} (from {source})", file=sys.stderr)
    match = find_matching_tag(args.version, tags)
    if match:
        print(match)
        return 0

    print(f"No {image} tag found for Go {args.version}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
