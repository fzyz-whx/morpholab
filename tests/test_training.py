"""SYNTHETIC fixtures verify mechanics; these are not real-data training acceptance."""

import copy
import json
from pathlib import Path

import numpy as np
import pytest

torch = pytest.importorskip("torch")

from morpholab_ml.training import runner  # noqa: E402


@pytest.fixture
def synthetic(tmp_path, monkeypatch):
    torch.set_num_threads(1)
    config = runner.load_config(Path("ml/configs/forecast-v1.yaml"))
    config.update(
        state_channels=4,
        hidden_channels=4,
        observations=2,
        train_horizon=2,
        evaluation_horizons=[2],
        evaluation_stride=2,
        validation_interval=2,
        batch_size=1,
    )
    manifest = tmp_path / "manifest.json"
    manifest.write_text('{"synthetic": true}', encoding="utf-8")
    records = [{"sequence_id": s, "project_split": s} for s in ("train", "validation", "test")]
    monkeypatch.setattr(runner, "read_manifest", lambda _: {"sequences": records})
    opened = []

    def load(root, record):
        opened.append(record["project_split"])
        assert record["project_split"] != "test", "test array must never be opened"
        y, x = np.mgrid[:8, :8]
        sdf = np.stack(
            [
                np.clip((3 - (x - 3.5) ** 2 / 3 - (y - 3.5) ** 2 / 3) * 0.1 - i * 0.01, -1, 1)
                for i in range(8)
            ]
        ).astype("float32")
        return {"working_sdf": sdf, "valid": np.ones(8, dtype=bool)}

    monkeypatch.setattr(runner, "load_sequence", load)
    return manifest, config, opened


@pytest.mark.parametrize("kind", ["nca", "nca_regularized", "convgru"])
def test_checkpoint_and_resume_equal_uninterrupted(synthetic, tmp_path, kind):
    manifest, config, opened = synthetic
    uninterrupted, resumed = tmp_path / "whole", tmp_path / "resume"
    runner.train(manifest, uninterrupted, config=config, model_kind=kind, steps=3, device="cpu")
    runner.train(manifest, resumed, config=config, model_kind=kind, steps=1, device="cpu")
    result = runner.train(
        manifest,
        resumed,
        config=config,
        model_kind=kind,
        steps=3,
        device="cpu",
        resume=resumed / "last.pt",
    )
    assert result["completed_steps"] == 3
    assert result["best_step"] == 2
    assert result["status"] == "budget_limited"
    assert "test" not in opened
    a, b = [runner.read_checkpoint(p / "last.pt") for p in (uninterrupted, resumed)]
    assert a["sampler_rng"] == b["sampler_rng"]
    for name, value in a["model_state"].items():
        assert torch.equal(value, b["model_state"][name])
    for left, right in zip(a["history"], b["history"], strict=True):
        assert left["loss"] == right["loss"]
        expected = left["supervised_loss"]
        if kind == "nca_regularized":
            expected += config["loss"]["nca_update_penalty"] * left["update_penalty"]
        assert left["loss"] == pytest.approx(expected)
    model = runner.load_forecaster(
        resumed / "best.pt", expected_sha256=runner.file_sha256(resumed / "best.pt")
    )
    assert model(torch.zeros(1, 2, 8, 8), 2).predictions.shape == (1, 2, 8, 8)
    with pytest.raises(ValueError, match="SHA256"):
        runner.load_forecaster(resumed / "best.pt", expected_sha256="0" * 64)
    metadata = json.loads((resumed / "run.json").read_text())
    assert metadata["test_arrays_loaded"] is False
    assert metadata["checkpoint_sha256"]["last.pt"] == runner.file_sha256(resumed / "last.pt")
    assert b["git_sha"] == metadata["git_sha"]
    assert b["run_id"] == metadata["run_id"]
    assert b["started_utc"] == metadata["started_utc"]
    assert metadata["cpu_threads"] >= 1


def test_initial_checkpoint_and_resume_mismatch(synthetic, tmp_path):
    manifest, config, _ = synthetic
    output = tmp_path / "initial"
    runner.train(manifest, output, config=config, steps=0, device="cpu")
    assert runner.read_checkpoint(output / "last.pt")["step"] == 0
    changed = copy.deepcopy(config)
    changed["learning_rate"] = 0.001
    with pytest.raises(ValueError, match="Resume"):
        runner.train(
            manifest, output, config=changed, steps=1, device="cpu", resume=output / "last.pt"
        )


def test_nonfinite_fails_and_preserves_valid_checkpoint(synthetic, tmp_path, monkeypatch):
    manifest, config, _ = synthetic
    original = runner.sample_batch

    def corrupt(*args, **kwargs):
        history, future = original(*args, **kwargs)
        future.fill_(float("nan"))
        return history, future

    monkeypatch.setattr(runner, "sample_batch", corrupt)
    output = tmp_path / "failed"
    with pytest.raises(ValueError, match="Nonfinite"):
        runner.train(manifest, output, config=config, steps=2, device="cpu")
    assert runner.read_checkpoint(output / "last.pt")["step"] == 0
    failed = json.loads((output / "run.json").read_text())
    assert failed["status"] == "failed"
    assert "Nonfinite" in failed["failure_reason"]


def test_unknown_config_and_checkpoint_rejected(synthetic, tmp_path):
    _, config, _ = synthetic
    config["arbitrary"] = True
    with pytest.raises(ValueError, match="configuration keys"):
        runner.validate_config(config)
    path = tmp_path / "unknown.pt"
    torch.save(
        {"schema": runner.CHECKPOINT_SCHEMA, "model_kind": "nca", "model_config": {"unknown": 1}},
        path,
    )
    with pytest.raises(ValueError, match="model configuration"):
        runner.load_forecaster(path)


def test_loss_formula_and_sampler_alignment():
    config = runner.load_config(Path("ml/configs/forecast-v1.yaml"))["loss"]
    prediction = torch.zeros(1, 1, 2, 2)
    target = torch.ones_like(prediction) * 0.5
    expected = (1 + 4 * np.exp(-2)) * 0.25 + 0.1 * (1 - (4 + 1e-6) / (6 + 1e-6))
    assert runner.supervised_loss(prediction, target, config).item() == pytest.approx(expected)
    frames = np.arange(8 * 4 * 4, dtype=np.float32).reshape(8, 4, 4)
    sequences = [{"sdf": frames, "starts": [0, 1]}]
    a = runner.sample_batch(sequences, np.random.default_rng(17), 3, 2, 2, torch.device("cpu"))
    b = runner.sample_batch(sequences, np.random.default_rng(17), 3, 2, 2, torch.device("cpu"))
    assert all(torch.equal(x, y) for x, y in zip(a, b, strict=True))
    assert torch.equal(a[1][:, 0] - a[0][:, 0], torch.full_like(a[1][:, 0], 32))
