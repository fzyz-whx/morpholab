"""Serve the local workbench and supervise its separate durable-queue worker."""

import argparse
import subprocess
import sys
from pathlib import Path

import uvicorn

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-worker", action="store_true", help="Run worker separately")
    args = parser.parse_args()
    worker = None
    if not args.no_worker:
        worker = subprocess.Popen(
            [sys.executable, str(ROOT / "scripts/worker.py")],
            cwd=ROOT,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    try:
        uvicorn.run("backend.app.main:app", host="127.0.0.1", port=args.port)
    finally:
        if worker is not None and worker.poll() is None:
            worker.terminate()
            try:
                worker.wait(timeout=10)
            except subprocess.TimeoutExpired:
                worker.kill()
                worker.wait()


if __name__ == "__main__":
    main()
