"""Mock child processes only: no external services or user processes are started."""

import subprocess
import threading
import time

import pytest

from scripts import serve


class FakeProcess:
    def __init__(self, exit_code=None, *, stubborn=False):
        self.exit_code = exit_code
        self.stubborn = stubborn
        self.terminated = 0
        self.killed = 0
        self.wait_timeouts = []

    def poll(self):
        return self.exit_code

    def terminate(self):
        self.terminated += 1
        if not self.stubborn:
            self.exit_code = -15

    def kill(self):
        self.killed += 1
        self.exit_code = -9

    def wait(self, timeout):
        self.wait_timeouts.append(timeout)
        if self.exit_code is None:
            raise subprocess.TimeoutExpired("synthetic-worker", timeout)
        return self.exit_code


def await_condition(predicate):
    deadline = time.monotonic() + 3
    while not predicate():
        if time.monotonic() >= deadline:
            pytest.fail("Supervisor did not reach expected state within three seconds")
        threading.Event().wait(0.01)


def test_confirmed_exit_restarts_only_owned_worker(monkeypatch, tmp_path, caplog):
    processes = []
    launches = []

    def popen(command, **options):
        launches.append((command, options))
        process = FakeProcess()
        processes.append(process)
        return process

    monkeypatch.setattr(serve.subprocess, "Popen", popen)
    supervisor = serve.WorkerSupervisor(tmp_path, restart_delay=0.01)
    try:
        supervisor.start()
        assert len(processes) == 1
        # A live process is retained; only an actual poll exit permits replacement.
        threading.Event().wait(0.15)
        assert len(processes) == 1
        processes[0].exit_code = 5
        await_condition(lambda: len(processes) == 2)
        assert supervisor.restart_count == 1
        assert processes[0].terminated == 0
        windows_venv = serve.sys.platform == "win32" and serve.sys.prefix != serve.sys.base_prefix
        executable = serve.sys._base_executable if windows_venv else serve.sys.executable
        assert launches[0][0] == [executable, str(tmp_path / "scripts/worker.py")]
        if windows_venv:
            assert launches[0][1]["env"]["__PYVENV_LAUNCHER__"] == serve.sys.executable
        else:
            assert launches[0][1]["env"] is None
        assert launches[0][1]["cwd"] == tmp_path
        assert launches[0][1]["creationflags"] == getattr(subprocess, "CREATE_NO_WINDOW", 0)
        assert "code 5" in caplog.text
    finally:
        supervisor.close()
    assert processes[1].terminated == 1
    assert processes[1].wait_timeouts == [5]
    assert not supervisor._thread.is_alive()
    supervisor.close()
    assert processes[1].terminated == 1


def test_close_interrupts_restart_delay_without_new_child(monkeypatch):
    process = FakeProcess(exit_code=7)
    calls = []

    def popen(*args, **kwargs):
        calls.append(1)
        return process

    monkeypatch.setattr(serve.subprocess, "Popen", popen)
    supervisor = serve.WorkerSupervisor(restart_delay=5)
    supervisor.start()
    threading.Event().wait(0.15)
    started = time.monotonic()
    supervisor.close()
    assert time.monotonic() - started < 1
    assert len(calls) == 1
    assert supervisor.restart_count == 0
    with pytest.raises(RuntimeError, match="only be started once"):
        supervisor.start()


def test_repeated_crashes_exhaust_three_restart_budget(monkeypatch, caplog):
    processes = []

    def popen(*args, **kwargs):
        process = FakeProcess(exit_code=2)
        processes.append(process)
        return process

    monkeypatch.setattr(serve.subprocess, "Popen", popen)
    supervisor = serve.WorkerSupervisor(restart_delay=0.01, max_restarts=3, restart_window=60)
    try:
        supervisor.start()
        await_condition(lambda: supervisor.failure is not None)
        supervisor._thread.join(timeout=1)
        assert len(processes) == 4  # Initial launch plus three permitted restarts.
        assert supervisor.restart_count == 3
        assert "automatic restart stopped" in supervisor.failure
        assert "crash limit reached" in caplog.text
        assert not supervisor._thread.is_alive()
    finally:
        supervisor.close()


def test_stubborn_owned_worker_gets_bounded_kill_wait(monkeypatch):
    process = FakeProcess(stubborn=True)
    monkeypatch.setattr(serve.subprocess, "Popen", lambda *args, **kwargs: process)
    supervisor = serve.WorkerSupervisor()
    supervisor.start()
    supervisor.close()
    assert process.terminated == 1
    assert process.killed == 1
    assert process.wait_timeouts == [5, 3]


def test_launch_failure_is_explicit_and_not_retried(monkeypatch, caplog):
    def unavailable(*args, **kwargs):
        raise OSError("synthetic launch refusal")

    monkeypatch.setattr(serve.subprocess, "Popen", unavailable)
    supervisor = serve.WorkerSupervisor()
    with pytest.raises(RuntimeError, match="Could not start prediction worker"):
        supervisor.start()
    supervisor.close()
    assert "synthetic launch refusal" in caplog.text
    assert supervisor.restart_count == 0


def test_no_worker_option_never_creates_supervisor(monkeypatch):
    monkeypatch.setattr(serve.sys, "argv", ["serve.py", "--no-worker"])
    monkeypatch.setattr(
        serve, "WorkerSupervisor", lambda: pytest.fail("no-worker must not own a child")
    )
    runs = []
    monkeypatch.setattr(serve.uvicorn, "run", lambda *args, **kwargs: runs.append(kwargs))
    serve.main()
    assert runs == [{"host": "127.0.0.1", "port": 8765}]
