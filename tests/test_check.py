import json

import pytest

from conftest import load_script


def test_missing_base_url(monkeypatch, capsys):
    monkeypatch.delenv("EVALHUB_BASE_URL")
    mod = load_script("evalhub_check")
    with pytest.raises(SystemExit) as exc:
        mod.main()
    assert exc.value.code == 1
    out = json.loads(capsys.readouterr().out)
    assert out["ok"] is False
    assert "EVALHUB_BASE_URL" in out["error"]


def test_missing_token(monkeypatch, capsys):
    monkeypatch.delenv("EVALHUB_TOKEN")
    mod = load_script("evalhub_check")
    with pytest.raises(SystemExit) as exc:
        mod.main()
    assert exc.value.code == 1
    out = json.loads(capsys.readouterr().out)
    assert out["ok"] is False
    assert "EVALHUB_TOKEN" in out["error"]


def test_multiple_missing_vars(monkeypatch, capsys):
    monkeypatch.delenv("EVALHUB_BASE_URL")
    monkeypatch.delenv("EVALHUB_TOKEN")
    mod = load_script("evalhub_check")
    with pytest.raises(SystemExit) as exc:
        mod.main()
    assert exc.value.code == 1
    out = json.loads(capsys.readouterr().out)
    assert "EVALHUB_BASE_URL" in out["error"]
    assert "EVALHUB_TOKEN" in out["error"]


def test_healthy(evalhub_mock, mock_client, capsys):
    mock_client.health.return_value = {"status": "ok"}
    mod = load_script("evalhub_check")
    mod.main()
    out = json.loads(capsys.readouterr().out)
    assert out["ok"] is True
    assert out["base_url"] == "http://evalhub.test"
    assert out["tenant"] == "test-tenant"


def test_health_error(evalhub_mock, mock_client, capsys):
    mock_client.health.side_effect = Exception("connection refused")
    mod = load_script("evalhub_check")
    with pytest.raises(SystemExit) as exc:
        mod.main()
    assert exc.value.code == 1
