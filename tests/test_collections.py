import json
import sys
from unittest.mock import MagicMock

from conftest import load_script, make_collection


def test_list_all_collections(mock_client, monkeypatch, capsys):
    mock_client.collections.list.return_value = [
        make_collection("c1", "Safety Suite", evaluates=["safety"]),
        make_collection("c2", "Math Suite"),
    ]
    monkeypatch.setattr(sys, "argv", ["evalhub_collections"])
    mod = load_script("evalhub_collections")
    mod.main()
    out = json.loads(capsys.readouterr().out)
    assert len(out) == 2
    assert out[0]["id"] == "c1"
    assert out[0]["name"] == "Safety Suite"
    assert "safety" in out[0]["evaluates"]
    assert out[1]["id"] == "c2"


def test_filter_by_evaluates(mock_client, monkeypatch, capsys):
    mock_client.collections.list.return_value = [
        make_collection("c1", "Safety Suite", evaluates=["safety"]),
        make_collection("c2", "Math Suite", evaluates=["math"]),
    ]
    monkeypatch.setattr(sys, "argv", ["evalhub_collections", "--evaluates", "safety"])
    mod = load_script("evalhub_collections")
    mod.main()
    out = json.loads(capsys.readouterr().out)
    assert len(out) == 1
    assert out[0]["id"] == "c1"


def test_evaluates_filter_excludes_no_agent(mock_client, monkeypatch, capsys):
    mock_client.collections.list.return_value = [
        make_collection("c1", "Safety Suite", evaluates=["safety"]),
        make_collection("c2", "Plain Suite"),
    ]
    monkeypatch.setattr(sys, "argv", ["evalhub_collections", "--evaluates", "safety"])
    mod = load_script("evalhub_collections")
    mod.main()
    out = json.loads(capsys.readouterr().out)
    ids = [c["id"] for c in out]
    assert "c2" not in ids


def test_agent_flag_includes_full_metadata(mock_client, monkeypatch, capsys):
    mock_client.collections.list.return_value = [
        make_collection("c1", "Safety Suite", evaluates=["safety"]),
    ]
    monkeypatch.setattr(sys, "argv", ["evalhub_collections", "--agent"])
    mod = load_script("evalhub_collections")
    mod.main()
    out = json.loads(capsys.readouterr().out)
    assert "agent" in out[0]
    assert "safety" in out[0]["agent"]["evaluates"]


def test_single_collection_by_id(mock_client, monkeypatch, capsys):
    collection = MagicMock()
    collection.model_dump.return_value = {"id": "c1", "name": "Safety Suite", "benchmarks": []}
    mock_client.collections.get.return_value = collection
    monkeypatch.setattr(sys, "argv", ["evalhub_collections", "c1"])
    mod = load_script("evalhub_collections")
    mod.main()
    mock_client.collections.get.assert_called_once_with("c1")
    out = json.loads(capsys.readouterr().out)
    assert out["id"] == "c1"


def test_collection_without_agent_metadata(mock_client, monkeypatch, capsys):
    mock_client.collections.list.return_value = [
        make_collection("c1", "Plain Collection", description="Just a collection"),
    ]
    monkeypatch.setattr(sys, "argv", ["evalhub_collections"])
    mod = load_script("evalhub_collections")
    mod.main()
    out = json.loads(capsys.readouterr().out)
    assert out[0]["id"] == "c1"
    assert out[0]["description"] == "Just a collection"
    assert "agent" not in out[0]
    assert "evaluates" not in out[0]
