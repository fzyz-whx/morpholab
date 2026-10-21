"""Evaluate all frozen three-seed models; validation by default, test only when explicit."""

import argparse
from pathlib import Path

from morpholab_ml.evaluation.learned import evaluate_models
from morpholab_ml.evaluation.runner import PROJECT_ROOT, unique_output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest", type=Path, default=PROJECT_ROOT / "artifacts/processed/manifest.json"
    )
    parser.add_argument(
        "--matrix-root", type=Path, default=PROJECT_ROOT / "artifacts/training/forecast-v1"
    )
    parser.add_argument("--split", choices=("validation", "test"), default="validation")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--device", default="auto")
    args = parser.parse_args()
    destination = args.output or unique_output(PROJECT_ROOT / "artifacts/experiments/forecasts")
    evaluate_models(
        args.manifest, args.matrix_root, destination, split=args.split, device=args.device
    )
    print(f"Complete: {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
