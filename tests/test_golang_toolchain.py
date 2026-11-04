import importlib.util
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = (
    Path(__file__).resolve().parent.parent
    / "dev-skills"
    / "golang-toolchain-update"
    / "scripts"
)


def load_registry_utils():
    """Load dev-skills registry_utils.py without polluting the module namespace."""
    if str(SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_DIR))
    spec = importlib.util.spec_from_file_location(
        "golang_toolchain_registry_utils", SCRIPTS_DIR / "registry_utils.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def registry(monkeypatch):
    monkeypatch.delenv("GO_TOOLSET_IMAGE", raising=False)
    monkeypatch.delenv("GOLANG_TOOLCHAIN_UPDATE_NO_CACHE", raising=False)
    monkeypatch.delenv("GOLANG_CVE_UPDATE_NO_CACHE", raising=False)
    return load_registry_utils()


def test_normalize_image_accepts_short_and_full_reference(registry):
    assert registry.normalize_image("ubi9/go-toolset") == "ubi9/go-toolset"
    assert (
        registry.normalize_image("registry.access.redhat.com/ubi10/go-toolset")
        == "ubi10/go-toolset"
    )


def test_normalize_image_rejects_unknown_image(registry):
    with pytest.raises(ValueError):
        registry.normalize_image("ubi9/other-image")


def test_detect_image_from_containerfile(registry, tmp_path):
    (tmp_path / "Containerfile").write_text(
        "FROM registry.access.redhat.com/ubi9/go-toolset:1.26 AS builder\n"
    )
    assert registry.detect_image(tmp_path) == "ubi9/go-toolset"


def test_detect_image_from_dockerfile_variant(registry, tmp_path):
    (tmp_path / "Dockerfile.test").write_text(
        "FROM registry.access.redhat.com/ubi10/go-toolset:1.26.10\n"
    )
    assert registry.detect_image(tmp_path) == "ubi10/go-toolset"


def test_detect_image_returns_none_without_reference(registry, tmp_path):
    (tmp_path / "Containerfile").write_text("FROM scratch\n")
    assert registry.detect_image(tmp_path) is None


def test_resolve_image_precedence(registry, monkeypatch, tmp_path):
    (tmp_path / "Containerfile").write_text(
        "FROM registry.access.redhat.com/ubi9/go-toolset:1.26 AS builder\n"
    )

    assert registry.resolve_image("ubi8/go-toolset", tmp_path) == "ubi8/go-toolset"

    monkeypatch.setenv("GO_TOOLSET_IMAGE", "ubi10/go-toolset")
    assert registry.resolve_image(None, tmp_path) == "ubi10/go-toolset"

    monkeypatch.delenv("GO_TOOLSET_IMAGE")
    assert registry.resolve_image(None, tmp_path) == "ubi9/go-toolset"

    empty_root = tmp_path / "empty"
    empty_root.mkdir()
    assert registry.resolve_image(None, empty_root) == registry.DEFAULT_IMAGE


def test_resolve_image_reports_source(registry, monkeypatch, tmp_path):
    assert registry.resolve_image_with_source(None, tmp_path) == (
        registry.DEFAULT_IMAGE,
        "default",
    )
    assert registry.resolve_image_with_source("ubi9/go-toolset", tmp_path)[1] == "argument"
    monkeypatch.setenv("GO_TOOLSET_IMAGE", "ubi9/go-toolset")
    assert registry.resolve_image_with_source(None, tmp_path)[1] == "GO_TOOLSET_IMAGE"


def test_filter_tags_drops_source_tags(registry):
    tags = ["1.26.4", "1.26.4-source", "1.26.4-1782717933", "1.25.0"]
    assert registry.filter_tags(tags, prefix="1.26.4") == ["1.26.4", "1.26.4-1782717933"]


def test_find_matching_tag_prefers_newest_build(registry):
    tags = ["1.26.4", "1.26.4-1782717933", "1.26.4-1700000000", "1.26.5"]
    assert registry.find_matching_tag("1.26.4", tags) == "1.26.4-1782717933"


def test_find_matching_tag_returns_none(registry):
    assert registry.find_matching_tag("1.27.0", ["1.26.4"]) is None


def test_tag_sort_key_orders_patches_and_builds(registry):
    tags = ["1.25.0", "1.26.4", "1.26.10", "1.26.4-200", "1.26.4-100"]
    assert sorted(tags, key=registry.tag_sort_key) == [
        "1.25.0",
        "1.26.4",
        "1.26.4-100",
        "1.26.4-200",
        "1.26.10",
    ]


def test_no_cache_honours_current_and_legacy_flags(registry, monkeypatch):
    assert registry._no_cache() is False
    monkeypatch.setenv("GOLANG_CVE_UPDATE_NO_CACHE", "1")
    assert registry._no_cache() is True
    monkeypatch.delenv("GOLANG_CVE_UPDATE_NO_CACHE")
    monkeypatch.setenv("GOLANG_TOOLCHAIN_UPDATE_NO_CACHE", "1")
    assert registry._no_cache() is True
