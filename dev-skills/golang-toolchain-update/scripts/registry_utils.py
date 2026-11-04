"""Shared helpers for Red Hat go-toolset registry queries.

The toolset image is not hardcoded: it can be passed explicitly, set with
``GO_TOOLSET_IMAGE``, detected from a container file in the target repository, or
falls back to :data:`DEFAULT_IMAGE`.
"""

from __future__ import annotations

import json
import os
import re
import time
import urllib.request
from pathlib import Path

REGISTRY = "https://registry.access.redhat.com"
DEFAULT_IMAGE = "ubi10/go-toolset"
CACHE_TTL_SEC = 300

_IMAGE_RE = re.compile(r"^ubi\d+/go-toolset$")
_IMAGE_IN_TEXT_RE = re.compile(r"registry\.access\.redhat\.com/(ubi\d+/go-toolset)")
_CONTAINER_FILES = ("Containerfile", "Dockerfile")


def normalize_image(image: str) -> str:
    """Normalize an image reference to ``ubiX/go-toolset``.

    Accepts ``ubi10/go-toolset`` and the fully qualified
    ``registry.access.redhat.com/ubi10/go-toolset``.
    """
    value = image.strip()
    value = value.removeprefix(f"{REGISTRY}/")
    value = value.removeprefix("registry.access.redhat.com/")
    if not _IMAGE_RE.fullmatch(value):
        raise ValueError(f"Unsupported go-toolset image: {image!r} (expected ubiX/go-toolset)")
    return value


def detect_image(root: str | Path = ".") -> str | None:
    """Return the go-toolset image referenced by a container file in *root*."""
    base = Path(root)
    candidates = [base / name for name in _CONTAINER_FILES]
    candidates += sorted(base.glob("Containerfile.*")) + sorted(base.glob("Dockerfile.*"))
    for path in candidates:
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        match = _IMAGE_IN_TEXT_RE.search(text)
        if match:
            return match.group(1)
    return None


def resolve_image_with_source(image: str | None = None, root: str | Path = ".") -> tuple[str, str]:
    """Resolve the toolset image and report where the choice came from.

    Precedence: explicit argument, ``GO_TOOLSET_IMAGE``, detection from a
    container file in *root*, then :data:`DEFAULT_IMAGE`.
    """
    if image:
        return normalize_image(image), "argument"
    env_image = os.environ.get("GO_TOOLSET_IMAGE")
    if env_image:
        return normalize_image(env_image), "GO_TOOLSET_IMAGE"
    detected = detect_image(root)
    if detected:
        return detected, "container file"
    return DEFAULT_IMAGE, "default"


def resolve_image(image: str | None = None, root: str | Path = ".") -> str:
    """Return only the resolved image name. See :func:`resolve_image_with_source`."""
    return resolve_image_with_source(image, root)[0]


def _cache_path(image: str) -> Path:
    base = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    slug = image.replace("/", "-")
    return base / "golang-toolchain-update" / f"{slug}-tags.json"


def _fetch_tags_from_registry(image: str) -> list[str]:
    url = f"{REGISTRY}/v2/{image}/tags/list"
    tags: list[str] = []
    while url:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read())
            tags.extend(data.get("tags", []))
            link = resp.headers.get("Link", "")
            url = None
            if 'rel="next"' in link:
                part = next(p for p in link.split(",") if 'rel="next"' in p)
                url = REGISTRY + part.split(";")[0].strip().strip("<>")
    return tags


def _no_cache() -> bool:
    return any(
        os.environ.get(name) == "1"
        for name in ("GOLANG_TOOLCHAIN_UPDATE_NO_CACHE", "GOLANG_CVE_UPDATE_NO_CACHE")
    )


def fetch_all_tags(image: str | None = None, *, root: str | Path = ".") -> list[str]:
    """Return all tags for the resolved go-toolset image, cached for 5 minutes."""
    resolved = resolve_image(image, root)
    if _no_cache():
        return _fetch_tags_from_registry(resolved)

    cache = _cache_path(resolved)
    if cache.is_file():
        try:
            data = json.loads(cache.read_text())
            if time.time() - data.get("fetched_at", 0) < CACHE_TTL_SEC:
                return data["tags"]
        except (json.JSONDecodeError, KeyError, OSError):
            pass

    tags = _fetch_tags_from_registry(resolved)
    try:
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps({"fetched_at": time.time(), "tags": tags}))
    except OSError:
        pass
    return tags


def version_pattern(version: str) -> re.Pattern[str]:
    return re.compile(rf"^{re.escape(version)}($|-)")


def filter_tags(tags: list[str], *, prefix: str | None = None) -> list[str]:
    matches = [tag for tag in tags if not tag.endswith("-source")]
    if prefix:
        pattern = version_pattern(prefix)
        matches = [tag for tag in matches if pattern.match(tag)]
    return matches


def tag_sort_key(tag: str) -> tuple[tuple[int, ...], int]:
    m = re.match(r"^(\d+\.\d+\.\d+)(?:-(\d+))?", tag)
    if m:
        parts = tuple(int(x) for x in m.group(1).split("."))
        return parts, int(m.group(2) or 0)
    m = re.match(r"^(\d+\.\d+)$", tag)
    if m:
        parts = tuple(int(x) for x in m.group(1).split(".")) + (0,)
        return parts, 0
    return (0, 0, 0), 0


def find_matching_tag(version: str, tags: list[str]) -> str | None:
    matches = filter_tags(tags, prefix=version)
    if not matches:
        return None
    return sorted(set(matches), key=tag_sort_key, reverse=True)[0]
