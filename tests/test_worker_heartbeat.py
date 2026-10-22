"""Synthetic filesystem faults exercise a real Windows sharing violation when available."""

import json
import os
import threading
import time

import pytest

from backend.app import jobs, worker


def test_atomic_json_retries_transient_reader_and_removes_its_own_temp(tmp_path, monkeypatch):
    path = tmp_path / "status.json"
    actual = os.replace
    calls = []

    def initially_locked(source, destination):
        calls.append(destination)
        if len(calls) <= 2:
            raise PermissionError("SYNTHETIC temporary target reader")
        actual(source, destination)

    monkeypatch.setattr(jobs.os, "replace", initially_locked)
    jobs.atomic_json(path, {"state": "ready"})
    assert json.loads(path.read_text()) == {"state": "ready"}
    assert len(calls) == 3 and list(tmp_path.glob("*.tmp")) == []


@pytest.mark.skipif(os.name != "nt", reason="Windows FILE_SHARE_DELETE semantics")
def test_real_windows_read_handle_can_close_during_atomic_retry(tmp_path):
    path = tmp_path / "status.json"
    jobs.atomic_json(path, {"state": "before"})
    reader = path.open("r", encoding="utf-8")
    released = threading.Event()

    def release_reader():
        time.sleep(0.04)
        reader.close()
        released.set()

    thread = threading.Thread(target=release_reader)
    thread.start()
    jobs.atomic_json(path, {"state": "after"})
    thread.join(timeout=1)
    assert released.is_set() and json.loads(path.read_text())["state"] == "after"


def test_heartbeat_write_failure_does_not_kill_queue_executor(tmp_path, monkeypatch, caplog):
    def unavailable(*_):
        raise PermissionError("SYNTHETIC persistent status reader")

    monkeypatch.setattr(worker, "atomic_json", unavailable)
    monkeypatch.setattr(worker, "deterministic_cpu", lambda: True)
    worker.run_worker(tmp_path / "cache", tmp_path / "app", once=True)
    assert "continuing durable queue" in caplog.text
