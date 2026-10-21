"""Data-contract checks use local encoded images, never the research dataset."""

import hashlib
from pathlib import Path

import pytest
from morpholab_ml.data import DatasetCollection, FrameRecord, SequenceRecord
from PIL import Image
from pydantic import ValidationError


def frame_data(index=0, **changes):
    result = {
        "frame_index": index,
        "source_frame_index": index + 10,
        "timestamp_min": float(index),
        "image_relpath": f"images/{index}.png",
        "annotation_relpath": f"annotations/{index}.png",
        "image_file_sha256": "a" * 64,
        "annotation_file_sha256": "b" * 64,
        "annotation_type": "junction_skeleton",
        "height": 4,
        "width": 5,
        "provenance": "REAL_OBSERVED",
        "annotation_provenance": "source_annotation",
        "annotation_source": "Published segmentation stack, frame index as recorded",
    }
    result.update(changes)
    return result


def sequence_data(**changes):
    result = {
        "sequence_id": "seq01",
        "experiment_id": "proxy01",
        "dataset_id": "fixture",
        "biology_domain": "fixture_domain",
        "grouping_basis": "source_sequence_proxy",
        "split": "train",
        "frames": [frame_data(0), frame_data(1)],
    }
    result.update(changes)
    return result


@pytest.mark.parametrize(
    "field,value",
    [
        ("annotation_type", "unknown"),
        ("annotation_provenance", "assumed_ground_truth"),
        ("annotation_source", " "),
        ("provenance", "SYNTHETIC"),
        ("height", 0),
        ("width", -1),
        ("source_frame_index", -1),
        ("frame_index", -1),
        ("frame_index", 1.0),
        ("pixel_size_um", 0),
        ("timestamp_min", float("nan")),
        ("timestamp_min", float("inf")),
        ("image_file_sha256", "pixels_hash_is_not_a_file_hash"),
        ("annotation_file_sha256", "x" * 64),
    ],
)
def test_invalid_frame_fields(field, value):
    with pytest.raises(ValidationError):
        FrameRecord.model_validate(frame_data(**{field: value}))


@pytest.mark.parametrize("field", ["image_relpath", "annotation_relpath"])
@pytest.mark.parametrize(
    "path", ["../x.png", "/x.png", "C:/x.png", "a\\x.png", "a/../x.png", "./x", "a//x", ""]
)
def test_paths_are_canonical_safe_relative_files(field, path):
    with pytest.raises(ValidationError):
        FrameRecord.model_validate(frame_data(**{field: path}))


def test_unknown_scale_and_time_stay_null_and_extra_fields_fail():
    record = FrameRecord.model_validate(frame_data(timestamp_min=None))
    assert record.pixel_size_um is None
    assert record.timestamp_min is None
    assert record.model_dump(mode="json")["annotation_type"] == "junction_skeleton"
    with pytest.raises(ValidationError):
        FrameRecord.model_validate(frame_data(guessed_time=5))
    with pytest.raises(ValidationError):
        SequenceRecord.model_validate(sequence_data(extra_field=True))


@pytest.mark.parametrize(
    "second",
    [
        frame_data(0),
        frame_data(2),
        frame_data(1, source_frame_index=12),
        frame_data(1, timestamp_min=0),
        frame_data(1, timestamp_min=-1),
        frame_data(1, height=6),
    ],
)
def test_sequence_rejects_duplicates_gaps_times_and_size_changes(second):
    with pytest.raises(ValidationError):
        SequenceRecord.model_validate(sequence_data(frames=[frame_data(0), second]))


def test_known_times_increase_across_unknown_timestamp():
    frames = [frame_data(0), frame_data(1, timestamp_min=None), frame_data(2, timestamp_min=0)]
    with pytest.raises(ValidationError):
        SequenceRecord.model_validate(sequence_data(frames=frames))
    frames[-1]["timestamp_min"] = 2
    assert (
        SequenceRecord.model_validate(sequence_data(frames=frames)).frames[1].timestamp_min is None
    )


def test_unassigned_is_auditable_but_not_trainable():
    record = SequenceRecord.model_validate(sequence_data(split="unassigned"))
    collection = DatasetCollection(sequences=(record,))
    with pytest.raises(ValueError, match="Unassigned"):
        collection.validate_trainable()
    assert SequenceRecord.model_validate(sequence_data()).validate_trainable().split == "train"


def test_collection_rejects_duplicate_sequence_ids_and_group_leakage():
    first = SequenceRecord.model_validate(sequence_data())
    with pytest.raises(ValidationError, match="Duplicate"):
        DatasetCollection(sequences=(first, first))
    second = SequenceRecord.model_validate(sequence_data(sequence_id="seq02", split="test"))
    with pytest.raises(ValidationError, match="crosses splits"):
        DatasetCollection(sequences=(first, second))
    second = SequenceRecord.model_validate(
        sequence_data(sequence_id="seq02", experiment_id="proxy02", split="test")
    )
    assert DatasetCollection(sequences=(first, second)).validate_trainable()


def local_record(root: Path):
    frame = frame_data()
    for relative, field in (
        (frame["image_relpath"], "image_file_sha256"),
        (frame["annotation_relpath"], "annotation_file_sha256"),
    ):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        Image.new("L", (5, 4), 0).save(path)
        frame[field] = hashlib.sha256(path.read_bytes()).hexdigest()
    return SequenceRecord.model_validate(sequence_data(frames=[frame]))


def test_actual_encoded_file_hash_and_dimensions_pass(tmp_path):
    record = local_record(tmp_path)
    assert DatasetCollection(sequences=(record,)).validate_files(tmp_path)
    frame = record.frames[0]
    assert frame.image_file_sha256 != hashlib.sha256(bytes(20)).hexdigest()


@pytest.mark.parametrize("field", ["image_relpath", "annotation_relpath"])
def test_missing_file_rejected(tmp_path, field):
    record = local_record(tmp_path)
    (tmp_path / getattr(record.frames[0], field)).unlink()
    with pytest.raises(FileNotFoundError):
        record.validate_files(tmp_path)


def test_hash_mismatch_rejected(tmp_path):
    record = local_record(tmp_path)
    (tmp_path / record.frames[0].image_relpath).write_bytes(b"changed")
    with pytest.raises(ValueError, match="SHA256 mismatch"):
        record.validate_files(tmp_path)


@pytest.mark.parametrize("field", ["image_relpath", "annotation_relpath"])
def test_decoded_file_dimensions_rejected(tmp_path, field):
    record = local_record(tmp_path)
    data = record.model_dump(mode="json")
    path = tmp_path / getattr(record.frames[0], field)
    Image.new("L", (2, 2), 0).save(path)
    hash_field = "image_file_sha256" if field == "image_relpath" else "annotation_file_sha256"
    data["frames"][0][hash_field] = hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(ValueError, match="dimensions mismatch"):
        SequenceRecord.model_validate(data).validate_files(tmp_path)


def test_escaped_symlink_rejected(tmp_path):
    root = tmp_path / "dataset"
    root.mkdir()
    record = local_record(root)
    image = root / record.frames[0].image_relpath
    outside = tmp_path / "outside.png"
    image.replace(outside)
    try:
        image.symlink_to(outside)
    except OSError as exc:
        pytest.skip(f"Host does not permit symlink creation: {exc}")
    with pytest.raises(ValueError, match="escapes dataset root"):
        record.validate_files(root)


def test_resolved_path_escape_rejected_without_symlink_privileges(tmp_path, monkeypatch):
    root = tmp_path / "dataset"
    root.mkdir()
    record = local_record(root)
    source = root / record.frames[0].image_relpath
    outside = tmp_path / "outside.png"
    original_resolve = Path.resolve

    def resolve_fixture(path, strict=False):
        if path == source:
            return outside
        return original_resolve(path, strict=strict)

    monkeypatch.setattr(Path, "resolve", resolve_fixture)
    with pytest.raises(ValueError, match="escapes dataset root"):
        record.validate_files(root)


def test_nonexistent_root_rejected(tmp_path):
    record = SequenceRecord.model_validate(sequence_data())
    with pytest.raises(FileNotFoundError):
        record.validate_files(tmp_path / "missing")
