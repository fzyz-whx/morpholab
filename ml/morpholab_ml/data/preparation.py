"""Pure array preparation under ADR-0001; no archives, HTTP, or filesystem access."""

from __future__ import annotations

import hashlib
from typing import Any

import numpy as np
from numpy.typing import NDArray
from scipy import ndimage

PROTOCOL = "morpholab-split-v1"
QC_PARAMETERS = {
    "native_shape": [128, 128],
    "working_shape": [64, 64],
    "foreground_connectivity": 8,
    "hole_background_connectivity": 4,
    "require_components": 1,
    "require_endpoints": 0,
    "require_branch_pixels": 0,
    "require_enclosed_holes": 1,
    "reject_border_contact": True,
    "region_definition": "binary_fill_holes(source_boundary > 0)",
    "resampling": "nearest_pixel_centers: source_index=floor((target_index+0.5)*2)",
    "sdf_definition": "clip(edt(region)-edt(~region),-8,8)/8; inside positive",
    "invalid_target_policy": "zero placeholders; valid=false; retain source frame and index",
    "target_provenance": "DERIVED_ANNOTATION",
}


def split_assignments(sequence_ids: list[str]) -> dict[str, str]:
    """Freeze all 62 source sequences without guessing the unavailable official split."""
    expected = (
        {f"Test{i:02d}" for i in range(1, 6)}
        | {f"WH{i:02d}" for i in range(1, 36)}
        | {f"WHu{i:02d}" for i in range(1, 23)}
    )
    if len(sequence_ids) != len(set(sequence_ids)) or set(sequence_ids) != expected:
        raise ValueError("Split protocol requires exactly the 62 known, unique source IDs")
    holdout = {f"Test{i:02d}" for i in range(1, 6)}
    candidates = sorted(
        expected - holdout,
        key=lambda key: hashlib.sha256(f"{PROTOCOL}:{key}".encode()).hexdigest(),
    )
    validation = set(candidates[:12])
    return {
        key: "test" if key in holdout else "validation" if key in validation else "train"
        for key in sorted(expected)
    }


def window_starts(
    valid: NDArray[np.bool_], length: int, horizon: int, stride: int = 1
) -> list[int]:
    """Return starts whose complete observed+target span is valid; never bridge gaps."""
    if valid.ndim != 1 or valid.dtype != np.bool_:
        raise ValueError("valid must be a one-dimensional boolean array")
    if any(type(value) is not int or value <= 0 for value in (length, horizon, stride)):
        raise ValueError("length, horizon, and stride must be positive integers")
    width = length + horizon
    return [
        start
        for start in range(0, len(valid) - width + 1, stride)
        if valid[start : start + width].all()
    ]


def prepare_sequence(
    images: NDArray[Any], source_boundary: NDArray[Any]
) -> tuple[dict[str, NDArray[Any]], list[dict[str, Any]]]:
    """Preserve native arrays and derive only QC-accepted morphology targets."""
    if (
        images.ndim != 3
        or images.shape[1:] != (128, 128)
        or images.dtype != np.uint16
        or len(images) == 0
    ):
        raise ValueError("Expected nonempty native uint16 image stack (N,128,128)")
    if source_boundary.shape != images.shape or source_boundary.dtype != np.uint8:
        raise ValueError("Expected aligned native uint8 boundary stack (N,128,128)")
    values = np.unique(source_boundary)
    if not np.isin(values, [0, 1, 255]).all() or (1 in values and 255 in values):
        raise ValueError("Boundary stack must use a consistent 0/1 or 0/255 encoding")
    count = len(images)
    arrays = {
        "images_native": np.array(images, copy=True),
        "source_boundary_native": np.array(source_boundary, copy=True),
        "derived_region_native": np.zeros(images.shape, dtype=np.bool_),
        "working_region": np.zeros((count, 64, 64), dtype=np.bool_),
        "working_sdf": np.zeros((count, 64, 64), dtype=np.float32),
        "valid": np.zeros(count, dtype=np.bool_),
        "source_frame_indices": np.arange(count, dtype=np.int64),
    }
    reports = []
    indices = np.arange(64) * 2 + 1
    for index, encoded in enumerate(source_boundary):
        boundary = encoded > 0
        neighbors = ndimage.convolve(
            boundary.astype(np.uint8), np.ones((3, 3), dtype=np.uint8), mode="constant"
        ) - boundary.astype(np.uint8)
        filled = ndimage.binary_fill_holes(boundary)
        components = int(ndimage.label(boundary, np.ones((3, 3)))[1])
        holes = int(ndimage.label(filled & ~boundary)[1])
        endpoints = int((boundary & (neighbors == 1)).sum())
        branches = int((boundary & (neighbors >= 3)).sum())
        border = bool(
            boundary[0].any() or boundary[-1].any() or boundary[:, 0].any() or boundary[:, -1].any()
        )
        reasons = []
        if components != 1:
            reasons.append("not_single_component")
        if endpoints:
            reasons.append("endpoints")
        if branches:
            reasons.append("branch_pixels")
        if holes != 1:
            reasons.append("not_single_enclosed_hole")
        if border:
            reasons.append("touches_border")
        if not reasons:
            working = filled[np.ix_(indices, indices)]
            if not working.any() or working.all():
                reasons.append("working_region_empty_or_full")
            else:
                arrays["derived_region_native"][index] = filled
                arrays["working_region"][index] = working
                sdf = ndimage.distance_transform_edt(working) - ndimage.distance_transform_edt(
                    ~working
                )
                arrays["working_sdf"][index] = (np.clip(sdf, -8, 8) / 8).astype(np.float32)
                arrays["valid"][index] = True
        reports.append(
            {
                "source_frame_index": index,
                "valid": not reasons,
                "reasons": reasons,
                "components_8_connected": components,
                "endpoints_8_neighbor": endpoints,
                "branch_pixels_8_neighbor": branches,
                "enclosed_holes_4_connected": holes,
                "touches_border": border,
            }
        )
    return arrays, reports


def reference_fingerprint(images: NDArray[Any]) -> NDArray[np.float64] | None:
    """A limited near-duplicate screen: normalized 16x16 first/middle/last thumbnails.

    This is a candidate flag, not proof of biological independence. Different crops,
    shifts, or temporal sampling can evade it; similar views may be false positives.
    """
    if images.ndim != 3 or images.shape[1:] != (128, 128) or not len(images):
        raise ValueError("Fingerprint expects nonempty native (N,128,128) images")
    samples = images[[0, len(images) // 2, len(images) - 1]].astype(np.float64)
    thumbnails = samples.reshape(3, 16, 8, 16, 8).mean(axis=(2, 4)).reshape(3, -1)
    thumbnails -= thumbnails.mean(axis=1, keepdims=True)
    norms = np.linalg.norm(thumbnails, axis=1, keepdims=True)
    if (norms == 0).any():
        return None
    return np.asarray((thumbnails / norms).ravel() / np.sqrt(3), dtype=np.float64)
