"""Frozen-matrix evaluation: history-only forecasts and nested sequence/seed summaries."""

from __future__ import annotations

import csv
import hashlib
import importlib.metadata
import json
import os
import platform
import subprocess
import time
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import torch
import yaml
from PIL import Image, ImageDraw

from morpholab_ml.data.preparation import window_starts
from morpholab_ml.evaluation.metrics import region_metrics
from morpholab_ml.evaluation.runner import (
    BASELINES,
    METRICS,
    PROJECT_ROOT,
    file_sha256,
    git_dirty,
    git_sha,
    load_sequence,
    read_manifest,
    safe_path,
    save_json,
)
from morpholab_ml.training.runner import (
    MODEL_KEYS,
    load_forecaster,
    read_checkpoint,
    resolve_device,
)

SCHEMA = "morpholab-forecast-evaluation-v1"
SEEDS = (17, 29, 43)
VARIANTS = ("nca", "nca_regularized", "convgru", "nca_h1")
HORIZON = 24
STRIDE = 12
SOURCE_FILES = (
    "ml/morpholab_ml/evaluation/learned.py",
    "ml/morpholab_ml/evaluation/metrics.py",
    "ml/morpholab_ml/evaluation/runner.py",
    "ml/morpholab_ml/baselines/geometric.py",
    "ml/morpholab_ml/data/preparation.py",
    "ml/morpholab_ml/models/forecast.py",
    "ml/morpholab_ml/training/runner.py",
    "scripts/evaluate_models.py",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def git_blob(sha: str, relative: str) -> bytes:
    require(len(sha) == 40 and all(c in "0123456789abcdef" for c in sha), "Invalid Git SHA")
    require(
        not relative.startswith(("/", "\\"))
        and ":" not in relative
        and ".." not in relative.split("/")
        and "\\" not in relative,
        "Invalid source path",
    )
    return subprocess.run(
        ["git", "show", f"{sha}:{relative}"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        check=True,
    ).stdout


def verify_source(sha: str, hashes: dict[str, str]) -> None:
    require(bool(hashes), "Missing implementation hashes")
    for name, expected in hashes.items():
        actual = hashlib.sha256(git_blob(sha, name)).hexdigest()
        require(actual == expected, f"Git source hash mismatch: {name}")


def checked_matrix(matrix_root: Path, manifest_sha: str) -> list[dict[str, Any]]:
    """Verify every trained seed before opening any evaluation arrays."""
    matrix = read_json(matrix_root / "matrix.json")
    require(matrix.get("status") == "complete", "Training matrix is not complete")
    require(
        matrix.get("expected_runs") == 12 and len(matrix.get("runs", [])) == 12,
        "Matrix must register exactly 12 runs",
    )
    entries = {r["run_id"]: r for r in matrix["runs"]}
    require(len(entries) == 12, "Duplicate matrix run ID")
    runs = []
    seen = set()
    for run_path in sorted(matrix_root.glob("*/run.json")):
        run_path = safe_path(matrix_root, f"{run_path.parent.name}/run.json")
        metadata = read_json(run_path)
        config = metadata["config"]
        variant = (
            "nca_h1" if config["protocol"] == "morpholab-forecast-h1-v1" else metadata["model_kind"]
        )
        pair = (variant, metadata["seed"])
        require(
            run_path.parent.name == metadata["run_id"] == f"{variant}_seed{metadata['seed']}",
            "Run directory identity mismatch",
        )
        registered = entries.get(metadata["run_id"])
        require(
            registered is not None and registered["variant"] == variant,
            "Run is absent from matrix or variant differs",
        )
        for key in (
            "status",
            "git_sha",
            "git_dirty",
            "seed",
            "completed_steps",
            "best_step",
            "best_validation_loss",
            "checkpoint_sha256",
        ):
            require(registered[key] == metadata[key], f"Matrix/run metadata differs: {key}")
        require(
            variant in VARIANTS and metadata["seed"] in SEEDS and pair not in seen,
            "Unexpected or duplicate matrix member",
        )
        seen.add(pair)
        require(
            metadata["status"] == "complete" and metadata["git_dirty"] is False,
            "Incomplete or dirty training run",
        )
        require(
            metadata["completed_steps"] == metadata["target_steps"] == 600,
            "Training budget differs from frozen 600 steps",
        )
        require(metadata["manifest_sha256"] == manifest_sha, "Training data manifest mismatch")
        require(metadata["test_arrays_loaded"] is False, "Test data used during training")
        require(
            metadata["validation_selection"]
            == "supervised loss; windows then equal sequence weights",
            "Unknown checkpoint selection",
        )
        config_name = "forecast-h1-ablation.yaml" if variant == "nca_h1" else "forecast-v1.yaml"
        frozen = yaml.safe_load(git_blob(metadata["git_sha"], f"ml/configs/{config_name}"))
        require(config == frozen, "Training configuration differs from frozen Git config")
        require(
            config["maximum_steps"] == 600
            and config["batch_size"] == metadata["batch_size"] == 8
            and config["observations"] == 4
            and config["sampling_horizon"] == 12
            and config["train_horizon"] == (1 if variant == "nca_h1" else 12)
            and config["evaluation_horizons"] == [4, 12, 24]
            and config["evaluation_stride"] == STRIDE
            and config["seeds"] == list(SEEDS),
            "Unexpected frozen protocol",
        )
        require(
            metadata["model_kind"] == ("nca" if variant == "nca_h1" else variant),
            "Ablation model kind mismatch",
        )
        require(
            metadata["model_config"] == {key: config[key] for key in MODEL_KEYS},
            "Model configuration mismatch",
        )
        require(
            set(metadata["source_hashes"])
            == {
                "ml/morpholab_ml/training/runner.py",
                "ml/morpholab_ml/models/forecast.py",
                "ml/morpholab_ml/data/preparation.py",
                "ml/morpholab_ml/evaluation/runner.py",
            },
            "Missing training implementation source hashes",
        )
        verify_source(metadata["git_sha"], metadata["source_hashes"])
        for name, expected in metadata["source_hashes"].items():
            require(
                file_sha256(PROJECT_ROOT / name) == expected,
                f"Installed implementation differs from training source: {name}",
            )
        history = read_json(run_path.parent / "history.json")
        require([r["step"] for r in history] == list(range(1, 601)), "Incomplete training history")
        validation = [r for r in history if "validation_loss" in r]
        require(
            [r["step"] for r in validation] == list(range(100, 601, 100)),
            "Unexpected validation schedule",
        )
        require(
            all(np.isfinite(r["validation_loss"]) for r in validation),
            "Nonfinite validation selection loss",
        )
        best = min(validation, key=lambda r: (r["validation_loss"], r["step"]))
        require(
            metadata["best_step"] == best["step"]
            and metadata["best_validation_loss"] == best["validation_loss"],
            "Best checkpoint was not selected by validation loss",
        )
        weight_path = run_path.parent / "best.pt"
        weight_sha = metadata["checkpoint_sha256"]["best.pt"]
        require(file_sha256(weight_path) == weight_sha, "Best checkpoint SHA256 mismatch")
        checkpoint = read_checkpoint(weight_path, weight_sha)
        signature = {
            key: metadata[key]
            for key in (
                "model_kind",
                "model_config",
                "config",
                "seed",
                "batch_size",
                "manifest_sha256",
                "source_hashes",
            )
        }
        require(
            checkpoint["signature"] == signature
            and all(checkpoint[key] == value for key, value in signature.items())
            and checkpoint["git_sha"] == metadata["git_sha"]
            and checkpoint["git_dirty"] is False
            and checkpoint["step"] == best["step"]
            and checkpoint["best_step"] == best["step"]
            and checkpoint["best_loss"] == best["validation_loss"],
            "Checkpoint identity, source or selected step mismatch",
        )
        runs.append(
            {
                "variant": variant,
                "seed": metadata["seed"],
                "metadata": metadata,
                "directory": run_path.parent,
                "weight_path": weight_path,
                "best_sha256": weight_sha,
                "run_json_sha256": file_sha256(run_path),
                "history_sha256": file_sha256(run_path.parent / "history.json"),
            }
        )
    require(seen == {(v, s) for v in VARIANTS for s in SEEDS}, "Expected exactly 12 trained runs")
    require(len({r["metadata"]["git_sha"] for r in runs}) == 1, "Mixed model source revisions")
    return runs


def evaluation_windows(
    arrays: dict[str, Any], observations: int = 4, *, matched: bool = False
) -> list[dict[str, Any]]:
    """Sensitivity uses the same eight-frame QC block and forecast origin for all L."""
    require(observations in (2, 4, 8), "Input length must be 2, 4 or 8")
    candidate_length = 8 if matched else observations
    starts = window_starts(arrays["valid"], candidate_length, HORIZON, STRIDE)
    return [
        {
            "window_start": start,
            "forecast_origin": start + candidate_length,
            "history": arrays["working_sdf"][
                start + candidate_length - observations : start + candidate_length
            ].copy(),
            "source_history_indices": arrays["source_frame_indices"][
                start + candidate_length - observations : start + candidate_length
            ].tolist(),
        }
        for start in starts
    ]


def summarize_forecasts(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Windows -> sequence means -> seed means -> seed sample SD (not sequence×seed)."""
    require(bool(rows), "No evaluation rows")
    grouped: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    identities = set()
    coverage: dict[tuple[Any, ...], set[tuple[Any, ...]]] = defaultdict(set)
    for row in rows:
        key = tuple(
            row[k]
            for k in ("variant", "seed", "observations", "window_protocol", "sequence_id", "lead")
        )
        identity = (*key, row["window_start"])
        require(identity not in identities, "Duplicate evaluation row")
        identities.add(identity)
        require(all(np.isfinite(row[m]) for m in METRICS), "Nonfinite evaluation metric")
        grouped[key].append(row)
        coverage[
            (row["variant"], row["seed"], row["observations"], row["window_protocol"], row["lead"])
        ].add((row["sequence_id"], row["window_start"]))
    common = {}
    for (_, _, length, protocol, lead), windows in coverage.items():
        reference = common.setdefault((length, protocol, lead), windows)
        require(windows == reference, "Models or seeds evaluated different windows")
    per_sequence = []
    for (variant, seed, length, protocol, sequence, lead), group in grouped.items():
        per_sequence.append(
            {
                "variant": variant,
                "seed": seed,
                "observations": length,
                "window_protocol": protocol,
                "sequence_id": sequence,
                "lead": lead,
                "n_windows": len(group),
                "metrics": {m: float(np.mean([r[m] for r in group])) for m in METRICS},
            }
        )
    seed_groups: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in per_sequence:
        seed_groups[
            tuple(row[k] for k in ("variant", "observations", "window_protocol", "lead"))
        ].append(row)
    summary = []
    for (variant, length, protocol, lead), group in sorted(seed_groups.items()):
        learned = variant in VARIANTS
        expected_seeds = set(SEEDS) if learned else {None}
        require({r["seed"] for r in group} == expected_seeds, "Missing or extra evaluation seed")
        seed_means = []
        sequence_set = None
        windows_per_seed = []
        for seed in SEEDS if learned else (None,):
            sequence_rows = [r for r in group if r["seed"] == seed]
            ids = {r["sequence_id"] for r in sequence_rows}
            if sequence_set is None:
                sequence_set = ids
            require(ids == sequence_set, "Seed sequence coverage mismatch")
            windows_per_seed.append(sum(r["n_windows"] for r in sequence_rows))
            seed_means.append(
                {m: float(np.mean([r["metrics"][m] for r in sequence_rows])) for m in METRICS}
            )
        require(len(set(windows_per_seed)) == 1, "Seed window counts differ")
        summary.append(
            {
                "variant": variant,
                "observations": length,
                "window_protocol": protocol,
                "lead": lead,
                "is_endpoint": lead in (4, 12, 24),
                "n_sequences": len(sequence_set or []),
                "n_windows": windows_per_seed[0],
                "n_seeds": 3 if learned else 0,
                "n_realizations": len(seed_means),
                "metrics_mean": {m: float(np.mean([r[m] for r in seed_means])) for m in METRICS},
                "metrics_std": {
                    m: float(np.std([r[m] for r in seed_means], ddof=1)) if learned else None
                    for m in METRICS
                },
            }
        )
    return {"per_sequence": per_sequence, "summary": summary}


def predict(model: Any, history: np.ndarray, device: torch.device) -> np.ndarray:
    with torch.inference_mode():
        values = model(
            torch.as_tensor(history.copy(), dtype=torch.float32, device=device).unsqueeze(0),
            HORIZON,
        ).predictions
    prediction = values.detach().cpu().numpy()
    require(
        prediction.shape == (1, HORIZON, 64, 64) and np.isfinite(prediction).all(),
        "Nonfinite or incorrectly shaped model forecast",
    )
    return prediction[0]


def score_windows(
    arrays: dict[str, Any],
    record: dict[str, Any],
    variant: str,
    seed: int | None,
    predictor: Any,
    observations: int,
    matched: bool,
) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    rows = []
    worst = None
    for window in evaluation_windows(arrays, observations, matched=matched):
        history = window["history"]
        prediction = np.asarray(predictor(history.copy()))
        require(
            prediction.shape == (HORIZON, 64, 64) and np.isfinite(prediction).all(),
            "Nonfinite or incorrectly shaped forecast",
        )
        for lead in range(1, HORIZON + 1):
            index = window["forecast_origin"] + lead - 1
            row = {
                "variant": variant,
                "seed": seed,
                "sequence_id": record["sequence_id"],
                "project_split": record["project_split"],
                "observations": observations,
                "window_protocol": "matched_origin8" if matched else "main_L4",
                "window_start": window["window_start"],
                "forecast_origin": window["forecast_origin"],
                "source_history_indices": window["source_history_indices"],
                "source_target_index": int(arrays["source_frame_indices"][index]),
                "lead": lead,
                "is_endpoint": lead in (4, 12, 24),
                **region_metrics(prediction[lead - 1] > 0, arrays["working_region"][index]),
            }
            rows.append(row)
            if lead == HORIZON and (worst is None or row["iou"] < worst["metrics"]["iou"]):
                worst = {
                    "metrics": row.copy(),
                    "history": history[-1] > 0,
                    "target": arrays["working_region"][index].copy(),
                    "prediction": prediction[-1] > 0,
                    "observed": arrays["images_native"][index].copy(),
                }
    return rows, worst


def failure_image(case: dict[str, Any], destination: Path) -> None:
    """Actual observation plus derived-history/target and algorithm prediction panels."""
    row = case["metrics"]
    canvas = Image.new("RGB", (1024, 330), "#111820")
    draw = ImageDraw.Draw(canvas)
    draw.text(
        (8, 8),
        f"{row['variant']} seed={row['seed']} {row['sequence_id']} "
        f"origin={row['forecast_origin']} lead=24 target frame={row['source_target_index']}",
        fill="white",
    )
    observed = case["observed"].astype(float)
    lo, hi = np.percentile(observed, [1, 99])
    observed = (np.clip((observed - lo) / max(hi - lo, 1), 0, 1) * 255).astype(np.uint8)
    panels = [
        observed,
        *(case[key].astype(np.uint8) * 255 for key in ("history", "target", "prediction")),
    ]
    labels = (
        "OBSERVED: target (contrast mapped)",
        f"HISTORY: DERIVED_ANNOTATION ({row['source_history_indices'][-1]})",
        "TARGET: DERIVED_ANNOTATION",
        "MODEL_PREDICTION" if row["variant"] in VARIANTS else "PREDICTION (deterministic)",
    )
    for i, (panel, label) in enumerate(zip(panels, labels, strict=True)):
        canvas.paste(
            Image.fromarray(panel).convert("RGB").resize((240, 240), Image.Resampling.NEAREST),
            (i * 256 + 8, 60),
        )
        draw.text((i * 256 + 8, 38), label, fill="white")
    draw.text(
        (8, 310),
        "Backova et al. 2023 / Zenodo 7660424 / CC BY 4.0 / modified visualization",
        fill="white",
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(destination)


def evaluate_models(
    manifest_path: Path,
    matrix_root: Path,
    output: Path,
    *,
    split: str = "validation",
    device: str = "auto",
) -> dict[str, Any]:
    started = time.monotonic()
    require(split in ("validation", "test"), "Choose validation or explicit test split")
    require(
        not output.exists() or (output.is_dir() and not any(output.iterdir())),
        "Output must be new or empty",
    )
    require(
        not output.resolve().is_relative_to(matrix_root.resolve()),
        "Cannot write into source matrix",
    )
    output.mkdir(parents=True, exist_ok=True)
    metadata = {
        "schema_version": SCHEMA,
        "status": "running",
        "split": split,
        "git_sha": git_sha(),
        "git_dirty": git_dirty(),
        "source_manifest_sha256": file_sha256(manifest_path),
        "started_utc": datetime.now(UTC).isoformat(),
    }
    save_json(output / "run.json", metadata)
    try:
        require(
            metadata["git_dirty"] is False, "Formal evaluation requires a clean committed worktree"
        )
        manifest = read_manifest(manifest_path)
        require(len(manifest["sequences"]) == 62, "Complete 62-sequence manifest required")
        runs = checked_matrix(matrix_root, metadata["source_manifest_sha256"])
        source_hashes = {name: file_sha256(PROJECT_ROOT / name) for name in SOURCE_FILES}
        verify_source(metadata["git_sha"], source_hashes)
        records = [r for r in manifest["sequences"] if r["project_split"] == split]
        arrays = {r["sequence_id"]: load_sequence(manifest_path.parent, r) for r in records}
        os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
        require(
            os.environ["CUBLAS_WORKSPACE_CONFIG"] in (":4096:8", ":16:8"),
            "Deterministic CUDA requires a supported CUBLAS workspace configuration",
        )
        selected_device = resolve_device(device)
        if selected_device.type == "cpu":
            torch.set_num_threads(1)
        torch.use_deterministic_algorithms(True)
        torch.backends.cuda.matmul.fp32_precision = "ieee"
        torch.backends.cudnn.conv.fp32_precision = "ieee"
        torch.backends.cudnn.benchmark = False
        rows = []
        worst_by_variant = {}
        public_runs = []
        for run in runs:
            metadata["active_variant"] = run["variant"]
            metadata["active_seed"] = run["seed"]
            save_json(output / "run.json", metadata)
            model = load_forecaster(run["weight_path"], str(selected_device), run["best_sha256"])
            require(
                sum(p.numel() for p in model.parameters()) == run["metadata"]["parameter_count"],
                "Model parameter count mismatch",
            )

            def predictor(h, model=model):
                return predict(model, h, selected_device)

            for record in records:
                for length, matched in ((4, False), (2, True), (4, True), (8, True)):
                    scored, case = score_windows(
                        arrays[record["sequence_id"]],
                        record,
                        run["variant"],
                        run["seed"],
                        predictor,
                        length,
                        matched,
                    )
                    require(bool(scored), "A selected sequence has no valid common windows")
                    rows.extend(scored)
                    if not matched and case is not None:
                        previous = worst_by_variant.get(run["variant"])
                        if previous is None or case["metrics"]["iou"] < previous["metrics"]["iou"]:
                            worst_by_variant[run["variant"]] = case
            public_runs.append(
                {
                    "variant": run["variant"],
                    "seed": run["seed"],
                    "best_sha256": run["best_sha256"],
                    "run_json_sha256": run["run_json_sha256"],
                    "history_sha256": run["history_sha256"],
                    **{
                        k: run["metadata"][k]
                        for k in (
                            "git_sha",
                            "git_dirty",
                            "config",
                            "model_kind",
                            "model_config",
                            "source_hashes",
                            "parameter_count",
                            "best_step",
                            "completed_steps",
                            "best_validation_loss",
                            "elapsed_seconds",
                            "cuda_peak_allocated_bytes",
                            "cpu_peak_memory_bytes",
                            "versions",
                            "device",
                            "precision",
                        )
                    },
                }
            )
            del model
        for variant, baseline in BASELINES.items():
            metadata.update(active_variant=variant, active_seed=None)
            save_json(output / "run.json", metadata)
            for record in records:
                for length, matched in ((4, False), (2, True), (4, True), (8, True)):
                    scored, case = score_windows(
                        arrays[record["sequence_id"]],
                        record,
                        variant,
                        None,
                        lambda h, b=baseline: b(h, HORIZON, distance_clip=8),
                        length,
                        matched,
                    )
                    require(bool(scored), "A selected sequence has no valid common windows")
                    rows.extend(scored)
                    if not matched and case is not None:
                        previous = worst_by_variant.get(variant)
                        if previous is None or case["metrics"]["iou"] < previous["metrics"]["iou"]:
                            worst_by_variant[variant] = case
        aggregated = summarize_forecasts(rows)
        failures = []
        for variant, case in sorted(worst_by_variant.items()):
            relative = f"failure-cases/{variant}.png"
            failure_image(case, output / relative)
            failures.append(
                {
                    "variant": variant,
                    "selection": "minimum main-L4 lead24 window IoU across all seeds",
                    "metrics": case["metrics"],
                    "png_relpath": relative,
                    "png_sha256": file_sha256(output / relative),
                    "target_provenance": "DERIVED_ANNOTATION",
                    "prediction_provenance": "MODEL_PREDICTION"
                    if variant in VARIANTS
                    else "PREDICTION",
                }
            )
        qc = []
        for record in records:
            data = arrays[record["sequence_id"]]
            for matched, length in ((False, 4), (True, 8)):
                possible = len(range(0, len(data["valid"]) - length - HORIZON + 1, STRIDE))
                valid = len(evaluation_windows(data, length, matched=matched))
                qc.append(
                    {
                        "sequence_id": record["sequence_id"],
                        "window_protocol": "matched_origin8" if matched else "main_L4",
                        "candidate_windows": possible,
                        "valid_windows": valid,
                        "qc_excluded_windows": possible - valid,
                    }
                )
        main = [r for r in aggregated["summary"] if r["window_protocol"] == "main_L4"]
        sensitivity = [
            r for r in aggregated["summary"] if r["window_protocol"] == "matched_origin8"
        ]
        result = {
            "schema_version": SCHEMA,
            "status": "complete",
            "split": split,
            "source_manifest_sha256": metadata["source_manifest_sha256"],
            "git_sha": metadata["git_sha"],
            "git_dirty": metadata["git_dirty"],
            "implementation_file_sha256": source_hashes,
            "matrix_sha256": file_sha256(matrix_root / "matrix.json"),
            "manifest_scope": "complete_62_sequence_source",
            "protocol": manifest["protocol"],
            "source_archive": manifest["source_archive"],
            "runs": public_runs,
            "per_sequence": aggregated["per_sequence"],
            "summary": main,
            "input_sensitivity": sensitivity,
            "failure_cases": failures,
            "window_qc": qc,
            "official_split": None,
            "grouping_basis": "source_sequence_proxy",
            "target_provenance": "DERIVED_ANNOTATION",
            "prediction_provenance": "MODEL_PREDICTION",
            "metric_units": {
                "area_mae": "64-grid pixel^2",
                "signed_area_error": "64-grid pixel^2",
                "mean_boundary_distance": "64-grid pixel",
                "hausdorff95": "64-grid pixel",
            },
            "configuration": {
                "observations": 4,
                "horizon": HORIZON,
                "stride": STRIDE,
                "input_sensitivity_lengths": [2, 4, 8],
                "sensitivity_origin_offset": 8,
            },
            "aggregation": "window means within sequence; equal sequences within seed; "
            "mean and sample SD across 3 seeds",
            "seed_sd_note": "SD describes training-seed variation, not biological uncertainty; "
            "deterministic baseline SD is null",
            "evaluation_environment": {
                "python": platform.python_version(),
                "torch": str(torch.__version__),
                "numpy": np.__version__,
                "scipy": importlib.metadata.version("scipy"),
                "pillow": importlib.metadata.version("pillow"),
                "cuda_runtime": torch.version.cuda,
                "device": str(selected_device),
                "matmul_fp32_precision": torch.backends.cuda.matmul.fp32_precision,
                "convolution_fp32_precision": torch.backends.cudnn.conv.fp32_precision,
                "deterministic_algorithms": torch.are_deterministic_algorithms_enabled(),
                "cudnn_benchmark": torch.backends.cudnn.benchmark,
                "cpu_threads": torch.get_num_threads(),
                "cublas_workspace_config": os.environ["CUBLAS_WORKSPACE_CONFIG"],
            },
            "elapsed_seconds": time.monotonic() - started,
        }
        save_json(output / "metrics.json", rows)
        with (output / "metrics.csv").open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        save_json(output / "per_sequence.json", result["per_sequence"])
        save_json(output / "summary.json", {"summary": main, "input_sensitivity": sensitivity})
        result["source_files_sha256"] = {
            name: file_sha256(output / name)
            for name in ("metrics.json", "summary.json", "per_sequence.json")
        }
        save_json(output / "report.json", result)
        metadata.update(status="complete", n_sequences=len(records), n_runs=len(runs))
        return result
    except BaseException as exc:
        metadata.update(status="failed", error_type=type(exc).__name__, error=str(exc)[:2000])
        raise
    finally:
        metadata.update(
            elapsed_seconds=time.monotonic() - started, finished_utc=datetime.now(UTC).isoformat()
        )
        save_json(output / "run.json", metadata)
