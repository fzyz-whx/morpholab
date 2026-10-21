"""Matrix orchestration fixtures; no real model is trained by these tests."""

import json
import sys

import pytest
from morpholab_ml.evaluation import runner as evaluation

from scripts import train_matrix

pytest.importorskip("torch")
from morpholab_ml.training import runner as training  # noqa: E402


@pytest.fixture
def matrix_fixture(monkeypatch, tmp_path):
    output = tmp_path / "matrix"
    monkeypatch.setattr(sys, "argv", ["train_matrix", "--output", str(output)])
    monkeypatch.setattr(evaluation, "git_dirty", lambda: False)
    monkeypatch.setattr(evaluation, "read_manifest", lambda _: {"sequences": [None] * 62})
    monkeypatch.setattr(training, "load_config", lambda _: {"seeds": [17, 29, 43]})
    calls = []

    def fake_train(manifest, destination, **kwargs):
        calls.append((destination.name, kwargs))
        return {
            "run_id": destination.name,
            "status": "complete",
            "git_sha": "a" * 40,
            "git_dirty": False,
            "completed_steps": 600,
            "best_step": 500,
            "best_validation_loss": 0.1,
            "elapsed_seconds": 1,
            "cuda_peak_allocated_bytes": None,
            "checkpoint_sha256": {"best.pt": "b" * 64},
        }

    monkeypatch.setattr(training, "train", fake_train)
    return output, calls


def test_matrix_keeps_all_variants_and_seeds(matrix_fixture):
    output, calls = matrix_fixture
    assert train_matrix.main() == 0
    result = json.loads((output / "matrix.json").read_text())
    assert result["status"] == "complete"
    assert len(result["runs"]) == len(calls) == 12
    assert calls[-1][0] == "nca_h1_seed43"
    assert calls[-1][1]["model_kind"] == "nca"
    assert {r["variant"] for r in result["runs"]} == {"nca", "nca_regularized", "convgru", "nca_h1"}


def test_matrix_refuses_existing_directory(matrix_fixture):
    output, calls = matrix_fixture
    output.mkdir()
    with pytest.raises(ValueError, match="must not exist"):
        train_matrix.main()
    assert not calls


def test_matrix_stops_before_next_run_when_source_changes(matrix_fixture, monkeypatch):
    output, calls = matrix_fixture
    checks = iter([False, False, True])
    monkeypatch.setattr(evaluation, "git_dirty", lambda: next(checks))
    with pytest.raises(ValueError, match="Source changed"):
        train_matrix.main()
    result = json.loads((output / "matrix.json").read_text())
    assert result["status"] == "failed"
    assert len(calls) == len(result["runs"]) == 1
