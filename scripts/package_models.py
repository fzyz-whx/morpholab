"""Build a deterministic release bundle from all twelve verified best checkpoints."""

import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix-root", type=Path, default=ROOT / "artifacts/training/forecast-v1")
    parser.add_argument("--manifest", type=Path, default=ROOT / "artifacts/processed/manifest.json")
    parser.add_argument(
        "--output", type=Path, default=ROOT / "artifacts/release/morpholab-forecast-v1.zip"
    )
    parser.add_argument("--registry", type=Path, default=ROOT / "ml/pretrained/forecast-v1.json")
    args = parser.parse_args()
    from morpholab_ml.evaluation.learned import checked_matrix

    from scripts.download_data import hashes

    runs = checked_matrix(args.matrix_root, hashes(args.manifest)["sha256"])
    files = {"matrix.json": (args.matrix_root / "matrix.json").read_bytes()}
    for run in runs:
        for name in ("best.pt", "run.json", "history.json"):
            relative = f"{run['metadata']['run_id']}/{name}"
            files[relative] = (args.matrix_root / relative).read_bytes()
    files["WEIGHTS-LICENSE.txt"] = (
        b"MorphoLab Forecast v1 weights: CC BY 4.0.\n"
        b"https://creativecommons.org/licenses/by/4.0/\n"
        b"Models and training: MorphoLab contributors (fzyz-whx), 2026.\n"
        b"Trained on Backova et al. (2023), Zenodo 7660424, CC BY 4.0.\n"
        b"https://doi.org/10.5281/zenodo.7660424\n"
        b"Transforms: contour filling, QC, 64-grid SDF, model training.\n"
        b"No original microscopy TIFFs are included. Source code is separately MIT licensed.\n"
    )
    files["README.md"] = (
        b"# MorphoLab Forecast v1\n\n"
        b"All 12 validation-selected best checkpoints, metadata and numerical histories.\n"
        b"3 seeds per variant; no test selection. Not a clinical or causal model.\n"
        b"See https://github.com/fzyz-whx/morpholab/blob/main/docs/research/model-card.md\n"
        b"Check the pinned archive and member SHA256 values before loading any weights.\n"
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(
        args.output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as bundle:
        for name, content in sorted(files.items()):
            info = zipfile.ZipInfo(name, (2020, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            bundle.writestr(info, content)
    registry = {
        "schema_version": "morpholab-pretrained-v1",
        "url": "https://github.com/fzyz-whx/morpholab/releases/download/v0.1.0/morpholab-forecast-v1.zip",
        "size_bytes": args.output.stat().st_size,
        **hashes(args.output),
        "uncompressed_bytes": sum(map(len, files.values())),
        "license": "CC-BY-4.0",
        "model_git_sha": runs[0]["metadata"]["git_sha"],
        "files": {name: hashlib.sha256(data).hexdigest() for name, data in sorted(files.items())},
    }
    args.registry.parent.mkdir(parents=True, exist_ok=True)
    args.registry.write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")
    print(f"Bundled {len(runs)} verified best checkpoints; {registry['size_bytes']} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
