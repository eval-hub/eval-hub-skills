import json
import sys
from unittest.mock import MagicMock

from conftest import load_script, make_provider


def test_list_all_providers(mock_client, monkeypatch, capsys):
    mock_client.providers.list.return_value = [
        make_provider("p1", "Provider One", target_type="model", evaluates=["safety"]),
        make_provider("p2", "Provider Two"),
    ]
    monkeypatch.setattr(sys, "argv", ["evalhub_providers"])
    mod = load_script("evalhub_providers")
    mod.main()
    out = json.loads(capsys.readouterr().out)
    assert len(out) == 2
    assert out[0]["id"] == "p1"
    assert out[0]["name"] == "Provider One"
    assert out[0]["target_type"] == "model"
    assert "safety" in out[0]["evaluates"]
    assert out[1]["id"] == "p2"


def test_filter_by_target_type(mock_client, monkeypatch, capsys):
    mock_client.providers.list.return_value = [
        make_provider("p1", "Model Provider", target_type="model", evaluates=["reasoning"]),
        make_provider("p2", "Agent Provider", target_type="agent", evaluates=["safety"]),
    ]
    monkeypatch.setattr(sys, "argv", ["evalhub_providers", "--target-type", "model"])
    mod = load_script("evalhub_providers")
    mod.main()
    out = json.loads(capsys.readouterr().out)
    assert len(out) == 1
    assert out[0]["id"] == "p1"


def test_filter_by_evaluates(mock_client, monkeypatch, capsys):
    mock_client.providers.list.return_value = [
        make_provider("p1", "Safety Provider", target_type="model", evaluates=["safety", "reasoning"]),
        make_provider("p2", "Math Provider", target_type="model", evaluates=["math"]),
    ]
    monkeypatch.setattr(sys, "argv", ["evalhub_providers", "--evaluates", "safety"])
    mod = load_script("evalhub_providers")
    mod.main()
    out = json.loads(capsys.readouterr().out)
    assert len(out) == 1
    assert out[0]["id"] == "p1"


def test_agent_flag_includes_full_metadata(mock_client, monkeypatch, capsys):
    mock_client.providers.list.return_value = [
        make_provider("p1", "Provider One", target_type="model", evaluates=["safety"]),
    ]
    monkeypatch.setattr(sys, "argv", ["evalhub_providers", "--agent"])
    mod = load_script("evalhub_providers")
    mod.main()
    out = json.loads(capsys.readouterr().out)
    assert "agent" in out[0]
    assert out[0]["agent"]["target_type"] == "model"
    assert "safety" in out[0]["agent"]["evaluates"]


def test_benchmarks_flag(mock_client, monkeypatch, capsys):
    bench = MagicMock()
    bench.model_dump.return_value = {"id": "b1", "name": "Bench One", "category": "math"}
    mock_client.benchmarks.list.return_value = [bench]
    monkeypatch.setattr(sys, "argv", ["evalhub_providers", "--benchmarks"])
    mod = load_script("evalhub_providers")
    mod.main()
    out = json.loads(capsys.readouterr().out)
    assert out[0]["id"] == "b1"
    mock_client.benchmarks.list.assert_called_once_with(provider_id=None, category=None)


def test_single_provider_by_id(mock_client, monkeypatch, capsys):
    provider = MagicMock()
    provider.model_dump.return_value = {"id": "p1", "name": "Provider One"}
    mock_client.providers.get.return_value = provider
    monkeypatch.setattr(sys, "argv", ["evalhub_providers", "p1"])
    mod = load_script("evalhub_providers")
    mod.main()
    mock_client.providers.get.assert_called_once_with("p1")
    out = json.loads(capsys.readouterr().out)
    assert out["id"] == "p1"


def test_provider_without_agent_metadata(mock_client, monkeypatch, capsys):
    mock_client.providers.list.return_value = [
        make_provider("p1", "Basic Provider", description="A plain provider"),
    ]
    monkeypatch.setattr(sys, "argv", ["evalhub_providers"])
    mod = load_script("evalhub_providers")
    mod.main()
    out = json.loads(capsys.readouterr().out)
    assert out[0]["id"] == "p1"
    assert out[0]["description"] == "A plain provider"
    assert "agent" not in out[0]
    assert "target_type" not in out[0]


def test_target_type_filter_excludes_no_agent(mock_client, monkeypatch, capsys):
    mock_client.providers.list.return_value = [
        make_provider("p1", "Model Provider", target_type="model", evaluates=["safety"]),
        make_provider("p2", "No Agent Provider"),
    ]
    monkeypatch.setattr(sys, "argv", ["evalhub_providers", "--target-type", "model"])
    mod = load_script("evalhub_providers")
    mod.main()
    out = json.loads(capsys.readouterr().out)
    ids = [p["id"] for p in out]
    assert "p2" not in ids
