import json
import sys
from unittest.mock import MagicMock

import pytest

from conftest import load_script


def _make_job_mock(id="j1", name="eval-my-model", state="pending"):
    job = MagicMock()
    job.model_dump.return_value = {"id": id, "name": name, "state": state}
    return job


def test_submit_with_benchmark(mock_client, monkeypatch, capsys):
    mock_client.jobs.submit.return_value = _make_job_mock()
    monkeypatch.setattr(sys, "argv", [
        "evalhub_eval",
        "--model-url", "http://model:8000/v1",
        "--model-name", "my-model",
        "--provider", "p1",
        "--benchmark", "b1",
    ])
    mod = load_script("evalhub_eval")
    mod.main()
    mock_client.jobs.submit.assert_called_once()
    out = json.loads(capsys.readouterr().out)
    assert out["id"] == "j1"


def test_submit_with_collection(mock_client, monkeypatch, capsys):
    mock_client.jobs.submit.return_value = _make_job_mock()
    monkeypatch.setattr(sys, "argv", [
        "evalhub_eval",
        "--model-url", "http://model:8000/v1",
        "--model-name", "my-model",
        "--collection", "c1",
    ])
    mod = load_script("evalhub_eval")
    mod.main()
    mock_client.jobs.submit.assert_called_once()
    out = json.loads(capsys.readouterr().out)
    assert out["id"] == "j1"


def test_missing_model_url_exits(mock_client, monkeypatch):
    monkeypatch.setattr(sys, "argv", [
        "evalhub_eval",
        "--model-name", "my-model",
        "--provider", "p1",
        "--benchmark", "b1",
    ])
    mod = load_script("evalhub_eval")
    with pytest.raises(SystemExit) as exc:
        mod.main()
    assert exc.value.code == 2


def test_missing_benchmark_and_collection_exits(mock_client, monkeypatch):
    monkeypatch.setattr(sys, "argv", [
        "evalhub_eval",
        "--model-url", "http://model:8000/v1",
        "--model-name", "my-model",
    ])
    mod = load_script("evalhub_eval")
    with pytest.raises(SystemExit) as exc:
        mod.main()
    assert exc.value.code == 2


def test_benchmark_requires_provider(mock_client, monkeypatch):
    monkeypatch.setattr(sys, "argv", [
        "evalhub_eval",
        "--model-url", "http://model:8000/v1",
        "--model-name", "my-model",
        "--benchmark", "b1",
    ])
    mod = load_script("evalhub_eval")
    with pytest.raises(SystemExit) as exc:
        mod.main()
    assert exc.value.code == 2


def test_json_file_submission(mock_client, monkeypatch, capsys, tmp_path):
    job_request = {"name": "my-eval", "model": {"url": "http://model:8000", "name": "test"}}
    req_file = tmp_path / "job.json"
    req_file.write_text(json.dumps(job_request))
    mock_client.jobs.submit.return_value = _make_job_mock(name="my-eval")
    monkeypatch.setattr(sys, "argv", ["evalhub_eval", "--json", str(req_file)])
    mod = load_script("evalhub_eval")
    mod.main()
    mock_client.jobs.submit.assert_called_once()
    out = json.loads(capsys.readouterr().out)
    assert out["id"] == "j1"


def test_auto_generates_job_name(evalhub_mock, mock_client, monkeypatch):
    mock_client.jobs.submit.return_value = _make_job_mock(name="eval-mymodel")
    monkeypatch.setattr(sys, "argv", [
        "evalhub_eval",
        "--model-url", "http://model:8000/v1",
        "--model-name", "mymodel",
        "--collection", "c1",
    ])
    mod = load_script("evalhub_eval")
    mod.main()
    # JobSubmissionRequest is a MagicMock; check kwargs passed to its constructor
    assert evalhub_mock.JobSubmissionRequest.call_args.kwargs["name"] == "eval-mymodel"
