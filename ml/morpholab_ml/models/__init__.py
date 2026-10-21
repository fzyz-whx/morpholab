"""Local, history-conditioned shape forecasting models (optional PyTorch extra)."""

from .forecast import ForecastOutput, ModelConfig, build_model, summary_conditions

__all__ = ["ForecastOutput", "ModelConfig", "build_model", "summary_conditions"]
