"""Offline evaluation with source verification, common windows and sequence-level means."""

from __future__ import annotations

import csv
import hashlib
import importlib.metadata
import json
import subprocess
import time
import uuid
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any

import numpy as np
from PIL import Image, ImageDraw

from morpholab_ml.baselines.geometric import constant_normal_speed, persistence
from morpholab_ml.data.preparation import PROTOCOL, QC_PARAMETERS, split_assignments, window_starts
from morpholab_ml.evaluation.metrics import region_metrics

SOURCE_SHA256 = "0f74010ea3eb5820176c1c04a1804928efe23002dde3c2429e1c90defb497e57"
BASELINES = {"persistence": persistence, "constant_normal_speed": constant_normal_speed}
METRICS = (
    "iou",
    "dice",
    "area_mae",
    "signed_area_error",
    "mean_boundary_distance",
    "hausdorff95",
    "empty_boundary_mismatch",
)
PROJECT_ROOT = Path(__file__).resolve().parents[3]


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def save_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8"
    )


def safe_path(root: Path, relative: str) -> Path:
    if (
        not isinstance(relative, str)
        or not relative
        or "\\" in relative
        or ":" in relative
        or "\x00" in relative
        or PurePosixPath(relative).is_absolute()
        or any(part in ("", ".", "..") for part in relative.split("/"))
    ):
        raise ValueError("Unsafe relative NPZ path")
    root = root.resolve(strict=True)
    path = (root / relative).resolve(strict=True)
    if not root.is_dir() or not path.is_relative_to(root) or not path.is_file():
        raise ValueError("NPZ path escapes processed root or is not a file")
    return path


def read_manifest(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if (
        data.get("schema_version") != "morpholab-preparation-v1"
        or data.get("protocol") != PROTOCOL
        or data.get("source_archive") != {"source_id": "zenodo:7660424", "sha256": SOURCE_SHA256}
        or data.get("qc_parameters") != QC_PARAMETERS
    ):
        raise ValueError("Manifest source, schema, preparation or split protocol mismatch")
    records = data.get("sequences", [])
    if not records or data.get("totals", {}).get("sequences") != len(records):
        raise ValueError("Manifest sequence count mismatch")
    known_ids = (
        [f"Test{i:02d}" for i in range(1, 6)]
        + [f"WH{i:02d}" for i in range(1, 36)]
        + [f"WHu{i:02d}" for i in range(1, 23)]
    )
    assignments = split_assignments(known_ids)
    seen = set()
    groups = {}
    for record in records:
        key = record["sequence_id"]
        if key in seen or key not in assignments:
            raise ValueError("Duplicate or unknown sequence ID")
        seen.add(key)
        if record["project_split"] != assignments[key] or record["official_split"] is not None:
            raise ValueError("Sequence split differs from frozen project protocol")
        if record["grouping_basis"] != "source_sequence_proxy":
            raise ValueError("Unknown independent grouping basis")
        previous = groups.setdefault(record["experiment_id"], record["project_split"])
        if previous != record["project_split"]:
            raise ValueError("Experiment crosses project splits")
    return data


def load_sequence(root: Path, record: dict[str, Any]) -> dict[str, np.ndarray]:
    path = safe_path(root, record["npz_relpath"])
    if file_sha256(path) != record["output_file_sha256"]:
        raise ValueError("NPZ file SHA256 mismatch")
    with np.load(path, allow_pickle=False) as bundle:
        arrays = {key: bundle[key] for key in bundle.files}
    count = record["frame_count"]
    specs = {
        "images_native": ((count, 128, 128), np.uint16),
        "source_boundary_native": ((count, 128, 128), np.uint8),
        "derived_region_native": ((count, 128, 128), np.bool_),
        "working_region": ((count, 64, 64), np.bool_),
        "working_sdf": ((count, 64, 64), np.float32),
        "valid": ((count,), np.bool_),
        "source_frame_indices": ((count,), np.int64),
    }
    if type(count) is not int or count <= 0 or set(arrays) != set(specs):
        raise ValueError("NPZ frame count or array schema mismatch")
    for key, (shape, dtype) in specs.items():
        array = arrays[key]
        if array.shape != shape or array.dtype != dtype or not np.isfinite(array).all():
            raise ValueError(f"NPZ shape, dtype or finite-value mismatch: {key}")
        if record["arrays"].get(key) != {"shape": list(shape), "dtype": str(array.dtype)}:
            raise ValueError(f"NPZ array metadata mismatch: {key}")
    if not np.array_equal(arrays["source_frame_indices"], np.arange(count)):
        raise ValueError("Source frame indices contain gaps or reorderings")
    valid = arrays["valid"]
    if (
        int(valid.sum()) != record["valid_frame_count"]
        or np.flatnonzero(~valid).tolist() != record["invalid_frame_indices"]
    ):
        raise ValueError("NPZ valid mask differs from manifest QC")
    sdf = arrays["working_sdf"]
    if np.abs(sdf).max() > 1.00001 or not np.array_equal(
        sdf[valid] > 0, arrays["working_region"][valid]
    ):
        raise ValueError("Working SDF range or derived-region sign mismatch")
    if (
        (arrays["working_region"][valid].sum(axis=(1, 2)) == 0)
        | (arrays["working_region"][valid].sum(axis=(1, 2)) == 4096)
    ).any():
        raise ValueError("Valid derived region is empty or full")
    return arrays


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    grouped = defaultdict(list)
    for row in rows:
        grouped[(row["baseline"], row["sequence_id"], row["lead"])].append(row)
    per_sequence = []
    for (baseline, sequence, lead), group in sorted(grouped.items()):
        per_sequence.append(
            {
                "baseline": baseline,
                "sequence_id": sequence,
                "lead": lead,
                "n_windows": len(group),
                **{key: float(np.mean([float(row[key]) for row in group])) for key in METRICS},
            }
        )
    aggregate_groups = defaultdict(list)
    for row in per_sequence:
        aggregate_groups[(row["baseline"], row["lead"])].append(row)
    aggregate = []
    for (baseline, lead), group in sorted(aggregate_groups.items()):
        aggregate.append(
            {
                "baseline": baseline,
                "lead": lead,
                "n_sequences": len(group),
                "n_windows": sum(row["n_windows"] for row in group),
                **{key: float(np.mean([row[key] for row in group])) for key in METRICS},
            }
        )
    return {
        "aggregation": "windows within sequence, then equal sequence weights",
        "per_sequence": per_sequence,
        "aggregate": aggregate,
    }


def git_sha() -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=PROJECT_ROOT, capture_output=True, text=True, check=False
    )
    return result.stdout.strip() if result.returncode == 0 else None


def git_dirty() -> bool | None:
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return bool(result.stdout.strip()) if result.returncode == 0 else None


def evaluate(
    manifest_path: Path,
    output: Path,
    *,
    split: str = "validation",
    observations: int = 4,
    horizons: tuple[int, ...] = (4, 12, 24),
    stride: int = 12,
    failure_count: int = 3,
) -> dict[str, Any]:
    started = time.monotonic()
    if split not in {"train", "validation", "test"}:
        raise ValueError("Choose an explicit assigned project split")
    if (
        not horizons
        or any(type(h) is not int or h <= 0 for h in horizons)
        or len(horizons) != len(set(horizons))
        or type(observations) is not int
        or observations < 2
        or type(stride) is not int
        or stride < 1
        or type(failure_count) is not int
        or failure_count < 0
    ):
        raise ValueError("Invalid observations, horizons, stride or failure count")
    manifest = read_manifest(manifest_path)
    selected = [record for record in manifest["sequences"] if record["project_split"] == split]
    if not selected:
        raise ValueError("Selected split has no sequences")
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        raise ValueError("Evaluation output must be a new or empty directory")
    output.mkdir(parents=True, exist_ok=True)
    metadata = {
        "run_id": output.name,
        "status": "running",
        "git_sha": git_sha(),
        "git_dirty": git_dirty(),
        "implementation_file_sha256": {
            name: file_sha256(PROJECT_ROOT / name)
            for name in (
                "ml/morpholab_ml/evaluation/runner.py",
                "ml/morpholab_ml/evaluation/metrics.py",
                "ml/morpholab_ml/baselines/geometric.py",
                "ml/morpholab_ml/data/preparation.py",
            )
        },
        "source_manifest_sha256": file_sha256(manifest_path),
        "manifest_scope": "complete_62_sequence_source"
        if len(manifest["sequences"]) == 62
        else "partial_source_manifest",
        "protocol": PROTOCOL,
        "split": split,
        "official_split": None,
        "observations": observations,
        "horizons": sorted(horizons),
        "stride": stride,
        "distance_clip": 8,
        "maximum_classical_speed": 2,
        "baselines": list(BASELINES),
        "seeds": [],
        "randomness": "none: deterministic geometric baselines",
        "versions": {
            name: importlib.metadata.version(name) for name in ("numpy", "scipy", "pillow")
        },
        "target_provenance": "DERIVED_ANNOTATION",
        "prediction_provenance": "PREDICTION",
        "metric_units": {
            "area_mae": "64-grid pixel^2",
            "mean_boundary_distance": "64-grid pixel",
            "hausdorff95": "64-grid pixel",
        },
        "started_utc": datetime.now(UTC).isoformat(),
    }
    save_json(output / "run.json", metadata)
    try:
        rows = []
        qc = []
        max_horizon = max(horizons)
        for record in selected:
            arrays = load_sequence(manifest_path.parent, record)
            starts = window_starts(arrays["valid"], observations, max_horizon, stride)
            possible = len(range(0, len(arrays["valid"]) - observations - max_horizon + 1, stride))
            qc.append(
                {
                    "sequence_id": record["sequence_id"],
                    "candidate_windows": possible,
                    "valid_windows": len(starts),
                    "qc_excluded_windows": possible - len(starts),
                }
            )
            for start in starts:
                for baseline, predictor in BASELINES.items():
                    history = arrays["working_sdf"][start : start + observations].copy()
                    prediction = np.asarray(predictor(history, max_horizon, distance_clip=8))
                    if (
                        prediction.shape != (max_horizon, 64, 64)
                        or not np.isfinite(prediction).all()
                    ):
                        raise ValueError("Predictor returned invalid shape or nonfinite values")
                    for lead in range(1, max_horizon + 1):
                        target_index = start + observations + lead - 1
                        values = region_metrics(
                            prediction[lead - 1] > 0, arrays["working_region"][target_index]
                        )
                        rows.append(
                            {
                                "baseline": baseline,
                                "sequence_id": record["sequence_id"],
                                "project_split": split,
                                "window_start": start,
                                "lead": lead,
                                "is_endpoint": lead in horizons,
                                **values,
                            }
                        )
            print(f"{record['sequence_id']}: {len(starts)}/{possible} common windows", flush=True)
        if not rows:
            raise ValueError("No valid common evaluation windows")
        summary = summarize(rows)
        summary["endpoints"] = [row for row in summary["aggregate"] if row["lead"] in horizons]
        summary["window_qc"] = qc
        save_json(output / "metrics.json", rows)
        with (output / "metrics.csv").open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        cases = failure_cases(
            rows, selected, manifest_path.parent, output, observations, max_horizon, failure_count
        )
        save_json(output / "failure-cases.json", cases)
        save_json(output / "summary.json", summary)
        metadata.update(
            {
                "status": "complete",
                "n_sequences": len(selected),
                "n_sequences_with_windows": len({row["sequence_id"] for row in rows}),
                "n_windows": sum(row["valid_windows"] for row in qc),
                "qc_excluded_windows": sum(row["qc_excluded_windows"] for row in qc),
            }
        )
        return {"metadata": metadata, "summary": summary}
    except Exception as exc:
        metadata.update({"status": "failed", "error": f"{type(exc).__name__}: {exc}"})
        raise
    finally:
        metadata["elapsed_seconds"] = round(time.monotonic() - started, 6)
        metadata["finished_utc"] = datetime.now(UTC).isoformat()
        save_json(output / "run.json", metadata)


def failure_cases(rows, records, root, output, observations, horizon, count):
    cases = []
    sequence_metrics = summarize(rows)["per_sequence"]
    for baseline, predictor in BASELINES.items():
        ranked = sorted(
            (
                row
                for row in sequence_metrics
                if row["baseline"] == baseline and row["lead"] == horizon
            ),
            key=lambda row: (row["iou"], row["sequence_id"]),
        )[:count]
        for rank in ranked:
            worst = min(
                (
                    row
                    for row in rows
                    if row["baseline"] == baseline
                    and row["sequence_id"] == rank["sequence_id"]
                    and row["lead"] == horizon
                ),
                key=lambda row: (row["iou"], row["window_start"]),
            )
            record = next(item for item in records if item["sequence_id"] == rank["sequence_id"])
            arrays = load_sequence(root, record)
            start = worst["window_start"]
            history = arrays["working_sdf"][start : start + observations].copy()
            predicted = predictor(history, horizon, distance_clip=8)[-1] > 0
            target_index = start + observations + horizon - 1
            masks = [history[-1] > 0, arrays["working_region"][target_index], predicted]
            canvas = Image.new("RGB", (768, 310), "#111820")
            draw = ImageDraw.Draw(canvas)
            draw.text(
                (12, 8),
                f"{baseline} / {record['sequence_id']} / start {start} / lead {horizon}",
                fill="white",
            )
            labels = ["HISTORY: DERIVED_ANNOTATION", "TARGET: DERIVED_ANNOTATION", "PREDICTION"]
            for column, (mask, label) in enumerate(zip(masks, labels, strict=True)):
                image = (
                    Image.fromarray(mask.astype(np.uint8) * 255)
                    .convert("RGB")
                    .resize((240, 240), Image.Resampling.NEAREST)
                )
                canvas.paste(image, (column * 256 + 8, 55))
                draw.text((column * 256 + 8, 32), label, fill="white")
            relative = f"failure-cases/{baseline}_{record['sequence_id']}.png"
            (output / relative).parent.mkdir(parents=True, exist_ok=True)
            canvas.save(output / relative)
            cases.append(
                {
                    "baseline": baseline,
                    "sequence_id": record["sequence_id"],
                    "sequence_mean_endpoint_iou": rank["iou"],
                    "window_start": start,
                    "source_target_index": target_index,
                    "lead": horizon,
                    "metrics": worst,
                    "png_relpath": relative,
                    "target_provenance": "DERIVED_ANNOTATION",
                    "prediction_provenance": "PREDICTION",
                }
            )
    return cases


def unique_output(root: Path) -> Path:
    return root / (datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ") + "_" + uuid.uuid4().hex[:8])
