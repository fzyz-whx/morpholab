"""SYNTHETIC fixtures: persistent job mechanics, never real-data E2E acceptance."""

import json

import numpy as np
import pytest
from fastapi.testclient import TestClient
from morpholab_ml.evaluation.runner import file_sha256

from backend.app import prediction
from backend.app.data import PRIMARY_DATASET
from backend.app.jobs import JobQueue, WorkerLock
from backend.app.main import create_app
from backend.app.worker import deterministic_cpu, execute_one


@pytest.fixture
def prepared(tmp_path, monkeypatch):
    deterministic_cpu()
    artifacts = tmp_path / "source"
    manifest_path = artifacts / "processed/manifest.json"
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text('{"provenance":"SYNTHETIC"}', encoding="utf-8")
    y, x = np.mgrid[:64, :64]
    sdf = np.stack(
        [np.clip((15 - np.hypot(x - 31, y - 31) - i * 0.1) / 8, -1, 1) for i in range(8)]
    ).astype(np.float32)
    valid = np.ones(8, dtype=bool)
    valid[6] = False
    arrays = {"working_sdf": sdf, "working_region": sdf > 0, "valid": valid}
    manifest = {
        "source_archive": {"source_id": "synthetic", "sha256": "a" * 64},
        "sequences": [
            {
                "sequence_id": "WH01",
                "project_split": "test",
                "frame_count": 8,
                "invalid_frame_indices": [6],
                "output_file_sha256": "b" * 64,
            }
        ],
    }
    monkeypatch.setattr(prediction, "read_manifest", lambda _: manifest)
    monkeypatch.setattr(prediction, "load_sequence", lambda *_: arrays)
    app = create_app(tmp_path, artifacts_root=artifacts)
    return tmp_path, artifacts, app, TestClient(app), arrays


def payload(**changes):
    return {
        "dataset_id": PRIMARY_DATASET,
        "sequence_id": "WH01",
        "model_id": "persistence",
        "observation_start": 1,
        "observations": 4,
        "horizon": 3,
    } | changes


def submit(client, **changes):
    response = client.post("/api/v1/experiments/predict", json=payload(**changes))
    assert response.status_code == 202, response.text
    return response.json()["job"]


def test_persisted_queue_worker_result_and_future_qc(prepared):
    root, artifacts, app, client, _ = prepared
    job = submit(client)
    assert job["status"] == "queued"
    assert client.get(f"/api/v1/jobs/{job['id']}/result").status_code == 409
    # A second API instance sees the same job; API routes have not executed computation.
    other = TestClient(create_app(root, artifacts_root=artifacts))
    assert other.get(f"/api/v1/jobs/{job['id']}").json()["job"]["status"] == "queued"
    assert execute_one(app.state.queue, app.state.prediction)
    result = other.get(f"/api/v1/jobs/{job['id']}/result").json()
    assert result["status"] == "succeeded"
    assert [f["source_frame_index"] for f in result["frames"]] == [5, 6, 7]
    assert [f["target_valid"] for f in result["frames"]] == [True, False, True]
    assert result["frames"][0]["metrics"]["iou"] > 0
    assert result["frames"][1]["metrics"] is None
    assert result["frames"][1]["target_region"] is None
    assert np.asarray(result["frames"][0]["region"]).shape == (64, 64)
    assert result["frames"][0]["contours"]
    assert result["provenance"] == "PREDICTION"
    assert result["source"]["project_split"] == "test"
    assert str(root) not in json.dumps(result)
    assert len(client.get("/api/v1/experiments").json()["items"]) == 1


@pytest.mark.parametrize(
    "changes",
    [
        {"observation_start": -1},
        {"observations": 3},
        {"observations": True},
        {"horizon": 25},
        {"model_id": "../../private.pt"},
        {"sequence_id": "../WH01"},
        {"checkpoint": "private.pt"},
        {"dataset_id": "other"},
        {"observation_start": 4},
        {"observation_start": 7},
    ],
)
def test_invalid_input_never_enqueues(prepared, changes):
    _, _, app, client, _ = prepared
    assert client.post("/api/v1/experiments/predict", json=payload(**changes)).status_code == 422
    assert app.state.queue.list() == []


def test_cancel_and_restart_recovery_and_lock(prepared):
    _, _, app, client, _ = prepared
    queue = app.state.queue
    first = submit(client)
    identifier = first["id"]
    assert client.post(f"/api/v1/jobs/{identifier}/cancel").json()["job"]["status"] == "cancelled"
    assert queue.claim() is None
    second = submit(client)
    assert queue.claim()["id"] == second["id"]
    restarted = JobQueue(queue.directory)
    with WorkerLock(queue.directory):
        with pytest.raises(RuntimeError, match="Another worker"):
            with WorkerLock(queue.directory):
                pass
        restarted.recover()
    assert restarted.get(second["id"])["status"] == "queued"
    restarted.claim()
    restarted.cancel(second["id"])
    restarted.recover()
    assert restarted.get(second["id"])["status"] == "cancelled"
    assert client.get("/api/v1/jobs/..%2Fsecret").status_code == 404


def test_running_cancellation_wins_finish(prepared, monkeypatch):
    _, _, app, client, _ = prepared
    job = submit(client)

    def cancelled_compute(*_):
        app.state.queue.cancel(job["id"])
        return {"status": "succeeded"}

    monkeypatch.setattr(app.state.prediction, "compute", cancelled_compute)
    execute_one(app.state.queue, app.state.prediction)
    assert app.state.queue.get(job["id"])["status"] == "cancelled"
    assert not app.state.queue.result_path(job["id"]).exists()


def trained_matrix(artifacts):
    torch = pytest.importorskip("torch")
    from morpholab_ml.models.forecast import build_model
    from morpholab_ml.training.runner import CHECKPOINT_SCHEMA

    config = {
        "state_channels": 4,
        "hidden_channels": 4,
        "step_size": 0.1,
        "state_limit": 4.0,
        "fire_rate": 1.0,
    }
    rows = []
    for variant in prediction.VARIANTS:
        for seed, loss in ((17, 0.2), (29, 0.1), (43, 0.3)):
            run_id = f"{variant}_seed{seed}"
            kind = "nca" if variant == "nca_h1" else variant
            path = artifacts / "training/forecast-v1" / run_id / "best.pt"
            path.parent.mkdir(parents=True)
            torch.save(
                {
                    "schema": CHECKPOINT_SCHEMA,
                    "model_kind": kind,
                    "model_config": config,
                    "model_state": build_model(kind, config).state_dict(),
                },
                path,
            )
            rows.append(
                {
                    "variant": variant,
                    "seed": seed,
                    "best_validation_loss": loss,
                    "test_loss": 0 if seed == 17 else 999,
                    "best_step": 100,
                    "completed_steps": 600,
                    "status": "complete",
                    "git_dirty": False,
                    "git_sha": "a" * 40,
                    "run_id": run_id,
                    "checkpoint_sha256": {"best.pt": file_sha256(path)},
                }
            )
    (artifacts / "training/forecast-v1/matrix.json").write_text(
        json.dumps({"status": "complete", "expected_runs": 12, "runs": rows}), encoding="utf-8"
    )


@pytest.mark.parametrize("kind", prediction.VARIANTS)
def test_trained_validation_selection_and_safe_checkpoint(prepared, kind):
    _, artifacts, app, client, _ = prepared
    trained_matrix(artifacts)
    models = client.get("/api/v1/models").json()["items"]
    assert len(models) == 6
    assert all(item["seed"] == 29 for item in models if item["trained"])
    job = submit(client, model_id=kind, horizon=1)
    assert execute_one(app.state.queue, app.state.prediction)
    result = client.get(f"/api/v1/jobs/{job['id']}/result").json()
    assert result["model"]["seed"] == 29
    assert result["model"]["checkpoint_sha256"]
    damaged = submit(client, model_id=kind, horizon=1)
    path = artifacts / "training/forecast-v1" / f"{kind}_seed29" / "best.pt"
    path.write_bytes(path.read_bytes() + b"changed")
    execute_one(app.state.queue, app.state.prediction)
    failed = app.state.queue.get(damaged["id"])
    assert failed["status"] == "failed"
    assert failed["error"]["type"] == "ValueError"
    assert str(artifacts) not in json.dumps(failed["error"])


def test_missing_matrix_and_research_pending(prepared):
    _, _, _, client, _ = prepared
    assert client.get("/api/v1/research").json()["status"] == "pending"
    models = client.get("/api/v1/models").json()["items"]
    assert sum(item["available"] for item in models) == 2
    assert (
        client.post("/api/v1/experiments/predict", json=payload(model_id="nca")).status_code == 503
    )


def test_manifest_mutation_fails_closed(prepared):
    _, artifacts, app, client, _ = prepared
    job = submit(client)
    (artifacts / "processed/manifest.json").write_text("changed", encoding="utf-8")
    execute_one(app.state.queue, app.state.prediction)
    assert app.state.queue.get(job["id"])["status"] == "failed"


def test_production_spa_preserves_deep_links_and_api_errors(tmp_path):
    dist = tmp_path / "frontend/dist"
    dist.mkdir(parents=True)
    (dist / "index.html").write_text("<html>SCIENCE WORKBENCH</html>", encoding="utf-8")
    client = TestClient(create_app(tmp_path))
    assert "SCIENCE WORKBENCH" in client.get("/studio/WH01").text
    assert client.get("/api/v1/unknown").status_code == 404
    assert client.get("/assets/missing.js").status_code == 404
    assert client.get("/api/v1/health").json()["worker_ready"] is False


def test_research_returns_all_actual_leads_and_rejects_wrong_schema(tmp_path):
    path = tmp_path / "docs/research/results/forecast-test-v1.json"
    path.parent.mkdir(parents=True)
    client = TestClient(create_app(tmp_path))
    path.write_text('{"schema_version":"wrong","split":"test"}')
    assert client.get("/api/v1/research").status_code == 503
    fixture = {
        "schema_version": "morpholab-forecast-evaluation-v1",
        "split": "test",
        "git_sha": "SYNTHETIC",
        "source_manifest_sha256": "SYNTHETIC",
        "summary": [
            {
                "variant": variant,
                "lead": lead,
                "is_endpoint": lead in (4, 12, 24),
                "n_sequences": 1,
                "n_windows": 1,
                "metrics_mean": {"iou": 0.5},
                "metrics_std": {"iou": None},
            }
            for variant in (*prediction.VARIANTS, *prediction.BASELINES)
            for lead in range(1, 25)
        ],
        "input_sensitivity": [],
    }
    path.write_text(json.dumps(fixture))
    reports = client.get("/api/v1/research").json()["reports"]
    assert len(reports) == 6
    assert all(len(report["metrics"]) == 24 for report in reports)
