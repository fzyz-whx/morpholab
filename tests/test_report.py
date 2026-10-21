"""Synthetic contract checks; these fixtures are not research evidence."""

import hashlib
import json
from types import SimpleNamespace

import pytest

from scripts import report


@pytest.fixture
def source(tmp_path, monkeypatch):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    manifest_path = tmp_path / "manifest.json"
    manifest = {
        "protocol": "morpholab-split-v1",
        "source_archive": {"sha256": "synthetic"},
        "qc_parameters": {"working_shape": [64, 64]},
        "sequences": [
            {"sequence_id": str(i), "project_split": "validation" if i < 2 else "train"}
            for i in range(62)
        ],
    }
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    run = {
        "status": "complete",
        "git_dirty": False,
        "git_sha": "synthetic",
        "manifest_scope": "complete_62_sequence_source",
        "split": "validation",
        "source_manifest_sha256": report.digest(manifest_path),
        "protocol": manifest["protocol"],
        "horizons": [4, 12, 24],
        "observations": 4,
        "baselines": ["persistence", "constant_normal_speed"],
        "target_provenance": "DERIVED_ANNOTATION",
        "prediction_provenance": "PREDICTION",
        "versions": {"numpy": "synthetic"},
        "implementation_file_sha256": {"source.py": hashlib.sha256(b"source").hexdigest()},
        "n_sequences": 2,
        "n_sequences_with_windows": 2,
        "n_windows": 3,
        "qc_excluded_windows": 0,
    }
    rows, per_sequence, aggregate = [], [], []
    for baseline in sorted(run["baselines"]):
        for lead in range(1, 25):
            aggregate.append(
                {
                    "baseline": baseline,
                    "lead": lead,
                    "n_sequences": 2,
                    "n_windows": 3,
                    **dict.fromkeys(report.METRICS, 0.5),
                }
            )
            for sequence, count, value in (("0", 1, 0.2), ("1", 2, 0.8)):
                per_sequence.append(
                    {
                        "baseline": baseline,
                        "sequence_id": sequence,
                        "lead": lead,
                        "n_windows": count,
                        **dict.fromkeys(report.METRICS, value),
                    }
                )
                for window in range(count):
                    rows.append(
                        {
                            "baseline": baseline,
                            "sequence_id": sequence,
                            "lead": lead,
                            "window_start": window,
                            "project_split": "validation",
                            "is_endpoint": lead in [4, 12, 24],
                            **dict.fromkeys(report.METRICS, value),
                        }
                    )
    summary = {
        "aggregate": aggregate,
        "per_sequence": per_sequence,
        "endpoints": [r for r in aggregate if r["lead"] in [4, 12, 24]],
        "aggregation": "windows within sequence, then equal sequence weights",
        "window_qc": [
            {"sequence_id": s, "valid_windows": n, "candidate_windows": n, "qc_excluded_windows": 0}
            for s, n in (("0", 1), ("1", 2))
        ],
    }
    for name, value in (
        ("run.json", run),
        ("summary.json", summary),
        ("metrics.json", rows),
        ("failure-cases.json", []),
    ):
        (run_dir / name).write_text(json.dumps(value), encoding="utf-8")
    monkeypatch.setattr(
        report.subprocess, "run", lambda *a, **kw: SimpleNamespace(stdout=b"source")
    )
    return run_dir, manifest_path


def mutate(source, filename, change):
    path = source[0] / filename
    value = report.load(path)
    change(value)
    path.write_text(json.dumps(value), encoding="utf-8")


def test_equal_sequence_weights_and_source_hashes(source):
    result = report.checked_report(*source)
    assert result["aggregate"][0]["iou"] == 0.5  # Pooled windows would give 0.6.
    assert len(result["endpoints"]) == 6
    assert result["source_files_sha256"]["metrics.json"] == report.digest(
        source[0] / "metrics.json"
    )


@pytest.mark.parametrize(
    "field,value",
    [("git_dirty", True), ("status", "running"), ("manifest_scope", "partial_source_manifest")],
)
def test_reject_nonformal_run(source, field, value):
    mutate(source, "run.json", lambda r: r.update({field: value}))
    with pytest.raises(ValueError):
        report.checked_report(*source)


def test_reject_metric_scope_and_tampered_summary(source):
    mutate(source, "summary.json", lambda s: s["aggregate"][0].update(iou=0.9))
    with pytest.raises(ValueError, match="aggregate mismatch"):
        report.checked_report(*source)
    mutate(source, "metrics.json", lambda rows: rows[0].update(project_split="test"))
    with pytest.raises(ValueError, match="outside validation scope"):
        report.checked_report(*source)


def test_reject_source_hash_mismatch(source):
    mutate(
        source,
        "run.json",
        lambda r: r["implementation_file_sha256"].update({"source.py": "0" * 64}),
    )
    with pytest.raises(ValueError, match="Source hash mismatch"):
        report.checked_report(*source)


def test_reject_manifest_change_and_local_path(source):
    source[1].write_text(source[1].read_text() + " ", encoding="utf-8")
    with pytest.raises(ValueError, match="Manifest hash mismatch"):
        report.checked_report(*source)
    with pytest.raises(ValueError, match="Absolute local path"):
        report.public_metadata({"accidental": "C:\\Users\\private\\data"})
