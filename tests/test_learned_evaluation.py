"""SYNTHETIC only: contracts for held-out scoring, nested estimates and source gates."""

from types import SimpleNamespace

import numpy as np
import pytest
import yaml

torch = pytest.importorskip("torch")

from morpholab_ml.evaluation import learned  # noqa: E402
from morpholab_ml.evaluation.runner import METRICS, PROJECT_ROOT, file_sha256  # noqa: E402
from morpholab_ml.training.runner import MODEL_KEYS  # noqa: E402


def synthetic_arrays(frames=57):
    y, x = np.mgrid[:64, :64]
    shape = np.clip((10 - np.hypot(x - 31, y - 31)) / 8, -1, 1).astype(np.float32)
    sdf = np.repeat(shape[None], frames, axis=0)
    return {
        "working_sdf": sdf,
        "working_region": sdf > 0,
        "valid": np.ones(frames, dtype=bool),
        "source_frame_indices": np.arange(frames),
        "images_native": np.zeros((frames, 128, 128), dtype=np.uint16),
    }


def test_matched_input_lengths_share_origin_targets_and_qc():
    arrays = synthetic_arrays()
    arrays["valid"][1] = False  # Even L2 must honor the entire shared eight-frame QC block.
    versions = {
        length: learned.evaluation_windows(arrays, length, matched=True) for length in (2, 4, 8)
    }
    for length in (2, 4, 8):
        assert [w["forecast_origin"] for w in versions[length]] == [20, 32]
        assert [w["window_start"] for w in versions[length]] == [12, 24]
        for short, full in zip(versions[length], versions[8], strict=True):
            np.testing.assert_array_equal(short["history"], full["history"][-length:])
            assert short["source_history_indices"] == full["source_history_indices"][-length:]
    record = {"sequence_id": "SYNTHETIC", "project_split": "validation"}
    scored = []
    for length in (2, 4, 8):
        rows, _ = learned.score_windows(
            arrays,
            record,
            "persistence",
            None,
            lambda h: np.repeat(h[-1:], 24, axis=0),
            length,
            True,
        )
        scored.append([(r["forecast_origin"], r["source_target_index"], r["lead"]) for r in rows])
    assert scored[0] == scored[1] == scored[2]
    assert scored[0][0] == (20, 20, 1)


def summary_rows():
    rows = []
    for variant, seeds in (("nca", (17, 29, 43)), ("persistence", (None,))):
        for index, seed in enumerate(seeds):
            for sequence, count, offset in (("a", 1, 0.0), ("b", 3, 0.2)):
                for window in range(count):
                    rows.append(
                        {
                            "variant": variant,
                            "seed": seed,
                            "sequence_id": sequence,
                            "observations": 4,
                            "window_protocol": "main_L4",
                            "lead": 24,
                            "window_start": window,
                            **dict.fromkeys(METRICS, index * 0.3 + offset),
                        }
                    )
    return rows


def test_nested_mean_sample_sd_and_deterministic_semantics():
    result = learned.summarize_forecasts(summary_rows())
    nca, persistence = result["summary"]
    assert nca["n_sequences"] == 2 and nca["n_seeds"] == 3
    assert nca["n_windows"] == 4
    assert nca["metrics_mean"]["iou"] == pytest.approx(0.4)  # pooled windows would be 0.45
    assert nca["metrics_std"]["iou"] == pytest.approx(0.3)  # ddof=1 over three seed means
    assert persistence["n_seeds"] == 0 and persistence["n_realizations"] == 1
    assert persistence["metrics_std"]["iou"] is None
    assert len(result["per_sequence"]) == 8


@pytest.mark.parametrize("corruption", ["missing_seed", "duplicate", "nonfinite"])
def test_summary_rejects_incomplete_or_invalid_rows(corruption):
    rows = summary_rows()
    if corruption == "missing_seed":
        rows = [r for r in rows if r["seed"] != 43]
    elif corruption == "duplicate":
        rows.append(rows[0].copy())
    else:
        rows[0]["iou"] = float("nan")
    with pytest.raises(ValueError):
        learned.summarize_forecasts(rows)


@pytest.fixture
def matrix(tmp_path, monkeypatch):
    matrix_root = tmp_path / "matrix"
    matrix_root.mkdir()
    sha = learned.git_sha()
    source_names = (
        "training/runner.py",
        "models/forecast.py",
        "data/preparation.py",
        "evaluation/runner.py",
    )
    source_hashes = {
        f"ml/morpholab_ml/{name}": file_sha256(PROJECT_ROOT / f"ml/morpholab_ml/{name}")
        for name in source_names
    }
    registry, checkpoints = [], {}
    for variant in learned.VARIANTS:
        filename = "forecast-h1-ablation.yaml" if variant == "nca_h1" else "forecast-v1.yaml"
        config = yaml.safe_load((PROJECT_ROOT / f"ml/configs/{filename}").read_text())
        for seed in learned.SEEDS:
            run_id = f"{variant}_seed{seed}"
            directory = matrix_root / run_id
            directory.mkdir()
            (directory / "best.pt").write_bytes(b"SYNTHETIC placeholder; loader stubbed")
            weight_sha = file_sha256(directory / "best.pt")
            signature = {
                "model_kind": "nca" if variant == "nca_h1" else variant,
                "model_config": {key: config[key] for key in MODEL_KEYS},
                "config": config,
                "seed": seed,
                "batch_size": 8,
                "manifest_sha256": "synthetic",
                "source_hashes": source_hashes,
            }
            metadata = {
                **signature,
                "run_id": run_id,
                "status": "complete",
                "git_dirty": False,
                "git_sha": sha,
                "completed_steps": 600,
                "target_steps": 600,
                "test_arrays_loaded": False,
                "validation_selection": "supervised loss; windows then equal sequence weights",
                "best_step": 100,
                "best_validation_loss": 0.1,
                "checkpoint_sha256": {"best.pt": weight_sha},
            }
            learned.save_json(directory / "run.json", metadata)
            history = [
                {"step": step, **({"validation_loss": step / 1000} if step % 100 == 0 else {})}
                for step in range(1, 601)
            ]
            learned.save_json(directory / "history.json", history)
            registry.append({**metadata, "variant": variant})
            checkpoints[str(directory / "best.pt")] = {
                **signature,
                "signature": signature,
                "git_sha": sha,
                "git_dirty": False,
                "step": 100,
                "best_step": 100,
                "best_loss": 0.1,
            }
    learned.save_json(
        matrix_root / "matrix.json", {"status": "complete", "expected_runs": 12, "runs": registry}
    )
    monkeypatch.setattr(learned, "read_checkpoint", lambda path, expected: checkpoints[str(path)])
    return matrix_root


def test_matrix_checks_all_twelve_configs_selection_and_hashes(matrix):
    runs = learned.checked_matrix(matrix, "synthetic")
    assert {(r["variant"], r["seed"]) for r in runs} == {
        (variant, seed) for variant in learned.VARIANTS for seed in learned.SEEDS
    }
    assert (
        next(r for r in runs if r["variant"] == "nca_h1")["metadata"]["config"]["train_horizon"]
        == 1
    )
    (matrix / "nca_seed17" / "best.pt").write_bytes(b"tampered")
    with pytest.raises(ValueError, match="SHA256 mismatch"):
        learned.checked_matrix(matrix, "synthetic")


def test_matrix_rejects_nonvalidation_selection_and_incomplete_registry(matrix):
    path = matrix / "nca_seed17" / "history.json"
    history = learned.read_json(path)
    history[199]["validation_loss"] = 0.01
    learned.save_json(path, history)
    with pytest.raises(ValueError, match="not selected by validation"):
        learned.checked_matrix(matrix, "synthetic")
    registry = learned.read_json(matrix / "matrix.json")
    registry["status"] = "running"
    learned.save_json(matrix / "matrix.json", registry)
    with pytest.raises(ValueError, match="not complete"):
        learned.checked_matrix(matrix, "synthetic")


def test_nonfinite_forecast_is_failed_and_only_selected_arrays_open(tmp_path, monkeypatch):
    manifest = tmp_path / "manifest.json"
    manifest.write_text("{}")
    records = [
        {"sequence_id": str(i), "project_split": "validation" if i == 0 else "test"}
        for i in range(62)
    ]
    opened = []
    monkeypatch.setattr(learned, "git_dirty", lambda: False)
    monkeypatch.setattr(learned, "git_sha", lambda: "synthetic")
    monkeypatch.setattr(learned, "read_manifest", lambda _: {"sequences": records})
    monkeypatch.setattr(learned, "verify_source", lambda *args: None)
    monkeypatch.setattr(
        learned,
        "checked_matrix",
        lambda *args: [
            {
                "variant": "nca",
                "seed": 17,
                "weight_path": tmp_path / "unused.pt",
                "best_sha256": "synthetic",
                "metadata": {"parameter_count": 0},
            }
        ],
    )

    def load(root, record):
        opened.append(record["project_split"])
        assert record["project_split"] == "validation"
        return synthetic_arrays()

    class Nonfinite(torch.nn.Module):
        def forward(self, history, horizon):
            assert history.shape == (1, 4, 64, 64)  # Only history, never future targets.
            return SimpleNamespace(predictions=torch.full((1, horizon, 64, 64), float("nan")))

    monkeypatch.setattr(learned, "load_sequence", load)
    monkeypatch.setattr(learned, "load_forecaster", lambda *args: Nonfinite())
    destination = tmp_path / "failed"
    with pytest.raises(ValueError, match="Nonfinite"):
        learned.evaluate_models(manifest, tmp_path / "matrix", destination, device="cpu")
    state = learned.read_json(destination / "run.json")
    assert state["status"] == "failed" and state["active_seed"] == 17
    assert state["active_variant"] == "nca" and state["error_type"] == "ValueError"
    assert opened == ["validation"]
    assert not (destination / "report.json").exists()


def test_synthetic_complete_evaluation_and_report_roundtrip(tmp_path, monkeypatch):
    from scripts import report_forecasts

    torch.set_num_threads(1)
    manifest = tmp_path / "manifest.json"
    manifest.write_text("{}")
    records = [
        {"sequence_id": str(i), "project_split": "validation" if i == 0 else "test"}
        for i in range(62)
    ]
    opened = []
    metadata = {
        "git_sha": "synthetic",
        "git_dirty": False,
        "config": {},
        "model_kind": "nca",
        "model_config": {},
        "source_hashes": {},
        "parameter_count": 0,
        "best_step": 100,
        "completed_steps": 600,
        "best_validation_loss": 0.1,
        "elapsed_seconds": 1,
        "cuda_peak_allocated_bytes": None,
        "cpu_peak_memory_bytes": None,
        "versions": {"torch": "synthetic"},
        "device": "cpu",
        "precision": "fp32",
    }
    runs = [
        {
            "variant": variant,
            "seed": seed,
            "weight_path": tmp_path / "unused.pt",
            "best_sha256": "synthetic",
            "metadata": metadata,
            "run_json_sha256": "synthetic",
            "history_sha256": "synthetic",
        }
        for variant in learned.VARIANTS
        for seed in learned.SEEDS
    ]
    matrix_root = tmp_path / "matrix"
    matrix_root.mkdir()
    (matrix_root / "matrix.json").write_text('{"synthetic":true}')
    monkeypatch.setattr(learned, "git_dirty", lambda: False)
    monkeypatch.setattr(learned, "git_sha", lambda: "synthetic")
    monkeypatch.setattr(
        learned,
        "read_manifest",
        lambda _: {"sequences": records, "protocol": "SYNTHETIC", "source_archive": {}},
    )
    monkeypatch.setattr(learned, "verify_source", lambda *args: None)
    monkeypatch.setattr(learned, "checked_matrix", lambda *args: runs)

    def load(root, record):
        opened.append(record["project_split"])
        assert record["project_split"] == "validation"
        return synthetic_arrays(33)

    class Persistence(torch.nn.Module):
        def forward(self, history, horizon):
            assert history.shape[1] in (2, 4, 8)
            return SimpleNamespace(predictions=history[:, -1:].repeat(1, horizon, 1, 1))

    monkeypatch.setattr(learned, "load_sequence", load)
    monkeypatch.setattr(learned, "load_forecaster", lambda *args: Persistence())
    destination = tmp_path / "complete"
    result = learned.evaluate_models(manifest, matrix_root, destination, device="cpu")
    assert learned.read_json(destination / "run.json")["status"] == "complete"
    assert len(result["summary"]) == 6 * 24
    assert len(result["input_sensitivity"]) == 6 * 3 * 24
    assert len(result["runs"]) == 12
    assert len(result["failure_cases"]) == 6
    assert result["evaluation_environment"]["matmul_fp32_precision"] == "ieee"
    assert result["evaluation_environment"]["convolution_fp32_precision"] == "ieee"
    assert result["evaluation_environment"]["deterministic_algorithms"] is True
    assert result["evaluation_environment"]["cudnn_benchmark"] is False
    assert result["evaluation_environment"]["cpu_threads"] == 1
    assert result["evaluation_environment"]["cublas_workspace_config"] in (":4096:8", ":16:8")
    assert opened == ["validation"]
    monkeypatch.setattr(report_forecasts, "verify_source", lambda *args: None)
    public = report_forecasts.checked_report(destination)
    assert public["summary"] == result["summary"]
    assert public["source_evaluation_files_sha256"]["report.json"] == file_sha256(
        destination / "report.json"
    )
    with (destination / "metrics.json").open("a") as stream:
        stream.write(" ")
    with pytest.raises(ValueError, match="source hash mismatch"):
        report_forecasts.checked_report(destination)
