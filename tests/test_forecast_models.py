import io
import json

import pytest

torch = pytest.importorskip("torch")

from morpholab_ml.models import ModelConfig, build_model, summary_conditions  # noqa: E402


@pytest.fixture(autouse=True)
def small_cpu_thread_pool():
    previous = torch.get_num_threads()
    torch.set_num_threads(1)
    yield
    torch.set_num_threads(previous)


def history(length=4, size=9):
    return torch.rand(2, length, size, size) * 1.6 - 0.8


def test_history_summary_has_exact_last_and_ls_slope_and_autograd():
    intercept = torch.rand(2, 1, 5, 7) * 0.2
    series = (intercept + torch.arange(4)[None, :, None, None] * 0.1).requires_grad_()
    conditions = summary_conditions(series)
    torch.testing.assert_close(conditions[:, 0], series[:, -1])
    torch.testing.assert_close(conditions[:, 1], torch.full((2, 5, 7), 0.1))
    conditions.sum().backward()
    assert series.grad is not None and series.grad.isfinite().all()


def test_summary_uses_only_supplied_history_and_supports_two_or_eight_frames():
    sequence = history(length=12)
    prefix = summary_conditions(sequence[:, :4]).clone()
    sequence[:, 4:] = -1
    torch.testing.assert_close(summary_conditions(sequence[:, :4]), prefix)
    assert summary_conditions(sequence[:, :2]).shape == (2, 2, 9, 9)
    assert summary_conditions(sequence[:, :8]).shape == (2, 2, 9, 9)


@pytest.mark.parametrize("kind", ["nca", "nca_regularized", "convgru"])
def test_free_rollout_shape_fp32_finite_and_persistence_initialization(kind):
    model = build_model(kind, {})
    inputs = history().double()
    result = model(inputs, 24)
    assert result.predictions.shape == (2, 24, 9, 9)
    assert result.predictions.dtype == torch.float32
    assert result.predictions.isfinite().all()
    assert result.predictions.abs().max() <= 1
    assert result.update_penalty.shape == ()
    assert result.update_penalty.isfinite() and result.update_penalty >= 0
    torch.testing.assert_close(
        result.predictions, inputs[:, -1:, :, :].float().expand(-1, 24, -1, -1)
    )


@pytest.mark.parametrize("kind", ["nca", "nca_regularized", "convgru"])
def test_backpropagates_and_updates_encoder_after_zero_head_is_unfrozen(kind):
    model = build_model(kind, {})
    optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
    inputs = history().requires_grad_()
    for _ in range(2):
        optimizer.zero_grad()
        result = model(inputs, 3)
        loss = (result.predictions - 0.2).square().mean() + 0.001 * result.update_penalty
        loss.backward()
        assert inputs.grad is not None and inputs.grad.isfinite().all()
        assert all(p.grad is None or p.grad.isfinite().all() for p in model.parameters())
        optimizer.step()
    assert any(p.grad is not None and p.grad.abs().sum() > 0 for p in model.encoder.parameters())
    assert all(p.grad is not None for p in model.parameters())


@pytest.mark.parametrize("kind", ["nca", "convgru"])
def test_seed_determinism_and_serialized_state_dict_restore(kind):
    config = json.loads(json.dumps(ModelConfig().to_dict()))
    torch.manual_seed(17)
    first = build_model(kind, config)
    torch.manual_seed(17)
    second = build_model(kind, config)
    inputs = history()
    torch.testing.assert_close(first(inputs, 6).predictions, second(inputs, 6).predictions)
    # Make the residual nonzero: a zero head could conceal a broken restoration.
    for parameter in first.parameters():
        with torch.no_grad():
            parameter.add_(0.01)
    buffer = io.BytesIO()
    torch.save(first.state_dict(), buffer)
    buffer.seek(0)
    second.load_state_dict(torch.load(buffer, weights_only=True))
    result = first(inputs, 24)
    restored = second(inputs, 24)
    torch.testing.assert_close(result.predictions, restored.predictions, rtol=0, atol=0)
    torch.testing.assert_close(result.update_penalty, restored.update_penalty, rtol=0, atol=0)
    assert result.predictions.isfinite().all()


def test_nca_variants_share_architecture_and_penalty_measures_actual_delta():
    torch.manual_seed(9)
    vanilla = build_model("nca", {})
    torch.manual_seed(9)
    regularized = build_model("nca_regularized", {})
    assert type(vanilla) is type(regularized)
    for key, value in vanilla.state_dict().items():
        torch.testing.assert_close(value, regularized.state_dict()[key])
    with torch.no_grad():
        vanilla.update[-1].bias.fill_(0.5)
    result = vanilla(torch.zeros(1, 2, 5, 5), 2)
    torch.testing.assert_close(result.update_penalty, torch.tensor(0.05**2))
    torch.testing.assert_close(result.predictions[:, 0], torch.full((1, 5, 5), 0.05))
    torch.testing.assert_close(result.predictions[:, 1], torch.full((1, 5, 5), 0.1))


def test_fixed_perception_has_replicate_edges_and_zero_constant_derivatives():
    model = build_model("nca", {})
    state = torch.ones(1, 16, 3, 5)
    perceived = torch.nn.functional.conv2d(
        torch.nn.functional.pad(state, (1, 1, 1, 1), mode="replicate"),
        model.perception_kernels,
        groups=16,
    ).reshape(1, 16, 4, 3, 5)
    torch.testing.assert_close(perceived[:, :, 0], state)
    torch.testing.assert_close(perceived[:, :, 1:], torch.zeros(1, 16, 3, 3, 5))
    assert not model.perception_kernels.requires_grad


@pytest.mark.parametrize("kind", ["nca", "convgru"])
def test_long_nonzero_rollout_is_bounded_and_differentiable(kind):
    model = build_model(kind, {})
    with torch.no_grad():
        head = model.update[-1] if kind == "nca" else model.head
        head.bias.fill_(0.2)
        head.weight.normal_(std=0.01)
    result = model(history(size=5), 128)
    assert result.predictions.shape == (2, 128, 5, 5)
    assert result.predictions.isfinite().all()
    assert result.predictions.abs().max() <= 1
    assert result.update_penalty.isfinite() and result.update_penalty > 0
    (result.predictions.square().mean() + result.update_penalty).backward()
    assert all(
        parameter.grad is None or parameter.grad.isfinite().all()
        for parameter in model.parameters()
    )


@pytest.mark.parametrize("kind", ["nca", "convgru"])
@pytest.mark.parametrize(
    "bad",
    [
        torch.zeros(1, 1, 3, 3),
        torch.zeros(1, 4, 0, 3),
        torch.zeros(1, 4, 3),
        torch.ones(1, 4, 3, 3) * 1.1,
        torch.full((1, 4, 3, 3), float("nan")),
        torch.full((1, 4, 3, 3), float("inf")),
        torch.zeros(1, 4, 3, 3, dtype=torch.int64),
    ],
)
def test_invalid_history_is_rejected(kind, bad):
    with pytest.raises(ValueError):
        build_model(kind, {})(bad, 2)


@pytest.mark.parametrize("bad", [0, -1, 1.5, True])
def test_invalid_horizon_is_rejected(bad):
    with pytest.raises(ValueError, match="horizon"):
        build_model("nca", {})(history(), bad)


@pytest.mark.parametrize(
    "config",
    [
        {"state_channels": 2},
        {"hidden_channels": True},
        {"step_size": 0},
        {"step_size": float("nan")},
        {"state_limit": 0.5},
        {"fire_rate": 0.5},
        {"observations": 4},
        {"hidden_channnels": 64},
    ],
)
def test_invalid_config_is_rejected(config):
    with pytest.raises(ValueError):
        build_model("nca", config)


def test_unknown_kind_is_rejected():
    with pytest.raises(ValueError, match="unknown model"):
        build_model("unknown", {})
