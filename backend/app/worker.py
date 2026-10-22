"""Independent worker lifecycle; no computation executes in an API route."""

from __future__ import annotations

import logging
import os
import time
import uuid
from pathlib import Path

from backend.app.assets import image_assets
from backend.app.data import DataError
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
        result = image_assets(result, queue.directory / "results", identifier)
        atomic_json(
            path, {**result, "job_id": identifier, "schema_version": "1", "created_at_utc": now()}
        )
        queue.finish(identifier, "succeeded")
    except InterruptedError:
        queue.finish(identifier, "cancelled")
    except Exception as exc:
        trace_id = str(uuid.uuid4())
        logging.exception("Prediction job %s failed; trace_id=%s", identifier, trace_id)
        known = {
            "Checkpoint SHA256 mismatch": "CHECKPOINT_HASH_MISMATCH",
            "Source manifest changed after submission": "SOURCE_CHANGED",
            "Prepared sequence changed after submission": "SOURCE_CHANGED",
            "Invalid observation QC": "INVALID_CONTEXT",
            "Invalid prediction output": "INVALID_FORECAST",
            "Worker implementation differs from the submitted job": "IMPLEMENTATION_MISMATCH",
        }
        safe_message = str(exc) if str(exc) in known else None
        # Never publish local filesystem paths, pickle messages, or arbitrary exception text.
        queue.finish(
            identifier,
            "failed",
            {
                "code": exc.code
                if isinstance(exc, DataError)
                else known.get(str(exc), "PREDICTION_FAILED"),
                "type": type(exc).__name__,
                "message": exc.message
                if isinstance(exc, DataError)
                else safe_message or "Prediction failed validation or computation.",
                "details": {},
                "trace_id": trace_id,
            },
        )
    return True


def run_worker(artifacts: Path, app_root: Path, *, once: bool = False) -> None:
    queue = JobQueue(app_root)
    with WorkerLock(app_root):
        deterministic_cpu()
        queue.recover()
        service = PredictionService(artifacts)
        heartbeat_warning_at = 0.0
        while True:
            try:
                atomic_json(
                    app_root / "worker-status.json",
                    {
                        "status": "ready",
                        "heartbeat_utc": now(),
                        "pid": os.getpid(),
                    },
                )
            except OSError:
                # A display/status-file race must not terminate the queue executor.
                if time.monotonic() - heartbeat_warning_at >= 5:
                    logging.warning(
                        "Worker heartbeat could not be written; continuing durable queue"
                    )
                    heartbeat_warning_at = time.monotonic()
            worked = execute_one(queue, service)
            if once:
                return
            if not worked:
                time.sleep(0.25)
