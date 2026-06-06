import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

SCRIPTS_DIR = Path(__file__).parent.parent / "evalhub" / "scripts"


def load_script(name: str):
    """Load a script module fresh from evalhub/scripts/ without caching."""
    path = SCRIPTS_DIR / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None, f"Could not load script: {path}"
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def evalhub_mock():
    """Patch sys.modules with a fake evalhub SDK and yield the mock module."""
    mock_module = MagicMock()
    mock_models = MagicMock()
    with patch.dict(sys.modules, {
        "evalhub": mock_module,
        "evalhub.models": mock_models,
        "evalhub.models.api": mock_models,
    }):
        yield mock_module


@pytest.fixture
def mock_client(evalhub_mock):
    """Return the mock client instance that SyncEvalHubClient() will return."""
    return evalhub_mock.SyncEvalHubClient.return_value


@pytest.fixture(autouse=True)
def evalhub_env(monkeypatch):
    """Set required EvalHub environment variables for all tests."""
    monkeypatch.setenv("EVALHUB_BASE_URL", "http://evalhub.test")
    monkeypatch.setenv("EVALHUB_TOKEN", "test-token")
    monkeypatch.setenv("EVALHUB_TENANT", "test-tenant")


def make_provider(id, name, target_type=None, evaluates=None, description=None):
    """Build a mock provider object with optional agent metadata."""
    p = MagicMock()
    p.resource.id = id
    p.name = name
    p.description = description
    if target_type or evaluates:
        agent = MagicMock()
        agent.model_dump.return_value = {
            "target_type": target_type,
            "evaluates": evaluates or [],
            "summary": f"Summary for {name}",
            "recommended_when": "when needed",
            "hints": "some hints",
            "result_interpretation": "higher is better",
            "complements": [],
        }
        p.agent = agent
    else:
        p.agent = None
    return p


def make_collection(id, name, evaluates=None, description=None):
    """Build a mock collection object with optional agent metadata."""
    c = MagicMock()
    c.resource.id = id
    c.name = name
    c.description = description
    c.category = "general"
    if evaluates:
        agent = MagicMock()
        agent.model_dump.return_value = {
            "evaluates": evaluates,
            "summary": f"Collection: {name}",
            "recommended_when": "",
            "hints": "",
            "result_interpretation": "",
            "complements": [],
        }
        c.agent = agent
    else:
        c.agent = None
    return c


def make_job(id, name, state):
    """Build a mock job object."""
    j = MagicMock()
    j.resource.id = id
    j.name = name
    j.state.value = state
    j.resource.created_at = "2026-01-01T00:00:00Z"
    j.model_dump.return_value = {"id": id, "name": name, "state": state}
    return j
