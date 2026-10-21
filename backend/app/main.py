"""Local read-only HTTP adapter. Start with ``uv run python scripts/serve.py``."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from starlette.exceptions import HTTPException

from backend.app.data import PRIMARY_DATASET, RECOVERY, DataError, DataStore

ROOT = Path(__file__).resolve().parents[2]


def envelope(
    payload: dict[str, Any], *, dataset_id: str | None = None, provenance: str | None = None
) -> dict[str, Any]:
    """Apply the common response contract without inventing model/run provenance."""
    return {
        **payload,
        "schema_version": "1",
        "provenance": provenance,
        "dataset_id": dataset_id,
        "model_id": None,
        "run_id": None,
        "created_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }


def create_app(root: Path = ROOT) -> FastAPI:
    app = FastAPI(title="MorphoLab local data API", version="0.1.0")
    store = DataStore(root)
    app.state.store = store

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
                "model_status": "untrained",
                "read_only": True,
            }
        )

    @app.get("/api/v1/datasets")
    def datasets() -> dict[str, object]:
        return envelope({"items": store.datasets()})

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

    return app


app = create_app()
