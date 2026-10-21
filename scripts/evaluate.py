"""Run deterministic geometric baselines offline; validation is the default split."""

import argparse
import json
from pathlib import Path

from morpholab_ml.evaluation.runner import evaluate, read_manifest, unique_output

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=ROOT / "artifacts/processed/manifest.json")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--split", choices=["train", "validation", "test"], default="validation")
    parser.add_argument("--observations", type=int, default=4)
    parser.add_argument("--horizons", type=int, nargs="+", default=[4, 12, 24])
    parser.add_argument("--stride", type=int, default=12)
    parser.add_argument("--failure-count", type=int, default=3)
    args = parser.parse_args()
    destination = args.output or unique_output(ROOT / "artifacts/experiments")
    try:
        if len(read_manifest(args.manifest)["sequences"]) != 62:
            raise ValueError("Research CLI requires the complete 62-sequence manifest")
        result = evaluate(
            args.manifest,
            destination,
            split=args.split,
            observations=args.observations,
            horizons=tuple(args.horizons),
            stride=args.stride,
            failure_count=args.failure_count,
        )
    except (OSError, ValueError, KeyError) as exc:
        print(f"Evaluation failed: {type(exc).__name__}: {exc}", flush=True)
        return 1
    print(json.dumps(result["summary"]["endpoints"], indent=2), flush=True)
    print(f"Output: {destination}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
