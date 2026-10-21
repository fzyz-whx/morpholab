"""Persistence and a constant-normal-speed level-set approximation.

The classical baseline estimates effective-radius velocity from historical area.
It is an explicit geometrical approximation, not a biological force law.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray
from scipy import ndimage


def validate_history(
    history: NDArray[np.generic], horizon: int, distance_clip: float
) -> NDArray[np.float32]:
    values = np.asarray(history)
    if values.ndim != 3 or values.shape[0] < 1 or min(values.shape[1:]) < 2:
        raise ValueError("History must be [observations, height, width]")
    if not np.isfinite(values).all() or np.abs(values).max() > 1.00001:
        raise ValueError("History must contain finite signed distances normalized to [-1,1]")
    if isinstance(horizon, bool) or not isinstance(horizon, int) or horizon < 1:
        raise ValueError("Horizon must be a positive integer")
    if not np.isfinite(distance_clip) or distance_clip <= 0:
        raise ValueError("Distance clip must be positive and finite")
    return values.astype(np.float32, copy=False)


def persistence(
    history: NDArray[np.generic], horizon: int, *, distance_clip: float = 8.0
) -> NDArray[np.float32]:
    values = validate_history(history, horizon, distance_clip)
    return np.repeat(values[-1:], horizon, axis=0)


def constant_normal_speed(
    history: NDArray[np.generic],
    horizon: int,
    *,
    distance_clip: float = 8.0,
    maximum_speed: float = 2.0,
) -> NDArray[np.float32]:
    values = validate_history(history, horizon, distance_clip)
    if len(values) < 2:
        raise ValueError("Classical speed estimation requires at least two observations")
    if not np.isfinite(maximum_speed) or maximum_speed <= 0:
        raise ValueError("Maximum speed must be positive and finite")
    masks = values > 0
    radii = np.sqrt(masks.sum(axis=(1, 2)) / np.pi)
    times = np.arange(len(radii), dtype=np.float64)
    centered = times - times.mean()
    velocity = float(centered @ radii / (centered @ centered))
    velocity = float(np.clip(velocity, -maximum_speed, maximum_speed))
    last = masks[-1]
    if not last.any():
        return np.full((horizon, *last.shape), -1.0, dtype=np.float32)
    # Recover the full distance field before extrapolating. Shifting the clipped
    # field itself would incorrectly flip far-away saturated pixels in long runs.
    signed_distance = ndimage.distance_transform_edt(last) - ndimage.distance_transform_edt(~last)
    offsets = np.arange(1, horizon + 1, dtype=np.float32)[:, None, None] * velocity
    result = np.clip((signed_distance[None] + offsets) / distance_clip, -1.0, 1.0)
    return np.asarray(result, dtype=np.float32)
