#!/usr/bin/env python3
"""List go-toolset tags, optionally filtered by version prefix."""

from __future__ import annotations

import argparse
import re
import sys
import urllib.error

from registry_utils import (
    fetch_all_tags,
    filter_tags,
    resolve_image_with_source,
    tag_sort_key,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="List go-toolset tags, newest first.",
        epilog="Image precedence: --image, GO_TOOLSET_IMAGE, container file, ubi10/go-toolset.",
    )
    parser.add_argument("prefix", nargs="?", default="", help="version prefix, e.g. 1.26 or 1.26.4")
    parser.add_argument("--image", help="go-toolset image, e.g. ubi10/go-toolset")
    parser.add_argument(
        "--root", default=".", help="repository root used to detect the image (default: .)"
    )
    args = parser.parse_args()

    if args.prefix and not re.fullmatch(r"[0-9]+(\.[0-9]+(\.[0-9]+)?)?", args.prefix):
        print(f"Invalid version prefix: {args.prefix}", file=sys.stderr)
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
    matches = filter_tags(tags, prefix=args.prefix or None)
    for tag in sorted(set(matches), key=tag_sort_key, reverse=True):
        print(tag)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
