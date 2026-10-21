"""Local workbench HTTP adapter with a durable queue and separate inference worker."""

from __future__ import annotations

import json
import os
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from starlette.exceptions import HTTPException
from starlette.staticfiles import StaticFiles

from backend.app.data import PRIMARY_DATASET, RECOVERY, DataError, DataStore
from backend.app.jobs import JobQueue, worker_ready
from backend.app.prediction import PredictionRequest, PredictionService

ROOT = Path(__file__).resolve().parents[2]


class WorkbenchFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        normalized = path.replace("\\", "/").lstrip("/")
        try:
            return await super().get_response(path, scope)
        except HTTPException as error:
            if error.status_code == 404 and not normalized.startswith("api/") and "." not in path:
                return await super().get_response("index.html", scope)
            raise


def envelope(
    payload: dict[str, Any], *, dataset_id: str | None = None, provenance: str | None = None
) -> dict[str, Any]:
    """Apply the common response contract without inventing model/run provenance."""
    return {
        **payload,
        "schema_version": "1",
        "provenance": provenance if provenance is not None else payload.get("provenance"),
        "dataset_id": dataset_id if dataset_id is not None else payload.get("dataset_id"),
        "model_id": payload.get("model_id"),
        "run_id": payload.get("run_id"),
        "created_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }


def create_app(
    root: Path = ROOT, *, artifacts_root: Path | None = None, app_root: Path | None = None
) -> FastAPI:
    app = FastAPI(title="MorphoLab local workbench API", version="0.1.0")
    artifacts_root = artifacts_root or Path(
        os.environ.get("MORPHOLAB_ARTIFACTS_ROOT", root / "artifacts")
    )
    app_root = app_root or root / "artifacts/app"
    store = DataStore(root, artifacts_root)
    prediction = PredictionService(artifacts_root)
    queue = JobQueue(app_root)
    app.state.store = store
    app.state.prediction = prediction
    app.state.queue = queue

    def error_response(code: str, message: str, status: int, details: object) -> JSONResponse:
        return JSONResponse(
            envelope(
                {
                    "error": {
                        "code": code,
                        "message": message,
                        "details": details,
                        "trace_id": str(uuid.uuid4()),
                    },
                }
            ),
            status_code=status,
        )

    @app.exception_handler(DataError)
    async def data_error(_: Request, error: DataError) -> JSONResponse:
        details = {"recovery_commands": RECOVERY} if error.status == 503 else {}
        return error_response(error.code, error.message, error.status, details)

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, __: RequestValidationError) -> JSONResponse:
        return error_response("INVALID_REQUEST", "Request parameters are invalid.", 422, {})

    @app.exception_handler(HTTPException)
    async def http_error(_: Request, error: HTTPException) -> JSONResponse:
        return error_response(
            "HTTP_ERROR", "Requested route or method is unavailable.", error.status_code, {}
        )

    @app.exception_handler(Exception)
    async def internal_error(_: Request, __: Exception) -> JSONResponse:
        return error_response(
            "INTERNAL_ERROR", "Local service could not complete this request.", 500, {}
        )

    @app.get("/api/v1/health")
    def health() -> dict[str, object]:
        available, issue = store.available()
        return envelope(
            {
                "status": "ok" if available else "degraded",
                "data_available": available,
                "data_issue": issue,
                "model_status": "trained"
                if any(m["trained"] for m in prediction.registry())
                else "untrained",
                "read_only": False,
                "worker_ready": worker_ready(app_root),
            }
        )

    @app.get("/api/v1/datasets")
    def datasets() -> dict[str, object]:
        items = store.datasets()
        trained = any(model["trained"] for model in prediction.registry())
        for item in items:
            if item["id"] == PRIMARY_DATASET:
                item["model_status"] = "trained" if trained else "untrained"
        return envelope({"items": items})

    @app.get("/api/v1/datasets/{dataset_id}")
    def dataset(dataset_id: str) -> dict[str, object]:
        for item in store.datasets():
            if item["id"] == dataset_id:
                return envelope(item, dataset_id=dataset_id)
        raise DataError("DATASET_NOT_FOUND", "Dataset does not exist.", 404)

    @app.get("/api/v1/sequences")
    def sequences(dataset_id: str = PRIMARY_DATASET) -> dict[str, object]:
        return envelope(
            {"items": store.sequences(dataset_id)},
            dataset_id=dataset_id,
            provenance="REAL_OBSERVED" if dataset_id == PRIMARY_DATASET else None,
        )

    @app.get("/api/v1/sequences/{sequence_id}")
    def sequence(sequence_id: str) -> dict[str, object]:
        return envelope(
            store.sequence_detail(sequence_id),
            dataset_id=PRIMARY_DATASET,
            provenance="REAL_OBSERVED",
        )

    @app.get("/api/v1/sequences/{sequence_id}/frames/{frame_index}")
    def frame(
        sequence_id: str,
        frame_index: int,
        layer: Literal["observed", "annotation", "overlay"] = "observed",
    ) -> Response:
        provenance = {
            "observed": "OBSERVED",
            "annotation": "ANNOTATION",
            "overlay": "OBSERVED+ANNOTATION",
        }
        return Response(
            store.frame_png(sequence_id, frame_index, layer),
            media_type="image/png",
            headers={
                "X-Provenance": provenance[layer],
                "X-Derived-Display": "true",
                "X-Source-Dtype": "uint8" if layer == "annotation" else "uint16",
                "X-Schema-Version": "1",
                "X-Dataset-Id": PRIMARY_DATASET,
                "X-Source-Id": store.summary()["source_id"],
                "X-Sequence-Id": sequence_id,
                "X-Frame-Index": str(frame_index),
                "X-Annotation-Provenance": "source_annotation",
                "Cache-Control": "no-store",
            },
        )

    @app.get("/api/v1/models")
    def models() -> dict[str, Any]:
        return envelope({"items": prediction.registry()})

    @app.post("/api/v1/experiments/predict", status_code=202)
    def submit_predict(payload: PredictionRequest) -> dict[str, Any]:
        pinned = prediction.validate(payload)
        return envelope(
            {"job": queue.submit(payload.model_dump(), pinned)},
            dataset_id=payload.dataset_id,
            provenance="PREDICTION",
        )

    @app.get("/api/v1/jobs/{identifier}")
    def job(identifier: str) -> dict[str, Any]:
        return envelope({"job": queue.public(queue.get(identifier))})

    @app.get("/api/v1/jobs/{identifier}/result")
    def result(identifier: str) -> dict[str, Any]:
        return envelope(queue.result(identifier))

    @app.post("/api/v1/jobs/{identifier}/cancel")
    def cancel(identifier: str) -> dict[str, Any]:
        return envelope({"job": queue.cancel(identifier)})

    @app.get("/api/v1/experiments")
    def experiments() -> dict[str, Any]:
        return envelope({"items": queue.list()})

    @app.get("/api/v1/research")
    def research() -> dict[str, Any]:
        path = root / "docs/research/results/forecast-test-v1.json"
        if not path.is_file():
            return envelope({"status": "pending", "reports": []})
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            if (
                value["schema_version"] != "morpholab-forecast-evaluation-v1"
                or value["split"] != "test"
            ):
                raise ValueError("Unexpected research report schema")
            reports = []
            for variant in (
                "persistence",
                "constant_normal_speed",
                "nca",
                "nca_regularized",
                "convgru",
                "nca_h1",
            ):
                rows = [row for row in value["summary"] if row["variant"] == variant]
                reports.append(
                    {
                        "id": variant,
                        "label": variant.replace("_", " "),
                        "model_id": variant,
                        "observations": 4,
                        "horizon": 24,
                        "seeds": []
                        if variant in ("persistence", "constant_normal_speed")
                        else [17, 29, 43],
                        "metrics": [
                            {
                                "lead": row["lead"],
                                "n": row["n_sequences"],
                                "n_windows": row["n_windows"],
                                "mean": row["metrics_mean"],
                                "sample_sd": row["metrics_std"],
                            }
                            for row in rows
                        ],
                        "provenance": {
                            "split": "test",
                            "git_sha": value["git_sha"],
                            "manifest_sha256": value["source_manifest_sha256"],
                            "target": "DERIVED_ANNOTATION",
                        },
                    }
                )
            return envelope(
                {
                    "status": "available",
                    "reports": reports,
                    "input_sensitivity": value["input_sensitivity"],
                }
            )
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise DataError(
                "RESEARCH_UNAVAILABLE", "Frozen research report failed schema validation."
            ) from exc

    dist = root / "frontend/dist"
    if dist.is_dir() and (dist / "index.html").is_file():
        app.mount("/", WorkbenchFiles(directory=dist, html=True), name="workbench")
    return app


app = create_app()
