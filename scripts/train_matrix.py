"""Run the frozen 12-run matrix into a new directory, stopping on the first failure."""

from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=ROOT / "artifacts/processed/manifest.json")
    parser.add_argument("--output", type=Path, required=True, help="New, non-existing matrix root")
    parser.add_argument("--device", default="auto")
    args = parser.parse_args()

    from morpholab_ml.evaluation.runner import git_dirty, read_manifest
    from morpholab_ml.training.runner import atomic_json, load_config, train

    if git_dirty():
        raise ValueError("Commit and synchronize the source before formal training")
    if args.output.exists():
        raise ValueError("Matrix output must not exist; existing runs are never overwritten")
    if len(read_manifest(args.manifest)["sequences"]) != 62:
        raise ValueError("Formal matrix requires the complete 62-sequence manifest")
    base = load_config(ROOT / "ml/configs/forecast-v1.yaml")
    ablation = load_config(ROOT / "ml/configs/forecast-h1-ablation.yaml")
    plan = [(kind, kind, base) for kind in ("nca", "nca_regularized", "convgru")]
    plan.append(("nca_h1", "nca", ablation))
    args.output.mkdir(parents=True)
    matrix = {"status": "running", "expected_runs": 12, "runs": []}
    destination = args.output / "matrix.json"
    atomic_json(destination, matrix)
    try:
        for variant, kind, config in plan:
            for seed in config["seeds"]:
                if git_dirty():
                    raise ValueError("Source changed during the matrix; stop before another run")
                run_id = f"{variant}_seed{seed}"
                print(f"START {run_id}", flush=True)
                result = train(
                    args.manifest,
                    args.output / run_id,
                    model_kind=kind,
                    seed=seed,
                    config=config,
                    device=args.device,
                )
                if result["status"] != "complete" or result["git_dirty"]:
                    raise ValueError("Incomplete or dirty training result")
                record = {
                    key: result[key]
                    for key in (
                        "run_id",
                        "status",
                        "git_sha",
                        "git_dirty",
                        "completed_steps",
                        "best_step",
                        "best_validation_loss",
                        "elapsed_seconds",
                        "cuda_peak_allocated_bytes",
                        "checkpoint_sha256",
                    )
                }
                record.update(variant=variant, seed=seed)
                matrix["runs"].append(record)
                atomic_json(destination, matrix)
                print(
                    f"DONE {run_id}: best validation loss={result['best_validation_loss']}",
                    flush=True,
                )
        matrix["status"] = "complete"
    except BaseException:
        matrix["status"] = "failed"
        raise
    finally:
        atomic_json(destination, matrix)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
