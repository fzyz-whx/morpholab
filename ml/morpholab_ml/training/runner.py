"""Frozen ADR-0002 training, safe checkpoints and held-out validation selection."""

from __future__ import annotations

import importlib.metadata
import json
import os
import platform
import time
import warnings
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import yaml

from morpholab_ml.data.preparation import window_starts
from morpholab_ml.evaluation.runner import (
    PROJECT_ROOT,
    file_sha256,
    git_dirty,
    git_sha,
    load_sequence,
    read_manifest,
)

try:
    import torch
except ImportError as exc:
    raise ImportError("Training requires PyTorch: run uv sync --extra cpu") from exc

from morpholab_ml.models.forecast import build_model

MODEL_KEYS = ("state_channels", "hidden_channels", "step_size", "state_limit", "fire_rate")
KINDS = {"nca", "nca_regularized", "convgru"}
CHECKPOINT_SCHEMA = "morpholab-training-v1"


def atomic_json(path: Path, value: Any) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8"
    )
    os.replace(temporary, path)


def atomic_checkpoint(path: Path, value: dict[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    torch.save(value, temporary)
    os.replace(temporary, path)


def load_config(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("Training configuration must be a mapping")
    validate_config(value)
    return value


def validate_config(config: dict[str, Any]) -> None:
    required = {
        "protocol",
        "data_protocol",
        "observations",
        "train_horizon",
        "evaluation_horizons",
        "evaluation_stride",
        "seeds",
        "models",
        "state_channels",
        "hidden_channels",
        "step_size",
        "state_limit",
        "fire_rate",
        "maximum_steps",
        "batch_size",
        "learning_rate",
        "gradient_clip",
        "validation_interval",
        "training_augmentation",
        "loss",
        "precision",
    }
    if set(config) != required:
        raise ValueError("Unknown or missing training configuration keys")
    if (
        config["protocol"] != "morpholab-forecast-v1"
        or config["data_protocol"] != "morpholab-split-v1"
        or config["precision"] != "fp32"
        or config["training_augmentation"] != "rotate90_and_flip"
    ):
        raise ValueError("Unknown training protocol, precision or augmentation")
    for key in (
        "observations",
        "train_horizon",
        "evaluation_stride",
        "state_channels",
        "hidden_channels",
        "maximum_steps",
        "batch_size",
        "validation_interval",
    ):
        if type(config[key]) is not int or config[key] <= 0:
            raise ValueError(f"Invalid positive integer: {key}")
    if config["maximum_steps"] > 600 or config["observations"] < 2:
        raise ValueError("ADR-0002 permits at most 600 optimization steps and L>=2")
    if (
        not isinstance(config["evaluation_horizons"], list)
        or not config["evaluation_horizons"]
        or any(type(h) is not int or h <= 0 for h in config["evaluation_horizons"])
    ):
        raise ValueError("Invalid evaluation horizons")
    for key in ("step_size", "state_limit", "fire_rate", "learning_rate", "gradient_clip"):
        if (
            type(config[key]) not in (int, float)
            or not np.isfinite(config[key])
            or config[key] <= 0
        ):
            raise ValueError(f"Invalid positive finite value: {key}")
    if (
        not isinstance(config["models"], list)
        or set(config["models"]) != KINDS
        or len(config["models"]) != len(KINDS)
        or not isinstance(config["seeds"], list)
        or not config["seeds"]
        or any(type(s) is not int or s < 0 for s in config["seeds"])
        or len(config["seeds"]) != len(set(config["seeds"]))
    ):
        raise ValueError("Unknown models or invalid seeds")
    loss = config["loss"]
    if (
        not isinstance(loss, dict)
        or set(loss)
        != {
            "sdf_weight",
            "boundary_weight",
            "boundary_decay",
            "soft_region_scale",
            "dice_weight",
            "nca_update_penalty",
        }
        or any(type(v) not in (int, float) or not np.isfinite(v) or v < 0 for v in loss.values())
    ):
        raise ValueError("Invalid loss configuration")


def resolve_device(requested: str) -> torch.device:
    if requested == "auto":
        requested = "cuda" if torch.cuda.is_available() else "cpu"
        if requested == "cpu":
            warnings.warn("CUDA unavailable; training uses CPU (slower).", stacklevel=2)
    elif requested.startswith("cuda") and not torch.cuda.is_available():
        warnings.warn("Requested CUDA unavailable; falling back to CPU.", stacklevel=2)
        requested = "cpu"
    device = torch.device(requested)
    if device.type not in {"cpu", "cuda"}:
        raise ValueError("Only CPU and CUDA are supported")
    return device


def supervised_loss(
    prediction: torch.Tensor, target: torch.Tensor, config: dict[str, Any]
) -> torch.Tensor:
    if prediction.shape != target.shape or not torch.isfinite(prediction).all():
        raise ValueError("Prediction shape mismatch or nonfinite prediction")
    if not torch.isfinite(target).all():
        raise ValueError("Nonfinite training target")
    weight = 1 + config["boundary_weight"] * torch.exp(-config["boundary_decay"] * target.abs())
    mse = (weight * (prediction - target).square()).mean()
    probability = torch.sigmoid(config["soft_region_scale"] * prediction)
    region = (target > 0).to(prediction.dtype)
    dims = (-2, -1)
    dice = (
        1
        - (
            (2 * (probability * region).sum(dims) + 1e-6)
            / (probability.sum(dims) + region.sum(dims) + 1e-6)
        ).mean()
    )
    return config["sdf_weight"] * mse + config["dice_weight"] * dice


def training_data(manifest_path: Path, config: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    manifest = read_manifest(manifest_path)
    result: dict[str, list[dict[str, Any]]] = {"train": [], "validation": []}
    for record in manifest["sequences"]:
        split = record["project_split"]
        if split not in result:
            continue  # Never open test NPZs, including during resume or checkpoint selection.
        arrays = load_sequence(manifest_path.parent, record)
        horizon = (
            config["train_horizon"] if split == "train" else max(config["evaluation_horizons"])
        )
        stride = 1 if split == "train" else config["evaluation_stride"]
        starts = window_starts(arrays["valid"], config["observations"], horizon, stride)
        if starts:
            result[split].append(
                {"id": record["sequence_id"], "sdf": arrays["working_sdf"], "starts": starts}
            )
    if not all(result.values()):
        raise ValueError("Both train and validation require valid windows")
    return result


def sample_batch(
    sequences: list[dict[str, Any]],
    rng: np.random.Generator,
    batch_size: int,
    observations: int,
    horizon: int,
    device: torch.device,
) -> tuple[torch.Tensor, torch.Tensor]:
    samples = []
    for _ in range(batch_size):
        sequence = sequences[int(rng.integers(len(sequences)))]
        start = sequence["starts"][int(rng.integers(len(sequence["starts"])))]
        sample = sequence["sdf"][start : start + observations + horizon]
        sample = np.rot90(sample, int(rng.integers(4)), axes=(-2, -1))
        if rng.integers(2):
            sample = np.flip(sample, axis=-1)
        if rng.integers(2):
            sample = np.flip(sample, axis=-2)
        samples.append(sample.copy())
    batch = torch.as_tensor(np.stack(samples), device=device, dtype=torch.float32)
    return batch[:, :observations], batch[:, observations:]


def validation_loss(
    model: torch.nn.Module,
    sequences: list[dict[str, Any]],
    config: dict[str, Any],
    device: torch.device,
) -> float:
    model.eval()
    means = []
    length, horizon = config["observations"], max(config["evaluation_horizons"])
    with torch.no_grad():
        for sequence in sequences:
            losses = []
            for start in sequence["starts"]:
                clip = torch.as_tensor(
                    sequence["sdf"][start : start + length + horizon].copy(),
                    device=device,
                    dtype=torch.float32,
                ).unsqueeze(0)
                output = model(clip[:, :length], horizon)
                losses.append(
                    float(
                        supervised_loss(output.predictions, clip[:, length:], config["loss"]).item()
                    )
                )
            means.append(float(np.mean(losses)))
    model.train()
    value = float(np.mean(means))
    if not np.isfinite(value):
        raise ValueError("Nonfinite validation loss")
    return value


def read_checkpoint(path: Path, expected_sha256: str | None = None) -> dict[str, Any]:
    if expected_sha256 is not None and file_sha256(path) != expected_sha256:
        raise ValueError("Checkpoint SHA256 mismatch")
    # Never permit a fallback to arbitrary pickle execution.
    value = torch.load(path, map_location="cpu", weights_only=True)
    if not isinstance(value, dict) or value.get("schema") != CHECKPOINT_SCHEMA:
        raise ValueError("Unknown checkpoint schema")
    if value.get("model_kind") not in KINDS or set(value.get("model_config", {})) != set(
        MODEL_KEYS
    ):
        raise ValueError("Unknown checkpoint model or model configuration")
    return value


def load_forecaster(
    path: Path | str, device: str = "cpu", expected_sha256: str | None = None
) -> torch.nn.Module:
    checkpoint = read_checkpoint(Path(path), expected_sha256)
    model = build_model(checkpoint["model_kind"], checkpoint["model_config"])
    model.load_state_dict(checkpoint["model_state"], strict=True)
    for parameter in model.parameters():
        if not torch.isfinite(parameter).all():
            raise ValueError("Nonfinite checkpoint parameter")
    model.to(resolve_device(device)).eval()
    return model


def source_hashes() -> dict[str, str]:
    paths = [
        "ml/morpholab_ml/training/runner.py",
        "ml/morpholab_ml/models/forecast.py",
        "ml/morpholab_ml/data/preparation.py",
        "ml/morpholab_ml/evaluation/runner.py",
    ]
    return {name: file_sha256(PROJECT_ROOT / name) for name in paths}


def train(
    manifest_path: Path,
    output: Path,
    *,
    model_kind: str = "nca",
    seed: int = 17,
    config: dict[str, Any],
    steps: int | None = None,
    batch_size: int | None = None,
    device: str = "auto",
    resume: Path | None = None,
) -> dict[str, Any]:
    """Run actual optimization; steps is a total target, not additional resume steps."""
    started = time.monotonic()
    started_utc = datetime.now(UTC).isoformat()
    validate_config(config)
    if model_kind not in KINDS or type(seed) is not int or seed not in config["seeds"]:
        raise ValueError("Invalid model or seed")
    steps = config["maximum_steps"] if steps is None else steps
    batch_size = config["batch_size"] if batch_size is None else batch_size
    if type(steps) is not int or not 0 <= steps <= config["maximum_steps"]:
        raise ValueError("Steps must lie within the configured fixed budget")
    if type(batch_size) is not int or batch_size <= 0:
        raise ValueError("Batch size must be positive")
    checkpoint = read_checkpoint(resume) if resume else None
    if (
        output.exists()
        and any(output.iterdir())
        and not (resume and resume.parent.resolve() == output.resolve())
    ):
        raise ValueError("Training output must be new or empty, unless resuming that run")
    output.mkdir(parents=True, exist_ok=True)
    selected_device = resolve_device(device)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.use_deterministic_algorithms(True)
    torch.backends.cuda.matmul.fp32_precision = "ieee"
    torch.backends.cudnn.conv.fp32_precision = "ieee"
    if torch.backends.cudnn.is_available():
        torch.backends.cudnn.benchmark = False
    rng = np.random.default_rng(seed)
    model_config = {key: config[key] for key in MODEL_KEYS}
    signature = {
        "model_kind": model_kind,
        "model_config": model_config,
        "config": config,
        "seed": seed,
        "batch_size": batch_size,
        "manifest_sha256": file_sha256(manifest_path),
        "source_hashes": source_hashes(),
    }
    if checkpoint and checkpoint["signature"] != signature:
        raise ValueError("Resume data, source, model, seed or training configuration mismatch")
    data = training_data(manifest_path, config)
    model = build_model(model_kind, model_config).to(selected_device)
    optimizer = torch.optim.Adam(model.parameters(), lr=config["learning_rate"])
    history: list[dict[str, Any]] = []
    step, best_loss, best_step, previous_seconds = 0, None, None, 0.0
    if checkpoint:
        step = checkpoint["step"]
        if steps < step:
            raise ValueError("Resume target steps precede saved step")
        model.load_state_dict(checkpoint["model_state"], strict=True)
        optimizer.load_state_dict(checkpoint["optimizer_state"])
        rng.bit_generator.state = checkpoint["sampler_rng"]
        torch.set_rng_state(checkpoint["torch_rng"])
        if selected_device.type == "cuda" and checkpoint["cuda_rng"]:
            torch.cuda.set_rng_state_all(checkpoint["cuda_rng"])
        history = checkpoint["history"]
        best_loss, best_step = checkpoint["best_loss"], checkpoint["best_step"]
        previous_seconds = checkpoint["elapsed_seconds"]
        if best_step is not None and not (output / "best.pt").is_file():
            raise ValueError("Resume requires the original run directory containing best.pt")
    if selected_device.type == "cuda":
        torch.cuda.reset_peak_memory_stats(selected_device)
    metadata = {
        "schema": CHECKPOINT_SCHEMA,
        "run_id": output.name,
        "status": "running",
        **signature,
        "git_sha": git_sha(),
        "git_dirty": git_dirty(),
        "device": str(selected_device),
        "precision": "fp32",
        "matmul_fp32_precision": torch.backends.cuda.matmul.fp32_precision,
        "convolution_fp32_precision": torch.backends.cudnn.conv.fp32_precision,
        "target_steps": steps,
        "started_utc": checkpoint.get("started_utc", started_utc) if checkpoint else started_utc,
        "attempt_started_utc": started_utc,
        "resume_from_step": step,
        "parameter_count": sum(p.numel() for p in model.parameters()),
        "versions": {
            "python": platform.python_version(),
            "torch": str(torch.__version__),
            "numpy": importlib.metadata.version("numpy"),
            "cuda_runtime": torch.version.cuda,
            "cudnn": torch.backends.cudnn.version(),
        },
        "device_name": (
            torch.cuda.get_device_name(selected_device) if selected_device.type == "cuda" else "CPU"
        ),
        "deterministic_algorithms": True,
        "cpu_threads": torch.get_num_threads(),
        "validation_selection": "supervised loss; windows then equal sequence weights",
        "test_arrays_loaded": False,
        "eligible_sequences": {split: len(sequences) for split, sequences in data.items()},
        "eligible_windows": {
            split: sum(len(sequence["starts"]) for sequence in sequences)
            for split, sequences in data.items()
        },
        "sampling": "uniform eligible train sequence, then uniform valid stride-1 window",
        "cpu_peak_memory_bytes": None,
        "cpu_memory_note": "CPU tensor peak memory is not measured by the PyTorch CUDA allocator",
        "completed_steps": step,
    }

    def elapsed() -> float:
        return previous_seconds + time.monotonic() - started

    def save_state(name: str) -> None:
        atomic_checkpoint(
            output / name,
            {
                "schema": CHECKPOINT_SCHEMA,
                "run_id": metadata["run_id"],
                "git_sha": metadata["git_sha"],
                "git_dirty": metadata["git_dirty"],
                "started_utc": metadata["started_utc"],
                **signature,
                "signature": signature,
                "step": step,
                "model_state": model.state_dict(),
                "optimizer_state": optimizer.state_dict(),
                "sampler_rng": rng.bit_generator.state,
                "torch_rng": torch.get_rng_state(),
                "cuda_rng": torch.cuda.get_rng_state_all() if torch.cuda.is_available() else [],
                "history": history,
                "best_loss": best_loss,
                "best_step": best_step,
                "elapsed_seconds": elapsed(),
            },
        )

    def progress() -> None:
        metadata.update(
            completed_steps=step,
            best_step=best_step,
            best_validation_loss=best_loss,
            elapsed_seconds=elapsed(),
            cuda_peak_allocated_bytes=(
                torch.cuda.max_memory_allocated(selected_device)
                if selected_device.type == "cuda"
                else None
            ),
        )
        metadata["checkpoint_sha256"] = {
            name: file_sha256(output / name)
            for name in ("last.pt", "best.pt")
            if (output / name).is_file()
        }
        atomic_json(output / "history.json", history)
        atomic_json(output / "run.json", metadata)

    save_state("last.pt")  # An initial checkpoint also makes a zero-step smoke resumable.
    progress()
    try:
        model.train()
        while step < steps:
            inputs, targets = sample_batch(
                data["train"],
                rng,
                batch_size,
                config["observations"],
                config["train_horizon"],
                selected_device,
            )
            optimizer.zero_grad(set_to_none=True)
            prediction = model(inputs, config["train_horizon"])
            supervised = supervised_loss(prediction.predictions, targets, config["loss"])
            penalty = prediction.update_penalty
            if penalty.ndim != 0 or not torch.isfinite(penalty):
                raise ValueError("Nonfinite or nonscalar model update penalty")
            loss = supervised
            if model_kind == "nca_regularized":
                loss = loss + config["loss"]["nca_update_penalty"] * penalty
            if not torch.isfinite(loss):
                raise ValueError("Nonfinite training loss")
            loss.backward()
            gradient_norm = torch.nn.utils.clip_grad_norm_(
                model.parameters(), config["gradient_clip"], error_if_nonfinite=True
            )
            optimizer.step()
            if any(not torch.isfinite(p).all() for p in model.parameters()):
                raise ValueError("Nonfinite model parameter after optimization")
            step += 1
            row = {
                "step": step,
                "loss": float(loss.item()),
                "supervised_loss": float(supervised.item()),
                "update_penalty": float(penalty.item()),
                "gradient_norm_before_clip": float(gradient_norm.item()),
                "elapsed_seconds": elapsed(),
            }
            if step % config["validation_interval"] == 0:
                value = validation_loss(model, data["validation"], config, selected_device)
                row["validation_loss"] = value
                if best_loss is None or value < best_loss:
                    best_loss, best_step = value, step
                    row["selected_best"] = True
            history.append(row)
            if row.get("selected_best"):
                save_state("best.pt")
            save_state("last.pt")
            progress()
        metadata["status"] = "complete" if steps == config["maximum_steps"] else "budget_limited"
        return metadata
    except BaseException as exc:
        metadata["status"] = "interrupted" if isinstance(exc, KeyboardInterrupt) else "failed"
        metadata["error_type"] = type(exc).__name__
        metadata["failure_reason"] = str(exc)[:2000] or "Interrupted by operator"
        raise
    finally:
        metadata["finished_utc"] = datetime.now(UTC).isoformat()
        progress()
