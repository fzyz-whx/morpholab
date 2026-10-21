import numpy as np
import pytest
from morpholab_ml.baselines.geometric import constant_normal_speed, persistence
from morpholab_ml.evaluation.metrics import region_metrics
from scipy import ndimage


def circle(radius, size=48):
    yy, xx = np.mgrid[:size, :size]
    return (yy - size // 2) ** 2 + (xx - size // 2) ** 2 <= radius**2


def sdf(mask):
    return np.clip(
        (ndimage.distance_transform_edt(mask) - ndimage.distance_transform_edt(~mask)) / 8,
        -1,
        1,
    ).astype(np.float32)


def test_identical_and_empty_regions_have_defined_perfect_metrics():
    for region in (circle(8), np.zeros((10, 10), bool)):
        result = region_metrics(region, region)
        assert result["iou"] == result["dice"] == 1
        assert result["mean_boundary_distance"] == result["hausdorff95"] == 0
        assert result["area_mae"] == 0
        assert not result["empty_boundary_mismatch"]


def test_missing_prediction_is_penalized_not_omitted():
    target = circle(8)
    result = region_metrics(np.zeros_like(target), target)
    assert result["iou"] == result["dice"] == 0
    assert result["mean_boundary_distance"] == pytest.approx(np.hypot(*target.shape))
    assert result["empty_boundary_mismatch"]
    assert result["signed_area_error"] == -target.sum()


def test_boundary_distances_are_symmetric_and_nonzero_for_displacement():
    target = circle(8)
    predicted = np.roll(target, 3, axis=1)
    forward, backward = region_metrics(predicted, target), region_metrics(target, predicted)
    assert forward["mean_boundary_distance"] == pytest.approx(backward["mean_boundary_distance"])
    assert forward["hausdorff95"] == pytest.approx(3.0)
    assert 0 < forward["mean_boundary_distance"] < 3
    assert forward["area_mae"] == 0


def test_metric_rejects_nonbinary_and_mismatched_grids():
    with pytest.raises(ValueError, match="binary"):
        region_metrics(np.full((4, 4), 0.5), np.zeros((4, 4)))
    with pytest.raises(ValueError, match="same dimensions"):
        region_metrics(np.zeros((3, 3)), np.zeros((4, 4)))


def test_persistence_uses_only_final_observed_field_and_returns_independent_copy():
    history = np.stack([sdf(circle(9)), sdf(circle(8))])
    result = persistence(history, 3)
    assert np.array_equal(result[0], history[-1])
    result[0] = 0
    assert history[-1].any()


def test_classical_baseline_forecasts_shrinking_shapes_without_future_input():
    history = np.stack([sdf(circle(r)) for r in (12, 11, 10, 9)])
    result = constant_normal_speed(history, 5)
    areas = (result > 0).sum(axis=(1, 2))
    assert result.shape == (5, 48, 48)
    assert np.isfinite(result).all()
    # A subpixel radius change can leave the first thresholded raster unchanged.
    assert areas[0] <= (history[-1] > 0).sum()
    assert areas[-1] < (history[-1] > 0).sum()
    assert np.all(np.diff(areas) <= 0)


def test_classical_baseline_allows_expansion_without_flipping_far_background():
    history = np.stack([sdf(circle(r)) for r in (4, 5, 6, 7)])
    result = constant_normal_speed(history, 8)
    assert (result[-1] > 0).sum() > (history[-1] > 0).sum()
    assert result[-1, 0, 0] < 0


@pytest.mark.parametrize("bad", [0, -1, True, 1.5])
def test_baselines_reject_invalid_horizon(bad):
    with pytest.raises(ValueError, match="Horizon"):
        persistence(np.stack([sdf(circle(4))]), bad)
