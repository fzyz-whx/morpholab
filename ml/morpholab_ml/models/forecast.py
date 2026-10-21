"""Free-running SDF forecasting under ADR-0002; no future frames enter this API."""

import math
from dataclasses import asdict, dataclass, fields
from typing import Any

import torch
from torch import Tensor, nn
from torch.nn import functional as F


@dataclass(frozen=True)
class ModelConfig:
    state_channels: int = 16
    hidden_channels: int = 64
    step_size: float = 0.1
    state_limit: float = 4.0
    fire_rate: float = 1.0

    def __post_init__(self) -> None:
        for name in ("state_channels", "hidden_channels"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 3:
                raise ValueError(f"{name} must be an integer >= 3")
        for name in ("step_size", "state_limit", "fire_rate"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"{name} must be a finite positive number")
            if not math.isfinite(value) or value <= 0:
                raise ValueError(f"{name} must be a finite positive number")
        if self.state_limit < 1:
            raise ValueError("state_limit must be >= 1")
        if self.fire_rate != 1:
            raise ValueError("only synchronous fire_rate=1 is supported")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, config: dict[str, Any]) -> "ModelConfig":
        """Restore only model configuration; reject misspelled or unrelated keys."""
        if not isinstance(config, dict):
            raise TypeError("model config must be a dictionary")
        names = {field.name for field in fields(cls)}
        unknown = config.keys() - names
        if unknown:
            raise ValueError(f"unknown model configuration keys: {sorted(unknown)}")
        return cls(**config)


@dataclass
class ForecastOutput:
    predictions: Tensor
    update_penalty: Tensor


def _validate_history(history: Tensor) -> None:
    if not isinstance(history, Tensor):
        raise TypeError("history must be a torch Tensor")
    if history.ndim != 4 or history.shape[1] < 2 or min(history.shape) < 1:
        raise ValueError("history must have nonempty shape [B,L>=2,Y,X]")
    if not history.is_floating_point():
        raise ValueError("history must be floating point SDF")
    if not bool(torch.isfinite(history).all()):
        raise ValueError("history must contain only finite values")
    if bool((history.abs() > 1).any()):
        raise ValueError("history SDF must lie in [-1,1]")


def summary_conditions(history: Tensor) -> Tensor:
    """Return [last SDF, per-pixel least-squares slope], using history indices only.

    Slopes are in normalized SDF units per source frame. They are not clipped or
    fitted using any dataset-wide statistics. Casting to fp32 preserves autograd.
    """
    _validate_history(history)
    history = history.float()
    time = torch.arange(history.shape[1], device=history.device, dtype=torch.float32)
    centered = time - time.mean()
    slope = (history * centered[None, :, None, None]).sum(dim=1) / centered.square().sum()
    return torch.stack((history[:, -1], slope), dim=1)


def _check_horizon(horizon: int) -> None:
    if isinstance(horizon, bool) or not isinstance(horizon, int) or horizon < 1:
        raise ValueError("horizon must be a positive integer")


def _spatial_conv(inputs: int, outputs: int) -> nn.Conv2d:
    return nn.Conv2d(inputs, outputs, 3, padding=1, padding_mode="replicate")


def _encoder(outputs: int, hidden: int) -> nn.Sequential:
    return nn.Sequential(_spatial_conv(2, hidden), nn.ReLU(), _spatial_conv(hidden, outputs))


class LocalNCA(nn.Module):
    """16-state default NCA; regularization is selected solely in the training loss."""

    perception_kernels: Tensor

    def __init__(self, config: ModelConfig) -> None:
        super().__init__()
        self.config = config
        self.encoder = _encoder(config.state_channels - 2, config.hidden_channels)
        kernels = torch.tensor(
            [
                [[0, 0, 0], [0, 1, 0], [0, 0, 0]],
                [[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]],
                [[-1, -2, -1], [0, 0, 0], [1, 2, 1]],
                [[0, 1, 0], [1, -4, 1], [0, 1, 0]],
            ],
            dtype=torch.float32,
        )
        kernels[1:3] /= 8
        self.register_buffer(
            "perception_kernels", kernels[:, None].repeat(config.state_channels, 1, 1, 1)
        )
        update_input = nn.Conv2d(config.state_channels * 4 + 2, config.hidden_channels, 1)
        update_output = nn.Conv2d(config.hidden_channels, config.state_channels, 1)
        self.update = nn.Sequential(update_input, nn.ReLU(), update_output)
        nn.init.zeros_(update_output.weight)
        if update_output.bias is not None:
            nn.init.zeros_(update_output.bias)

    def forward(self, history: Tensor, horizon: int) -> ForecastOutput:
        _check_horizon(horizon)
        conditions = summary_conditions(history)
        state = torch.cat((conditions, self.encoder(conditions)), dim=1)
        state = state.clamp(-self.config.state_limit, self.config.state_limit)
        predictions = []
        penalties = []
        for _ in range(horizon):
            perceived = F.conv2d(
                F.pad(state, (1, 1, 1, 1), mode="replicate"),
                self.perception_kernels,
                groups=self.config.state_channels,
            )
            update = self.update(torch.cat((perceived, conditions), dim=1))
            next_state = (state + self.config.step_size * update).clamp(
                -self.config.state_limit, self.config.state_limit
            )
            penalties.append((next_state - state).square().mean())
            state = next_state
            predictions.append(state[:, 0].clamp(-1, 1))
        return ForecastOutput(torch.stack(predictions, dim=1), torch.stack(penalties).mean())


class SummaryConvGRU(nn.Module):
    """Local ConvGRU with recurrent predictions and a fixed history slope input."""

    def __init__(self, config: ModelConfig) -> None:
        super().__init__()
        self.config = config
        self.encoder = _encoder(config.state_channels, config.hidden_channels)
        self.gates = _spatial_conv(config.state_channels + 2, config.state_channels * 2)
        self.candidate = _spatial_conv(config.state_channels + 2, config.state_channels)
        self.head = _spatial_conv(config.state_channels, 1)
        nn.init.zeros_(self.head.weight)
        if self.head.bias is not None:
            nn.init.zeros_(self.head.bias)

    def forward(self, history: Tensor, horizon: int) -> ForecastOutput:
        _check_horizon(horizon)
        conditions = summary_conditions(history)
        hidden = self.encoder(conditions).tanh()
        current = conditions[:, :1]
        slope = conditions[:, 1:2]
        predictions = []
        penalties = []
        for _ in range(horizon):
            inputs = torch.cat((current, slope), dim=1)
            reset, update = self.gates(torch.cat((inputs, hidden), dim=1)).sigmoid().chunk(2, 1)
            candidate = self.candidate(torch.cat((inputs, reset * hidden), dim=1)).tanh()
            next_hidden = (1 - update) * hidden + update * candidate
            penalties.append((next_hidden - hidden).square().mean())
            hidden = next_hidden
            current = (current + self.config.step_size * self.head(hidden)).clamp(-1, 1)
            predictions.append(current[:, 0])
        return ForecastOutput(torch.stack(predictions, dim=1), torch.stack(penalties).mean())


def build_model(kind: str, config: dict[str, Any]) -> nn.Module:
    settings = ModelConfig.from_dict(config)
    if kind in ("nca", "nca_regularized"):
        return LocalNCA(settings)
    if kind == "convgru":
        return SummaryConvGRU(settings)
    raise ValueError(f"unknown model kind: {kind!r}")
