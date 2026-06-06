import json
import sys

import pytest

from conftest import load_script, make_job


def test_list_jobs(mock_client, monkeypatch, capsys):
    mock_client.jobs.list.return_value = [
        make_job("j1", "Job One", "running"),
        make_job("j2", "Job Two", "completed"),
    ]
    monkeypatch.setattr(sys, "argv", ["evalhub_status", "--list"])
    mod = load_script("evalhub_status")
    mod.main()
    out = json.loads(capsys.readouterr().out)
    assert len(out) == 2
    assert out[0]["id"] == "j1"
    assert out[0]["state"] == "running"
    assert out[1]["state"] == "completed"


def test_list_with_status_filter(evalhub_mock, mock_client, monkeypatch, capsys):
    mock_client.jobs.list.return_value = [make_job("j1", "Job One", "running")]
    monkeypatch.setattr(sys, "argv", ["evalhub_status", "--list", "--status", "running"])
    mod = load_script("evalhub_status")
    mod.main()
    evalhub_mock.JobStatus.assert_called_with("running")
    out = json.loads(capsys.readouterr().out)
    assert len(out) == 1
    assert out[0]["id"] == "j1"


def test_get_job_by_id(mock_client, monkeypatch, capsys):
    job = make_job("j1", "Job One", "completed")
    job.model_dump.return_value = {"id": "j1", "name": "Job One", "state": "completed"}
    mock_client.jobs.get.return_value = job
    monkeypatch.setattr(sys, "argv", ["evalhub_status", "j1"])
    mod = load_script("evalhub_status")
    mod.main()
    mock_client.jobs.get.assert_called_once_with("j1")
    out = json.loads(capsys.readouterr().out)
    assert out["id"] == "j1"
    assert out["state"] == "completed"


def test_cancel_job(mock_client, monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["evalhub_status", "j1", "--cancel"])
    mod = load_script("evalhub_status")
    mod.main()
    mock_client.jobs.cancel.assert_called_once_with("j1")
    out = json.loads(capsys.readouterr().out)
    assert out["cancelled"] is True
    assert out["job_id"] == "j1"


def test_cancel_error_exits(mock_client, monkeypatch):
    mock_client.jobs.cancel.side_effect = Exception("not found")
    monkeypatch.setattr(sys, "argv", ["evalhub_status", "j1", "--cancel"])
    mod = load_script("evalhub_status")
    with pytest.raises(SystemExit) as exc:
        mod.main()
    assert exc.value.code == 1


def test_wait_for_completion(mock_client, monkeypatch, capsys):
    job = make_job("j1", "Job One", "completed")
    job.model_dump.return_value = {"id": "j1", "state": "completed"}
    mock_client.jobs.wait_for_completion.return_value = job
    monkeypatch.setattr(sys, "argv", ["evalhub_status", "j1", "--wait"])
    mod = load_script("evalhub_status")
    mod.main()
    mock_client.jobs.wait_for_completion.assert_called_once_with("j1", timeout=600.0, poll_interval=10.0)
    out = json.loads(capsys.readouterr().out)
    assert out["state"] == "completed"


def test_wait_timeout_exits(mock_client, monkeypatch):
    mock_client.jobs.wait_for_completion.side_effect = TimeoutError
    monkeypatch.setattr(sys, "argv", ["evalhub_status", "j1", "--wait"])
    mod = load_script("evalhub_status")
    with pytest.raises(SystemExit) as exc:
        mod.main()
    assert exc.value.code == 1


def test_no_job_id_exits(mock_client, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["evalhub_status"])
    mod = load_script("evalhub_status")
    with pytest.raises(SystemExit) as exc:
        mod.main()
    assert exc.value.code == 2
