"""Whitelisted model registry and computation isolated from HTTP and persistence."""

from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path
from typing import Any, Literal

import contourpy
import numpy as np
from morpholab_ml.baselines.geometric import constant_normal_speed, persistence
from morpholab_ml.evaluation.metrics import region_metrics
from morpholab_ml.evaluation.runner import file_sha256, load_sequence, read_manifest, safe_path
from pydantic import BaseModel, ConfigDict, Field

from backend.app.data import PRIMARY_DATASET, DataError

VARIANTS = ("nca", "nca_regularized", "convgru", "nca_h1")
BASELINES = {"persistence": persistence, "constant_normal_speed": constant_normal_speed}


class PredictionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    dataset_id: Literal["drosophila_wound_zenodo_7660424"]
    sequence_id: str = Field(pattern=r"^(Test\d{2}|WH\d{2}|WHu\d{2})$")
    model_id: Literal[
        "persistence", "constant_normal_speed", "nca", "nca_regularized", "convgru", "nca_h1"
    ]
    observation_start: int = Field(ge=0)
    observations: Literal[2, 4, 8]
    horizon: int = Field(ge=1, le=24)


class PredictionService:
    def __init__(self, artifacts: Path):
        self.artifacts = artifacts.resolve()
        self.manifest_path = self.artifacts / "processed/manifest.json"
        self.training = self.artifacts / "training/forecast-v1"

    def manifest(self) -> dict[str, Any]:
        try:
            return read_manifest(self.manifest_path)
        except (OSError, ValueError, KeyError) as exc:
            raise DataError(
                "PREPARATION_UNAVAILABLE", "Verified prepared data is unavailable."
            ) from exc

    def registry(self) -> list[dict[str, Any]]:
        items = [
            {
                "id": name,
                "label": name.replace("_", " "),
                "kind": "baseline",
                "variant": name,
                "seed": None,
                "trained": False,
                "available": True,
                "selection": None,
                "checkpoint_sha256": None,
            }
            for name in BASELINES
        ]
        rows = []
        try:
            matrix = json.loads((self.training / "matrix.json").read_text(encoding="utf-8"))
            candidates = matrix["runs"]
            expected = {(variant, seed) for variant in VARIANTS for seed in (17, 29, 43)}
            if (
                matrix["status"] != "complete"
                or matrix["expected_runs"] != 12
                or len(candidates) != 12
                or {(r["variant"], r["seed"]) for r in candidates} != expected
                or any(
                    r["status"] != "complete"
                    or r["completed_steps"] != 600
                    or not np.isfinite(r["best_validation_loss"])
                    or r.get("git_dirty") is not False
                    or not re.fullmatch(r"[0-9a-f]{40}", r.get("git_sha", ""))
                    for r in candidates
                )
            ):
                raise ValueError("Incomplete frozen training matrix")
            rows = candidates
        except (OSError, ValueError, TypeError, KeyError):
            pass
        for variant in VARIANTS:
            chosen = min(
                (row for row in rows if row["variant"] == variant),
                key=lambda row: (row["best_validation_loss"], row["seed"]),
                default=None,
            )
            info = {
                "id": variant,
                "label": variant.replace("_", " "),
                "kind": "trained",
                "variant": variant,
                "seed": None,
                "trained": False,
                "available": False,
                "selection": None,
                "checkpoint_sha256": None,
            }
            if chosen:
                info.update(trained=True, unavailable_reason="Verified weight file unavailable")
                identifier = chosen.get("run_id", "")
                digest = chosen.get("checkpoint_sha256", {}).get("best.pt", "")
                if re.fullmatch(r"[a-z0-9_]+", identifier) and re.fullmatch(
                    r"[0-9a-f]{64}", digest
                ):
                    try:
                        path = safe_path(self.training, identifier + "/best.pt")
                        if file_sha256(path) != digest:
                            raise ValueError("Checkpoint hash mismatch")
                        runtime = importlib.util.find_spec("torch") is not None
                        run_file = self.training / identifier / "run.json"
                        details = (
                            json.loads(run_file.read_text(encoding="utf-8"))
                            if run_file.is_file()
                            else {}
                        )
                        info.update(
                            seed=chosen["seed"],
                            trained=True,
                            available=runtime,
                            unavailable_reason=None if runtime else "Install the cpu or cuda extra",
                            run_id=identifier,
                            model_git_sha=chosen["git_sha"],
                            parameter_count=details.get("parameter_count"),
                            checkpoint_sha256=digest,
                            selection={
                                "criterion": "validation_supervised_loss",
                                "loss": chosen["best_validation_loss"],
                                "step": chosen["best_step"],
                            },
                        )
                    except (OSError, ValueError):
                        pass
            items.append(info)
        return items

    def validate(self, request: PredictionRequest) -> dict[str, Any]:
        manifest = self.manifest()
        record = next(
            (r for r in manifest["sequences"] if r["sequence_id"] == request.sequence_id), None
        )
        if record is None:
            raise DataError("SEQUENCE_NOT_FOUND", "Sequence does not exist.", 404)
        end = request.observation_start + request.observations
        if end + request.horizon > record["frame_count"]:
            raise DataError("INVALID_WINDOW", "Prediction must remain within recorded frames.", 422)
        invalid = set(record["invalid_frame_indices"])
        if end > record["frame_count"] or any(
            i in invalid for i in range(request.observation_start, end)
        ):
            raise DataError(
                "INVALID_CONTEXT", "Every observed source frame must pass preparation QC.", 422
            )
        model = next(item for item in self.registry() if item["id"] == request.model_id)
        if not model["available"]:
            raise DataError("MODEL_UNAVAILABLE", "Verified trained model is unavailable.")
        return {
            "model": model,
            "manifest_sha256": file_sha256(self.manifest_path),
            "npz_sha256": record["output_file_sha256"],
        }

    def compute(
        self, request: PredictionRequest, pinned: dict[str, Any], cancelled
    ) -> dict[str, Any]:
        if cancelled():
            raise InterruptedError("Cancelled")
        manifest = self.manifest()
        if file_sha256(self.manifest_path) != pinned["manifest_sha256"]:
            raise ValueError("Source manifest changed after submission")
        record = next(r for r in manifest["sequences"] if r["sequence_id"] == request.sequence_id)
        if record["output_file_sha256"] != pinned["npz_sha256"]:
            raise ValueError("Prepared sequence changed after submission")
        arrays = load_sequence(self.manifest_path.parent, record)
        start, length = request.observation_start, request.observations
        if not arrays["valid"][start : start + length].all():
            raise ValueError("Invalid observation QC")
        history = arrays["working_sdf"][start : start + length].copy()
        model = pinned["model"]
        if request.model_id in BASELINES:
            prediction = BASELINES[request.model_id](history, request.horizon, distance_clip=8)
        else:
            import torch
            from morpholab_ml.training.runner import load_forecaster

            path = safe_path(self.training, model["run_id"] + "/best.pt")
            forecaster = load_forecaster(
                path, device="cpu", expected_sha256=model["checkpoint_sha256"]
            )
            with torch.inference_mode():
                prediction = forecaster(torch.from_numpy(history).unsqueeze(0), request.horizon)
                prediction = prediction.predictions[0].cpu().numpy()
        prediction = np.asarray(prediction)
        if prediction.shape != (request.horizon, 64, 64) or not np.isfinite(prediction).all():
            raise ValueError("Invalid prediction output")
        frames = []
        for index, sdf in enumerate(prediction):
            if cancelled():
                raise InterruptedError("Cancelled")
            source_index = start + length + index
            valid = source_index < len(arrays["valid"]) and bool(arrays["valid"][source_index])
            region = sdf > 0
            target = arrays["working_region"][source_index] if valid else None
            contour = contourpy.contour_generator(z=sdf, name="serial").lines(0)
            frames.append(
                {
                    "lead": index + 1,
                    "source_frame_index": source_index,
                    "contours": [line.tolist() for line in contour],
                    "region": region.astype(int).tolist(),
                    "region_area": int(region.sum()),
                    "target_valid": valid,
                    "target_region": target.astype(int).tolist() if valid else None,
                    "metrics": dict(region_metrics(region, target)) if valid else None,
                }
            )
        return {
            "status": "succeeded",
            "request": request.model_dump(),
            "dataset_id": PRIMARY_DATASET,
            "model_id": request.model_id,
            "grid": {
                "width": 64,
                "height": 64,
                "contour_coordinates": "working-grid pixel centers",
            },
            "source": {
                "source_id": manifest["source_archive"]["source_id"],
                "sequence_id": request.sequence_id,
                "archive_sha256": manifest["source_archive"]["sha256"],
                "manifest_sha256": pinned["manifest_sha256"],
                "npz_sha256": pinned["npz_sha256"],
                "original_width": 128,
                "original_height": 128,
                "project_split": record["project_split"],
            },
            "model": model,
            "frames": frames,
            "provenance": "MODEL_PREDICTION" if request.model_id in VARIANTS else "PREDICTION",
            "target_provenance": "DERIVED_ANNOTATION",
            "device": "cpu",
            "precision": "fp32",
            "inference_environment": {
                "deterministic": True,
                "cpu_threads": 1,
                "convolution_fp32_precision": "ieee",
            },
        }
