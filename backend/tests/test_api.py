import io
import json
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pytest
import tifffile
from fastapi.testclient import TestClient
from PIL import Image

from backend.app.data import PRIMARY_DATASET, DataStore
from backend.app.main import create_app
from scripts.audit_data import audit_archive


@pytest.fixture
def data_root(tmp_path: Path) -> Path:
    archive = tmp_path / "artifacts/raw/zenodo_7660424/Dataset.zip"
    archive.parent.mkdir(parents=True)
    with zipfile.ZipFile(archive, "w") as target:
        for sequence in range(1, 6):
            image = np.arange(6 * 16 * 16, dtype=np.uint16).reshape(6, 16, 16) + sequence
            label = np.zeros_like(image, dtype=np.uint8)
            label[:, 4:12, 4] = 255
            label[:, 4:12, 11] = 255
            label[:, 4, 4:12] = 255
            label[:, 11, 4:12] = 255
            for directory, array in [("Videos", image), ("Segmentations", label)]:
                output = io.BytesIO()
                tifffile.imwrite(output, array, photometric="minisblack")
                target.writestr(f"{directory}/WH{sequence:02d}.tif", output.getvalue())
    report = audit_archive(archive, tmp_path / "artifacts/audit", tmp_path / "artifacts/sample", ())
    summary = tmp_path / "datasets/audits/zenodo-7660424-summary.json"
    summary.parent.mkdir(parents=True)
    summary.write_text(json.dumps(report), encoding="utf-8")
    (tmp_path / "datasets/registry.yaml").write_text(
        "datasets:\n"
        f"- id: {PRIMARY_DATASET}\n"
        "  biology_domain: drosophila_embryo_in_vivo_laser_wound\n"
        "  record_url: https://zenodo.org/records/7660424\n"
        "  doi: 10.5281/zenodo.7660424\n"
        "  license: CC-BY-4.0\n"
        "  annotation_type: skeletonized_wound_boundary\n",
        encoding="utf-8",
    )
    return tmp_path


def test_metadata_and_unknown_split(data_root: Path) -> None:
    client = TestClient(create_app(data_root))
    assert client.get("/api/v1/health").json()["data_available"] is True
    items = client.get("/api/v1/datasets").json()["items"]
    assert items[0]["sequence_count"] == 5
    assert items[0]["local_available"] is True
    assert items[0]["model_status"] == "untrained"
    assert client.get(f"/api/v1/datasets/{PRIMARY_DATASET}").json()["license"] == "CC-BY-4.0"
    sequences = client.get("/api/v1/sequences").json()["items"]
    assert len(sequences) == 5
    assert all(item["official_split"] is None for item in sequences)
    assert all(item["project_split"] == "unassigned" for item in sequences)
    detail = client.get("/api/v1/sequences/WH01").json()
    assert [frame["frame_index"] for frame in detail["frames"]] == list(range(6))
    assert all(frame["timestamp_min"] is None for frame in detail["frames"])
    assert str(data_root) not in json.dumps(detail)


@pytest.mark.parametrize("layer,mode", [("observed", "L"), ("annotation", "L"), ("overlay", "RGB")])
def test_png_layers_are_real_and_marked(data_root: Path, layer: str, mode: str) -> None:
    client = TestClient(create_app(data_root))
    response = client.get(f"/api/v1/sequences/WH01/frames/2?layer={layer}")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.headers["x-derived-display"] == "true"
    assert response.headers["x-source-dtype"] == ("uint8" if layer == "annotation" else "uint16")
    assert response.headers["x-schema-version"] == "1"
    assert response.headers["x-dataset-id"] == PRIMARY_DATASET
    assert response.headers["x-source-id"] == "zenodo:7660424"
    assert response.headers["x-sequence-id"] == "WH01"
    assert response.headers["x-frame-index"] == "2"
    with Image.open(io.BytesIO(response.content)) as png:
        assert png.mode == mode
        assert png.size == (16, 16)
        if layer == "annotation":
            assert set(np.unique(np.asarray(png))) == {0, 255}
        if layer == "overlay":
            assert np.array_equal(np.asarray(png)[4, 4], [212, 220, 165])


@pytest.mark.parametrize(
    "url,status",
    [
        ("/api/v1/sequences/not-a-sequence", 404),
        ("/api/v1/sequences?dataset_id=missing", 404),
        ("/api/v1/datasets/missing", 404),
        ("/api/v1/sequences/WH01/frames/-1", 404),
        ("/api/v1/sequences/WH01/frames/6", 404),
        ("/api/v1/sequences/WH01/frames/not-a-number", 422),
        ("/api/v1/sequences/WH01/frames/0?layer=prediction", 422),
        ("/api/v1/sequences/..%2Fsecret/frames/0", 404),
    ],
)
def test_invalid_requests_are_structured(data_root: Path, url: str, status: int) -> None:
    response = TestClient(create_app(data_root)).get(url)
    assert response.status_code == status
    error = response.json()["error"]
    assert error["code"]
    assert error["trace_id"]
    assert str(data_root) not in response.text


def test_missing_and_changed_archive_invalidate_availability(data_root: Path) -> None:
    client = TestClient(create_app(data_root))
    assert client.get("/api/v1/sequences/WH01/frames/0").status_code == 200
    archive = data_root / "artifacts/raw/zenodo_7660424/Dataset.zip"
    archive.write_bytes(archive.read_bytes() + b"changed")
    response = client.get("/api/v1/sequences/WH01/frames/0")
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "ARCHIVE_CHECKSUM_MISMATCH"
    archive.unlink()
    health = client.get("/api/v1/health").json()
    assert health["status"] == "degraded"
    assert health["data_available"] is False
    response = client.get("/api/v1/sequences/WH01/frames/0")
    assert response.status_code == 503
    assert "scripts/download_data.py" in response.text
    assert str(data_root) not in response.text


def test_stack_lru_is_bounded_and_archive_not_modified(data_root: Path) -> None:
    store = DataStore(data_root)
    original = store.archive.read_bytes()
    for sequence in range(1, 6):
        store.frame_png(f"WH{sequence:02d}", 0, "observed")
    assert len(store._cache) == 4
    assert "WH01" not in store._cache
    assert store.archive.read_bytes() == original


def test_split_map_applied_without_official_claim(data_root: Path) -> None:
    splits = data_root / "datasets/splits/morpholab-split-v1.json"
    splits.parent.mkdir()
    splits.write_text(json.dumps({"assignments": {"WH01": "train"}}), encoding="utf-8")
    response = TestClient(create_app(data_root)).get("/api/v1/sequences/WH01")
    assert response.json()["project_split"] == "train"
    assert response.json()["official_split"] is None


def test_root_does_not_depend_on_cwd(data_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(data_root / "artifacts")
    client = TestClient(create_app(data_root))
    assert client.get("/api/v1/sequences/WH01/frames/0").status_code == 200


def test_methods_are_read_only(data_root: Path) -> None:
    response = TestClient(create_app(data_root)).post("/api/v1/datasets", json={})
    assert response.status_code == 405
    assert response.json()["error"]["trace_id"]


def test_prepared_qc_overrides_source_only_qc(data_root: Path) -> None:
    prepared = data_root / "artifacts/processed/manifest.json"
    prepared.parent.mkdir()
    source = json.loads(
        (data_root / "datasets/audits/zenodo-7660424-summary.json").read_text(encoding="utf-8")
    )
    prepared.write_text(
        json.dumps(
            {
                "source_archive": {"sha256": source["archive_sha256"]},
                "sequences": [
                    {"sequence_id": "WH01", "valid_frame_count": 4, "invalid_frame_indices": [1, 4]}
                ],
            }
        ),
        encoding="utf-8",
    )
    response = TestClient(create_app(data_root)).get("/api/v1/sequences/WH01")
    body = response.json()
    assert body["qc_valid_count"] == 4
    assert [row["frame_index"] for row in body["frames"] if not row["qc_valid"]] == [1, 4]
    assert "64x64" in body["qc_definition"]


def test_missing_audit_is_not_silently_available(data_root: Path) -> None:
    (data_root / "artifacts/audit/content-audit.json").unlink()
    client = TestClient(create_app(data_root))
    assert client.get("/api/v1/health").json()["data_available"] is False
    response = client.get("/api/v1/sequences/WH01/frames/0")
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "AUDIT_UNAVAILABLE"


@pytest.mark.parametrize(
    "url,dataset_id,provenance",
    [
        ("/api/v1/health", None, None),
        ("/api/v1/datasets", None, None),
        (f"/api/v1/datasets/{PRIMARY_DATASET}", PRIMARY_DATASET, None),
        ("/api/v1/sequences", PRIMARY_DATASET, "REAL_OBSERVED"),
        ("/api/v1/sequences/WH01", PRIMARY_DATASET, "REAL_OBSERVED"),
        ("/api/v1/sequences/missing", None, None),
        ("/api/v1/sequences/WH01/frames/0?layer=prediction", None, None),
        ("/api/v1/not-a-route", None, None),
    ],
)
def test_json_envelope_preserves_evidence_contract(
    data_root: Path, url: str, dataset_id: str | None, provenance: str | None
) -> None:
    before = datetime.now(UTC)
    body = TestClient(create_app(data_root)).get(url).json()
    assert body["schema_version"] == "1"
    assert body["dataset_id"] == dataset_id
    assert body["provenance"] == provenance
    assert body["model_id"] is None
    assert body["run_id"] is None
    created = datetime.fromisoformat(body["created_at_utc"])
    assert before <= created <= datetime.now(UTC)
    assert created.utcoffset().total_seconds() == 0
