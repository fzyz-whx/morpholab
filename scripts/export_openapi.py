"""Export the actual FastAPI schema; --check detects a stale committed contract."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    from backend.app.main import app

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    destination = ROOT / "docs/architecture/openapi.json"
    text = json.dumps(app.openapi(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.check:
        if not destination.is_file() or destination.read_text(encoding="utf-8") != text:
            print(
                "OpenAPI snapshot is stale; run scripts/export_openapi.py and frontend api:generate"
            )
            return 1
        print("OpenAPI snapshot matches the actual response/request models")
    else:
        destination.write_text(text, encoding="utf-8")
        print("Exported docs/architecture/openapi.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
