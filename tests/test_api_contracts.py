"""Offline contract checks use synthetic metadata, never scientific evidence."""

from copy import deepcopy

import pytest
from pydantic import ValidationError

from backend.app.contracts import (
    DatasetEnvelope,
    DatasetListEnvelope,
    DatasetRecord,
    ErrorEnvelope,
    ExperimentListEnvelope,
    JobEnvelope,
    ModelListEnvelope,
    PredictionJob,
    PredictionResult,
    RegisteredModel,
    SequenceEnvelope,
    SequenceListEnvelope,
)

JOB = "00000000-0000-0000-0000-000000000001"
STAMP = "2026-10-22T00:00:00Z"
DIGEST = "a" * 64
REQUEST = {
    "dataset_id": "drosophila_wound_zenodo_7660424",
    "sequence_id": "WH01",
    "model_id": "persistence",
    "observation_start": 0,
    "observations": 4,
    "horizon": 1,
}
COMMON = {
    "schema_version": "1",
    "provenance": None,
    "dataset_id": None,
    "model_id": None,
    "run_id": None,
    "created_at_utc": STAMP,
}
MODEL = {
    "id": "persistence",
    "label": "persistence",
    "kind": "baseline",
    "variant": "persistence",
    "seed": None,
    "trained": False,
    "available": True,
    "selection": None,
    "checkpoint_sha256": None,
}


def result_fixture():
    def asset(layer):
        return {
            "url": f"/api/v1/jobs/{JOB}/frames/1?layer={layer}",
            "sha256": DIGEST,
        }

    return {
        **COMMON,
        "provenance": "MODEL_PREDICTION",
        "dataset_id": REQUEST["dataset_id"],
        "model_id": "persistence",
        "job_id": JOB,
        "status": "succeeded",
        "request": deepcopy(REQUEST),
        "grid": {"width": 64, "height": 64, "contour_coordinates": "working-grid pixel centers"},
        "source": {
            "source_id": "zenodo:7660424",
            "sequence_id": "WH01",
            "archive_sha256": DIGEST,
            "manifest_sha256": DIGEST,
            "npz_sha256": DIGEST,
            "original_width": 128,
            "original_height": 128,
            "project_split": "test",
        },
        "model": deepcopy(MODEL),
        "frames": [
            {
                "lead": 1,
                "source_frame_index": 4,
                "contours": [[[0.0, 1.0], [1.0, 2.0]]],
                "region_area": 5,
                "target_area": 5,
                "target_valid": True,
                "metrics": {
                    "iou": 1.0,
                    "dice": 1.0,
                    "area_mae": 0.0,
                    "signed_area_error": 0.0,
                    "mean_boundary_distance": 0.0,
                    "hausdorff95": 0.0,
                    "empty_boundary_mismatch": False,
                },
                "images": {layer: asset(layer) for layer in ("prediction", "target", "error")},
            }
        ],
        "target_provenance": "DERIVED_ANNOTATION",
        "device": "cpu",
        "precision": "fp32",
        "inference_environment": {
            "deterministic": True,
            "cpu_threads": 1,
            "convolution_fp32_precision": "ieee",
        },
    }


def job_fixture(status="queued"):
    return {
        "id": JOB,
        "status": status,
        "request": deepcopy(REQUEST),
        "created_at_utc": STAMP,
        "updated_at_utc": STAMP,
        "cancel_requested": False,
        "error": None,
        "result_available": status == "succeeded",
    }


def test_valid_synthetic_result_and_null_future_target():
    value = result_fixture()
    result = PredictionResult.model_validate(value)
    assert PredictionResult.model_validate_json(result.model_dump_json()) == result
    frame = value["frames"][0]
    frame.update(target_valid=False, target_area=None, metrics=None)
    frame["images"].update(target=None, error=None)
    assert PredictionResult.model_validate(value).frames[0].metrics is None


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("provenance",), "PREDICTION"),
        (("model_id",), "unknown"),
        (("request", "observations"), 3),
        (("request", "horizon"), 25),
        (("request", "horizon"), "1"),
        (("frames", 0, "region"), [[1]]),
        (("frames", 0, "region_area"), 4097),
        (("frames", 0, "target_valid"), False),
        (("frames", 0, "source_frame_index"), 6),
        (("frames", 0, "metrics", "iou"), 1.1),
        (("frames", 0, "metrics", "dice"), float("nan")),
        (("frames", 0, "contours"), [[[1.0, 2.0, 3.0]]]),
        (("frames", 0, "images", "prediction", "url"), "file:///private.png"),
        (("frames", 0, "images", "prediction", "sha256"), "bad-hash"),
        (("source", "sequence_id"), "WH02"),
        (("model", "id"), "nca"),
        (("inference_environment", "cpu_threads"), 0),
    ],
)
def test_strict_result_rejects_invalid_contract(path, value):
    payload = result_fixture()
    target = payload
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    with pytest.raises(ValidationError):
        PredictionResult.model_validate(payload)


def test_job_envelopes_and_legacy_safe_error():
    for status in ("queued", "running", "succeeded", "failed", "cancelled"):
        JobEnvelope.model_validate({**COMMON, "job": job_fixture(status)})
    job = job_fixture("failed")
    job["error"] = {"code": "PREDICTION_FAILED", "message": "Failed", "type": "ValueError"}
    validated = PredictionJob.model_validate(job)
    assert validated.error.trace_id is None
    assert validated.error.details is None
    ExperimentListEnvelope.model_validate({**COMMON, "items": [job]})
    error = ErrorEnvelope.model_validate({**COMMON, "error": job["error"]})
    assert error.error.trace_id is None
    with pytest.raises(ValidationError):
        PredictionJob.model_validate({**job, "status": "pending"})
    with pytest.raises(ValidationError):
        ExperimentListEnvelope.model_validate({**COMMON, "items": [job] * 101})


def test_registered_model_covers_registry_optional_fields():
    ModelListEnvelope.model_validate({**COMMON, "items": [MODEL]})
    trained = {
        **MODEL,
        "id": "nca",
        "variant": "nca",
        "kind": "trained",
        "seed": 17,
        "trained": True,
        "run_id": "nca_seed17",
        "model_git_sha": "b" * 40,
        "parameter_count": 14622,
        "checkpoint_sha256": DIGEST,
        "unavailable_reason": None,
        "selection": {"criterion": "validation_supervised_loss", "loss": 0.1, "step": 600},
    }
    assert RegisteredModel.model_validate(trained).seed == 17


def test_json_schema_has_exact_enums_assets_and_no_pixel_arrays():
    schema = PredictionResult.model_json_schema()
    model_ids = {
        "persistence",
        "constant_normal_speed",
        "nca",
        "nca_regularized",
        "convgru",
        "nca_h1",
    }
    assert set(schema["properties"]["model_id"]["enum"]) == model_ids
    assert schema["properties"]["provenance"]["const"] == "MODEL_PREDICTION"
    definitions = schema["$defs"]
    assert set(definitions["RegisteredModel"]["properties"]["id"]["enum"]) == model_ids
    assert "url" in definitions["ImageAsset"]["required"]
    assert "pattern" in definitions["ImageAsset"]["properties"]["url"]
    assert "images" in definitions["PredictionFrame"]["required"]
    assert not {"region", "target_region"} & definitions["PredictionFrame"]["properties"].keys()
    job_schema = PredictionJob.model_json_schema()
    assert set(job_schema["properties"]["status"]["enum"]) == {
        "queued",
        "running",
        "succeeded",
        "failed",
        "cancelled",
    }


def test_secondary_dataset_contract_and_json_metadata():
    secondary = {
        "id": "collective_cell_migration_bbbc019v2",
        "name": "BBBC019v2 static collective migration",
        "biology_domain": "static_collective_cell_migration",
        "source_url": "https://bbbc.broadinstitute.org/BBBC019",
        "doi": None,
        "license": "CC-BY-3.0",
        "sequence_count": None,
        "frame_count": None,
        "local_available": False,
        "annotation_type": "static_roi",
        "model_status": "untrained",
        "reported_frame_interval_min": None,
        "extra_source": {"verified": False, "notes": ["synthetic contract fixture", None, 1]},
    }
    record = DatasetRecord.model_validate(secondary)
    assert record.sequence_count is None
    assert record.model_dump()["extra_source"]["verified"] is False
    envelope = DatasetEnvelope.model_validate(
        {**COMMON, **secondary, "dataset_id": secondary["id"]}
    )
    assert envelope.dataset_id == secondary["id"]
    DatasetListEnvelope.model_validate({**COMMON, "items": [secondary]})
    with pytest.raises(ValidationError):
        DatasetRecord.model_validate(
            {key: value for key, value in secondary.items() if key != "name"}
        )
    with pytest.raises(ValidationError):
        DatasetRecord.model_validate({**secondary, "sequence_count": -1})
    with pytest.raises(ValidationError):
        DatasetRecord.model_validate({**secondary, "extra_source": object()})
    with pytest.raises(ValidationError):
        DatasetEnvelope.model_validate({**COMMON, **secondary, "extra_source": object()})


def test_sequence_and_frame_contracts_nullable_qc_and_shared_metadata():
    sequence = {
        "id": "WH01",
        "dataset_id": REQUEST["dataset_id"],
        "frame_count": 2,
        "width": 128,
        "height": 128,
        "project_split": "unassigned",
        "official_split": None,
        "qc_valid_count": None,
        "image_dtype": "uint16",
        "timestamp_min": None,
    }
    SequenceListEnvelope.model_validate({**COMMON, "items": [sequence]})
    payload = {
        **COMMON,
        **sequence,
        "provenance": "REAL_OBSERVED",
        "display": {"training_normalization": False, "source_dtype": "uint16"},
        "frames": [
            {"frame_index": 0, "timestamp_min": None, "qc_valid": True, "touches_border": False}
        ],
    }
    envelope = SequenceEnvelope.model_validate(payload)
    assert envelope.frames[0].timestamp_min is None
    assert envelope.qc_valid_count is None
    assert envelope.model_dump()["display"]["training_normalization"] is False
    with pytest.raises(ValidationError):
        SequenceEnvelope.model_validate({**payload, "width": "128"})
    with pytest.raises(ValidationError):
        SequenceEnvelope.model_validate({**payload, "display": object()})
    bad_frame = {**payload["frames"][0], "qc_valid": "true"}
    with pytest.raises(ValidationError):
        SequenceEnvelope.model_validate({**payload, "frames": [bad_frame]})


def test_data_contract_schemas_preserve_nullable_and_json_extras():
    dataset_schema = DatasetEnvelope.model_json_schema()
    assert dataset_schema["additionalProperties"] == {"$ref": "#/$defs/JsonValue"}
    assert dataset_schema["properties"]["dataset_id"]["anyOf"] == [
        {"type": "string"},
        {"type": "null"},
    ]
    sequence_schema = SequenceEnvelope.model_json_schema()
    assert sequence_schema["properties"]["qc_valid_count"]["anyOf"][1] == {"type": "null"}
    assert sequence_schema["properties"]["dataset_id"]["type"] == "string"
    assert (
        PredictionResult.model_json_schema()["properties"]["dataset_id"]["const"]
        == REQUEST["dataset_id"]
    )
