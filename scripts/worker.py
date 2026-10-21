"""Run a single locked CPU worker; restart safely requeues interrupted jobs."""

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> None:
    from backend.app.worker import run_worker

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    artifacts = Path(os.environ.get("MORPHOLAB_ARTIFACTS_ROOT", ROOT / "artifacts"))
    run_worker(artifacts, ROOT / "artifacts/app", once=args.once)


if __name__ == "__main__":
    main()
