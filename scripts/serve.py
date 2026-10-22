"""Serve the local workbench and supervise its separate durable-queue worker."""

import argparse
import logging
import os
import subprocess
import sys
import threading
import time
from collections import deque
from pathlib import Path

import uvicorn

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
LOGGER = logging.getLogger(__name__)


class WorkerSupervisor:
    """Own one child and restart confirmed exits within a finite crash budget."""

    def __init__(
        self,
        root: Path = ROOT,
        *,
        restart_delay: float = 1,
        max_restarts: int = 3,
        restart_window: float = 60,
    ) -> None:
        if restart_delay < 0 or max_restarts < 0 or restart_window <= 0:
            raise ValueError("Invalid worker restart policy")
        self.root = root
        self.restart_delay = restart_delay
        self.max_restarts = max_restarts
        self.restart_window = restart_window
        self.restart_count = 0
        self.failure: str | None = None
        self.worker: subprocess.Popen | None = None
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._restarts: deque[float] = deque()

    def _spawn(self) -> None:
        executable = sys.executable
        environment = None
        if sys.platform == "win32" and sys.prefix != sys.base_prefix:
            # Match CPython multiprocessing: own the interpreter, not its venv redirector.
            executable = sys._base_executable
            environment = os.environ.copy()
            environment["__PYVENV_LAUNCHER__"] = sys.executable
        try:
            self.worker = subprocess.Popen(
                [executable, str(self.root / "scripts/worker.py")],
                cwd=self.root,
                env=environment,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except OSError as error:
            self.failure = f"Could not start prediction worker: {error}"
            LOGGER.error(self.failure)
            raise RuntimeError(self.failure) from error

    def start(self) -> None:
        if self._thread is not None or self._stop.is_set():
            raise RuntimeError("Worker supervisor can only be started once")
        self._spawn()
        self._thread = threading.Thread(
            target=self._monitor, name="morpholab-worker-supervisor", daemon=True
        )
        try:
            self._thread.start()
        except RuntimeError:
            self._stop.set()
            self._shutdown_worker()
            self._thread = None
            raise

    def _monitor(self) -> None:
        try:
            while not self._stop.wait(0.1):
                assert self.worker is not None
                exit_code = self.worker.poll()
                if exit_code is None:
                    continue
                # poll() has reaped this owned child; never infer death from a heartbeat.
                LOGGER.error(
                    "Prediction worker exited with code %s (restarts so far: %s)",
                    exit_code,
                    self.restart_count,
                )
                now = time.monotonic()
                while self._restarts and now - self._restarts[0] >= self.restart_window:
                    self._restarts.popleft()
                if len(self._restarts) >= self.max_restarts:
                    self.failure = (
                        f"Prediction worker crash limit reached: {self.max_restarts} restarts "
                        f"in {self.restart_window:g}s; automatic restart stopped"
                    )
                    LOGGER.critical(self.failure)
                    return
                if self._stop.wait(self.restart_delay):
                    return
                self._restarts.append(time.monotonic())
                self.restart_count += 1
                LOGGER.warning("Restarting prediction worker (attempt %s)", self.restart_count)
                try:
                    self._spawn()
                except RuntimeError:
                    # A failed process launch is an explicit failure, not an infinite retry loop.
                    return
        finally:
            self._shutdown_worker()

    def _shutdown_worker(self) -> None:
        worker = self.worker
        if worker is None or worker.poll() is not None:
            return
        try:
            worker.terminate()
            try:
                worker.wait(timeout=5)
            except subprocess.TimeoutExpired:
                worker.kill()
                worker.wait(timeout=3)
        except (OSError, subprocess.TimeoutExpired):
            LOGGER.exception("Owned prediction worker did not exit cleanly during shutdown")

    def close(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=10)
            if self._thread.is_alive():
                LOGGER.error("Worker supervisor shutdown exceeded 10 seconds")
        else:
            self._shutdown_worker()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-worker", action="store_true", help="Run worker separately")
    args = parser.parse_args()
    supervisor = None if args.no_worker else WorkerSupervisor()
    try:
        if supervisor is not None:
            supervisor.start()
        uvicorn.run("backend.app.main:app", host="127.0.0.1", port=args.port)
    finally:
        if supervisor is not None:
            supervisor.close()


if __name__ == "__main__":
    main()
