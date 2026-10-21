"""Offline preparation/QC tests use synthetic arrays, never biological evidence."""

import hashlib
import io
from pathlib import Path

import numpy as np
import pytest
from morpholab_ml.data.preparation import (
    prepare_sequence,
    reference_fingerprint,
    split_assignments,
    window_starts,
)
from scipy import ndimage

from scripts.prepare_data import run


def diamond(center=(64, 64), radius=20):
    yy, xx = np.indices((128, 128))
    return ((abs(yy - center[0]) + abs(xx - center[1])) == radius).astype(np.uint8) * 255


def stack(boundaries):
    annotation = np.stack(boundaries)
    images = np.arange(annotation.size, dtype=np.uint16).reshape(annotation.shape)
    return images, annotation


def source_ids():
    return (
        [f"Test{i:02d}" for i in range(1, 6)]
        + [f"WH{i:02d}" for i in range(1, 36)]
        + [f"WHu{i:02d}" for i in range(1, 23)]
    )


def test_closed_diamond_derivation_sdf_sign_and_native_preservation():
    images, annotation = stack([diamond(radius=24)])
    arrays, reports = prepare_sequence(images, annotation)
    assert arrays["valid"].tolist() == [True]
    assert reports[0]["reasons"] == []
    np.testing.assert_array_equal(arrays["images_native"], images)
    np.testing.assert_array_equal(arrays["source_boundary_native"], annotation)
    native = ndimage.binary_fill_holes(annotation[0] > 0)
    np.testing.assert_array_equal(arrays["derived_region_native"][0], native)
    working = native[1::2, 1::2]
    np.testing.assert_array_equal(arrays["working_region"][0], working)
    expected = (
        np.clip(
            ndimage.distance_transform_edt(working) - ndimage.distance_transform_edt(~working),
            -8,
            8,
        )
        / 8
    )
    np.testing.assert_allclose(arrays["working_sdf"][0], expected)
    assert arrays["working_sdf"].dtype == np.float32
    assert arrays["working_sdf"][0][working].min() > 0
    assert arrays["working_sdf"][0][~working].max() < 0
    assert arrays["working_sdf"].max() == 1
    assert arrays["working_sdf"].min() == -1


def test_failed_frames_are_preserved_and_never_bridge_valid_windows():
    broken = diamond()
    broken[44, 64] = 0
    images, annotation = stack([diamond(), broken, diamond(), diamond()])
    arrays, reports = prepare_sequence(images, annotation)
    assert len(reports) == 4
    assert arrays["valid"].tolist() == [True, False, True, True]
    assert arrays["source_frame_indices"].tolist() == [0, 1, 2, 3]
    assert arrays["images_native"].shape[0] == 4
    assert not arrays["derived_region_native"][1].any()
    assert not arrays["working_sdf"][1].any()
    assert window_starts(arrays["valid"], 1, 1) == [2]


@pytest.mark.parametrize(
    "boundary,reason",
    [
        (np.zeros((128, 128), dtype=np.uint8), "not_single_component"),
        (diamond((20, 64)), "touches_border"),
        (diamond(radius=1), "working_region_empty_or_full"),
        (np.maximum(diamond((40, 40), 10), diamond((90, 90), 10)), "not_single_component"),
    ],
)
def test_qc_rejects_bad_geometry(boundary, reason):
    arrays, reports = prepare_sequence(*stack([boundary]))
    assert not arrays["valid"][0]
    assert reason in reports[0]["reasons"]


def test_branch_not_silently_repaired():
    boundary = diamond()
    boundary[39:44, 64] = 255
    arrays, reports = prepare_sequence(*stack([boundary]))
    assert not arrays["valid"][0]
    assert "branch_pixels" in reports[0]["reasons"]
    np.testing.assert_array_equal(arrays["source_boundary_native"][0], boundary)


@pytest.mark.parametrize(
    "images,annotations",
    [
        (np.zeros((0, 128, 128), np.uint16), np.zeros((0, 128, 128), np.uint8)),
        (np.zeros((1, 64, 64), np.uint16), np.zeros((1, 64, 64), np.uint8)),
        (np.zeros((1, 128, 128), np.float32), np.zeros((1, 128, 128), np.uint8)),
        (np.zeros((1, 128, 128), np.uint16), np.zeros((2, 128, 128), np.uint8)),
        (np.zeros((1, 128, 128), np.uint16), np.zeros((1, 128, 128), np.uint16)),
    ],
)
def test_input_contracts_reject_wrong_dtype_shape_or_empty(images, annotations):
    with pytest.raises(ValueError):
        prepare_sequence(images, annotations)


def test_deterministic_npz_bytes_and_no_source_mutation():
    images, annotation = stack([diamond(), diamond(radius=22)])
    originals = images.copy(), annotation.copy()
    first, _ = prepare_sequence(images, annotation)
    second, _ = prepare_sequence(images, annotation)
    buffers = [io.BytesIO(), io.BytesIO()]
    np.savez_compressed(buffers[0], **first)
    np.savez_compressed(buffers[1], **second)
    assert buffers[0].getvalue() == buffers[1].getvalue()
    np.testing.assert_array_equal(images, originals[0])
    np.testing.assert_array_equal(annotation, originals[1])


def test_frozen_split_counts_hash_order_and_no_leakage():
    assignments = split_assignments(source_ids())
    assert assignments == split_assignments(list(reversed(source_ids())))
    assert sum(value == "train" for value in assignments.values()) == 45
    assert sum(value == "validation" for value in assignments.values()) == 12
    assert sum(value == "test" for value in assignments.values()) == 5
    assert all(assignments[f"Test{i:02d}"] == "test" for i in range(1, 6))
    ranked = sorted(
        [key for key in source_ids() if not key.startswith("Test")],
        key=lambda key: hashlib.sha256(f"morpholab-split-v1:{key}".encode()).hexdigest(),
    )
    assert {key for key, value in assignments.items() if value == "validation"} == set(ranked[:12])


@pytest.mark.parametrize("ids", [source_ids()[:-1], source_ids() + ["WH01"], ["unknown"]])
def test_split_rejects_dropped_duplicate_or_new_sequence(ids):
    with pytest.raises(ValueError):
        split_assignments(ids)


def test_window_boundaries_stride_and_complete_horizon():
    valid = np.ones(10, dtype=np.bool_)
    assert window_starts(valid, 4, 4) == [0, 1, 2]
    assert window_starts(valid, 4, 4, 2) == [0, 2]
    assert window_starts(valid, 4, 6) == [0]
    assert window_starts(valid, 4, 7) == []
    valid[5] = False
    assert window_starts(valid, 2, 2) == [0, 1, 6]


@pytest.mark.parametrize("args", [(0, 1, 1), (1, 0, 1), (1, 1, 0), (1.0, 1, 1), (True, 1, 1)])
def test_bad_window_parameters(args):
    with pytest.raises(ValueError):
        window_starts(np.ones(10, dtype=np.bool_), *args)


def test_bad_valid_array():
    for valid in (np.ones(10, dtype=np.uint8), np.ones((2, 2), dtype=np.bool_)):
        with pytest.raises(ValueError):
            window_starts(valid, 1, 1)


def test_cli_processing_refuses_wrong_archive_hash(tmp_path: Path):
    archive = tmp_path / "bad.zip"
    archive.write_bytes(b"untrusted source")
    with pytest.raises(ValueError, match="SHA256"):
        run(archive, tmp_path / "processed", tmp_path / "freeze.json")
    assert not (tmp_path / "processed").exists()


def test_reference_fingerprint_flags_brightness_scaled_duplicate_and_skips_constant():
    rng = np.random.default_rng(0)
    images = rng.integers(0, 1000, (3, 128, 128), dtype=np.uint16)
    first = reference_fingerprint(images)
    second = reference_fingerprint(images * 2 + 20)
    assert first is not None and second is not None
    assert np.dot(first, second) == pytest.approx(1)
    assert reference_fingerprint(np.zeros_like(images)) is None


@pytest.mark.parametrize("value", [2, 128, 1])
def test_annotation_encoding_rejects_other_values_and_mixed_foreground(value):
    images, annotation = stack([diamond()])
    annotation[0, 0, 0] = value
    with pytest.raises(ValueError, match="consistent 0/1 or 0/255"):
        prepare_sequence(images, annotation)
