"""Metrics for derived regions on the explicitly declared working grid.

An absent boundary on exactly one side receives the grid diagonal as a finite
penalty and a failure flag. It is never silently omitted from averages.
"""

from __future__ import annotations

from typing import TypedDict

import numpy as np
from numpy.typing import NDArray
from scipy import ndimage


class RegionMetrics(TypedDict):
    iou: float
    dice: float
    area_mae: float
    signed_area_error: float
    mean_boundary_distance: float
    hausdorff95: float
    empty_boundary_mismatch: bool


def binary_region(value: NDArray[np.generic]) -> NDArray[np.bool_]:
    array = np.asarray(value)
    if array.ndim != 2 or min(array.shape) < 2:
        raise ValueError("A region must be a two-dimensional grid at least 2x2")
    if not np.isin(array, [0, 1]).all():
        raise ValueError("A region must contain only binary values")
    return array.astype(np.bool_, copy=False)


def boundary(region: NDArray[np.generic]) -> NDArray[np.bool_]:
    mask = binary_region(region)
    # A 4-connected erosion defines the inner digital boundary consistently.
    return mask & ~ndimage.binary_erosion(mask, border_value=0)


def region_metrics(predicted: NDArray[np.generic], target: NDArray[np.generic]) -> RegionMetrics:
    predicted_mask, target_mask = binary_region(predicted), binary_region(target)
    if predicted_mask.shape != target_mask.shape:
        raise ValueError("Prediction and target grids must have the same dimensions")
    predicted_area, target_area = int(predicted_mask.sum()), int(target_mask.sum())
    intersection = int((predicted_mask & target_mask).sum())
    union = predicted_area + target_area - intersection
    pred_boundary, true_boundary = boundary(predicted_mask), boundary(target_mask)
    pred_present, true_present = bool(pred_boundary.any()), bool(true_boundary.any())
    mismatch = pred_present != true_present
    if mismatch:
        mean_distance = hd95 = float(np.hypot(*predicted_mask.shape))
    elif not pred_present:
        mean_distance = hd95 = 0.0
    else:
        to_target = ndimage.distance_transform_edt(~true_boundary)[pred_boundary]
        to_prediction = ndimage.distance_transform_edt(~pred_boundary)[true_boundary]
        distances = np.concatenate((to_target, to_prediction))
        mean_distance = float(np.mean(distances))
        hd95 = float(np.percentile(distances, 95))
    return {
        "iou": intersection / union if union else 1.0,
        "dice": 2 * intersection / (predicted_area + target_area)
        if predicted_area + target_area
        else 1.0,
        "area_mae": float(abs(predicted_area - target_area)),
        "signed_area_error": float(predicted_area - target_area),
        "mean_boundary_distance": mean_distance,
        "hausdorff95": hd95,
        "empty_boundary_mismatch": mismatch,
    }
