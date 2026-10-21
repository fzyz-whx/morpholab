"""Train an ADR-0002 local forecasting model without opening test arrays."""

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=ROOT / "artifacts/processed/manifest.json")
    parser.add_argument("--config", type=Path, default=ROOT / "ml/configs/forecast-v1.yaml")
    parser.add_argument("--model", choices=["nca", "nca_regularized", "convgru"], default="nca")
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--steps", type=int)
    parser.add_argument("--batch-size", type=int)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--resume", type=Path, help="Path to last.pt in the existing run directory")
    args = parser.parse_args()
    try:
        from morpholab_ml.evaluation.runner import read_manifest, unique_output
        from morpholab_ml.training.runner import load_config, train

        if len(read_manifest(args.manifest)["sequences"]) != 62:
            raise ValueError("Research CLI requires the complete 62-sequence manifest")
        output = args.output or (
            args.resume.parent if args.resume else unique_output(ROOT / "artifacts/training")
        )
        result = train(
            args.manifest,
            output,
            model_kind=args.model,
            seed=args.seed,
            config=load_config(args.config),
            steps=args.steps,
            batch_size=args.batch_size,
            device=args.device,
            resume=args.resume,
        )
    except (ImportError, OSError, ValueError, RuntimeError, KeyError) as exc:
        print(f"Training failed: {type(exc).__name__}: {exc}", flush=True)
        return 1
    print(
        json.dumps(
            {
                key: result[key]
                for key in (
                    "run_id",
                    "status",
                    "completed_steps",
                    "best_step",
                    "best_validation_loss",
                    "elapsed_seconds",
                    "device",
                )
            },
            indent=2,
        ),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
