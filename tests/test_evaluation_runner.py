"""Offline runner contract tests; fixtures are synthetic and are not research results."""

import copy
import json
from pathlib import Path

import numpy as np
import pytest
from morpholab_ml.data.preparation import PROTOCOL, QC_PARAMETERS
from morpholab_ml.evaluation import runner


def fixture_manifest(root: Path, ids=("WH05",), count=8):
    records = []
    for key in ids:
        region = np.zeros((count, 64, 64), dtype=np.bool_)
        for index in range(count):
            region[index, 20:40, 20 : 40 - index] = True
        arrays = {
            "images_native": np.zeros((count, 128, 128), dtype=np.uint16),
            "source_boundary_native": np.zeros((count, 128, 128), dtype=np.uint8),
            "derived_region_native": np.zeros((count, 128, 128), dtype=np.bool_),
            "working_region": region,
            "working_sdf": np.where(region, 0.5, -0.5).astype(np.float32),
            "valid": np.ones(count, dtype=np.bool_),
            "source_frame_indices": np.arange(count, dtype=np.int64),
        }
        path = root / f"{key}.npz"
        np.savez_compressed(path, **arrays)
        records.append(
            {
                "sequence_id": key,
                "experiment_id": key,
                "grouping_basis": "source_sequence_proxy",
                "project_split": "validation",
                "official_split": None,
                "frame_count": count,
                "valid_frame_count": count,
                "invalid_frame_indices": [],
                "npz_relpath": path.name,
                "output_file_sha256": runner.file_sha256(path),
                "arrays": {
                    name: {"shape": list(array.shape), "dtype": str(array.dtype)}
                    for name, array in arrays.items()
                },
            }
        )
    manifest = {
        "schema_version": "morpholab-preparation-v1",
        "protocol": PROTOCOL,
        "source_archive": {"source_id": "zenodo:7660424", "sha256": runner.SOURCE_SHA256},
        "qc_parameters": QC_PARAMETERS,
        "totals": {"sequences": len(records)},
        "sequences": records,
    }
    path = root / "manifest.json"
    runner.save_json(path, manifest)
    return path, manifest


def rewrite_arrays(root, record, mutate):
    path = root / record["npz_relpath"]
    with np.load(path, allow_pickle=False) as bundle:
        arrays = dict(bundle)
    mutate(arrays)
    np.savez_compressed(path, **arrays)
    record["output_file_sha256"] = runner.file_sha256(path)


def test_evaluation_outputs_metadata_common_windows_and_sequence_means(tmp_path):
    path, manifest = fixture_manifest(tmp_path)
    output = tmp_path / "run"
    result = runner.evaluate(
        path, output, observations=2, horizons=(1, 3), stride=2, failure_count=1
    )
    metadata = json.loads((output / "run.json").read_text())
    assert metadata["status"] == "complete"
    assert metadata["split"] == "validation"
    assert metadata["source_manifest_sha256"] == runner.file_sha256(path)
    assert metadata["seeds"] == []
    assert metadata["n_sequences"] == 1
    assert metadata["n_windows"] == 2
    assert metadata["elapsed_seconds"] >= 0
    assert set(metadata["versions"]) == {"numpy", "scipy", "pillow"}
    assert metadata["git_sha"] is None or len(metadata["git_sha"]) == 40
    assert isinstance(metadata["git_dirty"], bool)
    assert len(metadata["implementation_file_sha256"]) == 4
    rows = json.loads((output / "metrics.json").read_text())
    assert len(rows) == 2 * 2 * 3
    assert {row["window_start"] for row in rows} == {0, 2}
    assert {row["lead"] for row in rows if row["is_endpoint"]} == {1, 3}
    assert (output / "metrics.csv").exists()
    assert len(result["summary"]["endpoints"]) == 4
    cases = json.loads((output / "failure-cases.json").read_text())
    assert len(cases) == 2
    assert cases[0]["target_provenance"] == "DERIVED_ANNOTATION"
    assert cases[0]["prediction_provenance"] == "PREDICTION"
    assert (output / cases[0]["png_relpath"]).exists()
    with pytest.raises(ValueError, match="new or empty"):
        runner.evaluate(path, output)


def test_source_protocol_and_split_integrity(tmp_path):
    path, manifest = fixture_manifest(tmp_path)
    for key, value in [("protocol", "other"), ("source_archive", {}), ("qc_parameters", {})]:
        changed = copy.deepcopy(manifest)
        changed[key] = value
        runner.save_json(path, changed)
        with pytest.raises(ValueError, match="mismatch"):
            runner.read_manifest(path)
    changed = copy.deepcopy(manifest)
    changed["sequences"][0]["project_split"] = "train"
    runner.save_json(path, changed)
    with pytest.raises(ValueError, match="split"):
        runner.read_manifest(path)


def test_duplicate_ids_and_cross_group_leakage(tmp_path):
    path, manifest = fixture_manifest(tmp_path, ids=("WH05", "WH06"))
    manifest["sequences"][1]["sequence_id"] = "WH05"
    runner.save_json(path, manifest)
    with pytest.raises(ValueError, match="Duplicate"):
        runner.read_manifest(path)
    path, manifest = fixture_manifest(tmp_path, ids=("WH05", "WH06"))
    second = manifest["sequences"][1]
    second.update(sequence_id="WH01", project_split="train", experiment_id="WH05")
    runner.save_json(path, manifest)
    with pytest.raises(ValueError, match="crosses"):
        runner.read_manifest(path)


@pytest.mark.parametrize(
    "path", ["../outside.npz", "/outside.npz", "C:/outside", "a\\b", "a//b", "./b"]
)
def test_unsafe_paths_rejected(tmp_path, path):
    with pytest.raises(ValueError, match="Unsafe"):
        runner.safe_path(tmp_path, path)


def test_resolved_symlink_escape_rejected(tmp_path, monkeypatch):
    inside = tmp_path / "inside.npz"
    outside = tmp_path.parent / "outside.npz"
    original = Path.resolve
    monkeypatch.setattr(
        Path,
        "resolve",
        lambda path, strict=False: outside if path == inside else original(path, strict=strict),
    )
    with pytest.raises(ValueError, match="escapes"):
        runner.safe_path(tmp_path, "inside.npz")


def test_npz_hash_mismatch(tmp_path):
    _, manifest = fixture_manifest(tmp_path)
    record = manifest["sequences"][0]
    (tmp_path / record["npz_relpath"]).write_bytes(b"changed")
    with pytest.raises(ValueError, match="SHA256"):
        runner.load_sequence(tmp_path, record)


@pytest.mark.parametrize(
    "key,change,match",
    [
        ("source_frame_indices", lambda a: a + 1, "gaps"),
        ("working_sdf", lambda a: np.full_like(a, np.nan), "finite"),
        ("working_sdf", lambda a: np.ones_like(a) * 2, "range"),
        ("working_sdf", lambda a: -a, "sign"),
        ("valid", lambda a: np.zeros_like(a), "valid mask"),
        ("working_region", lambda a: a[:, :32], "shape"),
    ],
)
def test_npz_array_contracts(tmp_path, key, change, match):
    _, manifest = fixture_manifest(tmp_path)
    record = manifest["sequences"][0]
    rewrite_arrays(tmp_path, record, lambda arrays: arrays.update({key: change(arrays[key])}))
    with pytest.raises(ValueError, match=match):
        runner.load_sequence(tmp_path, record)


def test_future_target_never_enters_predictor_and_qc_window_gaps_preserved(tmp_path, monkeypatch):
    path, manifest = fixture_manifest(tmp_path, count=8)
    record = manifest["sequences"][0]
    rewrite_arrays(tmp_path, record, lambda arrays: arrays["valid"].__setitem__(3, False))
    record.update(valid_frame_count=7, invalid_frame_indices=[3])
    runner.save_json(path, manifest)
    received = []

    def spy(history, horizon, *, distance_clip):
        assert history.shape == (2, 64, 64)
        assert horizon == 2
        received.append(history.copy())
        return np.repeat(history[-1:], horizon, axis=0)

    monkeypatch.setattr(runner, "BASELINES", {"spy": spy})
    result = runner.evaluate(
        path, tmp_path / "run", observations=2, horizons=(1, 2), stride=1, failure_count=0
    )
    assert result["metadata"]["n_windows"] == 1
    assert result["metadata"]["qc_excluded_windows"] == 4
    with np.load(tmp_path / record["npz_relpath"], allow_pickle=False) as arrays:
        np.testing.assert_array_equal(received[0], arrays["working_sdf"][4:6])
    assert len(received) == 1


def test_aggregation_gives_each_sequence_equal_weight():
    def row(sequence, score):
        return {
            "baseline": "fixture",
            "sequence_id": sequence,
            "lead": 4,
            **{key: score for key in runner.METRICS},
        }

    summary = runner.summarize([row("long", 1.0) for _ in range(10)] + [row("short", 0.0)])
    assert summary["aggregate"][0]["iou"] == 0.5
    assert summary["aggregate"][0]["n_sequences"] == 2
    assert summary["aggregate"][0]["n_windows"] == 11


def test_failure_saves_failed_status_and_does_not_touch_other_split(tmp_path):
    path, manifest = fixture_manifest(tmp_path)
    other = copy.deepcopy(manifest["sequences"][0])
    other.update(
        sequence_id="Test01",
        experiment_id="Test01",
        project_split="test",
        npz_relpath="missing-test.npz",
    )
    manifest["sequences"].append(other)
    manifest["totals"]["sequences"] = 2
    runner.save_json(path, manifest)
    runner.evaluate(path, tmp_path / "run", observations=2, horizons=(2,), failure_count=0)
    (tmp_path / manifest["sequences"][0]["npz_relpath"]).unlink()
    with pytest.raises(FileNotFoundError):
        runner.evaluate(path, tmp_path / "failed", observations=2, horizons=(2,), failure_count=0)
    assert json.loads((tmp_path / "failed/run.json").read_text())["status"] == "failed"


def test_unique_output_and_invalid_config(tmp_path):
    assert runner.unique_output(tmp_path) != runner.unique_output(tmp_path)
    path, _ = fixture_manifest(tmp_path)
    for kwargs in ({"split": "unassigned"}, {"horizons": ()}, {"observations": 1}, {"stride": 0}):
        with pytest.raises(ValueError):
            runner.evaluate(path, tmp_path / "unused", **kwargs)


def test_research_cli_rejects_a_silently_reduced_source_manifest(tmp_path, monkeypatch):
    from scripts import evaluate as command

    path, _ = fixture_manifest(tmp_path)
    output = tmp_path / "incomplete-run"
    monkeypatch.setattr(
        "sys.argv", ["evaluate.py", "--manifest", str(path), "--output", str(output)]
    )
    assert command.main() == 1
    assert not output.exists()
