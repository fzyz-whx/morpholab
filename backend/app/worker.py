"""Independent worker lifecycle; no computation executes in an API route."""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path

from backend.app.jobs import JobQueue, WorkerLock, atomic_json, now
from backend.app.prediction import PredictionRequest, PredictionService


def deterministic_cpu() -> bool:
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    os.environ.setdefault("MKL_NUM_THREADS", "1")
    try:
        import torch
    except ImportError:
        return False  # Classical baselines remain usable without the optional Torch extra.

    torch.set_num_threads(1)
    try:
        torch.set_num_interop_threads(1)
    except RuntimeError:
        pass  # The embedding test process may already have initialized its interop pool.
    torch.use_deterministic_algorithms(True)
    torch.backends.mkldnn.enabled = False  # Explicit IEEE fp32 convolution path.
    torch.backends.cuda.matmul.fp32_precision = "ieee"
    torch.backends.cudnn.conv.fp32_precision = "ieee"
    torch.manual_seed(0)
    return True


def execute_one(queue: JobQueue, service: PredictionService) -> bool:
    job = queue.claim()
    if job is None:
        return False
    identifier = job["id"]
    try:
        result = service.compute(
            PredictionRequest.model_validate(job["request"]),
            job["pinned"],
            lambda: queue.get(identifier)["cancel_requested"],
        )
        if queue.get(identifier)["cancel_requested"]:
            raise InterruptedError("Cancelled")
        path = queue.result_path(identifier)
        path.parent.mkdir(parents=True, exist_ok=True)
        atomic_json(
            path, {**result, "job_id": identifier, "schema_version": "1", "created_at_utc": now()}
        )
        queue.finish(identifier, "succeeded")
    except InterruptedError:
        queue.finish(identifier, "cancelled")
    except Exception as exc:
        logging.exception("Prediction job %s failed", identifier)
        # Never publish local filesystem paths, pickle messages, or arbitrary exception text.
        queue.finish(
            identifier,
            "failed",
            {
                "code": "PREDICTION_FAILED",
                "type": type(exc).__name__,
                "message": "Prediction failed validation or computation.",
            },
        )
    return True


def run_worker(artifacts: Path, app_root: Path, *, once: bool = False) -> None:
    queue = JobQueue(app_root)
    with WorkerLock(app_root):
        deterministic_cpu()
        queue.recover()
        service = PredictionService(artifacts)
        while True:
            atomic_json(
                app_root / "worker-status.json", {"status": "ready", "heartbeat_utc": now()}
            )
            worked = execute_one(queue, service)
            if once:
                return
            if not worked:
                time.sleep(0.25)
