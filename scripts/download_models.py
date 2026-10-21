"""Install pinned release weights without executing archive content or overwriting runs."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import stat
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.download_data import download, hashes  # noqa: E402

MEMBER = re.compile(
    r"(?:matrix\.json|README\.md|WEIGHTS-LICENSE\.txt|(?:nca|nca_regularized|convgru|nca_h1)_seed(?:17|29|43)/(?:best\.pt|run\.json|history\.json))"
)


def install_bundle(archive: Path, registry: dict, destination: Path) -> None:
    if (
        archive.stat().st_size != registry["size_bytes"]
        or hashes(archive)["sha256"] != registry["sha256"]
    ):
        raise ValueError("Model archive size or SHA256 mismatch")
    expected = registry["files"]
    if len(expected) != 39 or any(not MEMBER.fullmatch(name) for name in expected):
        raise ValueError("Invalid model bundle member registry")
    with zipfile.ZipFile(archive) as bundle:
        members = bundle.infolist()
        if len(members) != len(expected) or {m.filename for m in members} != set(expected):
            raise ValueError("Unexpected or duplicate model archive members")
        if (
            sum(m.file_size for m in members) != registry["uncompressed_bytes"]
            or registry["uncompressed_bytes"] > 50 * 1024 * 1024
        ):
            raise ValueError("Model archive exceeds extraction budget")
        for member in members:
            if stat.S_ISLNK(member.external_attr >> 16) or member.flag_bits & 1:
                raise ValueError("Links and encrypted model members are forbidden")
            if member.file_size > 8 * 1024 * 1024 or member.compress_size == 0:
                raise ValueError("Invalid model member size")
        destination.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(
            prefix="model-stage-", dir=destination.parent
        ) as temporary:
            stage = Path(temporary) / "verified"
            stage.mkdir()
            for member in members:
                content = bundle.read(member)
                if hashlib.sha256(content).hexdigest() != expected[member.filename]:
                    raise ValueError("Model member SHA256 mismatch")
                target = stage / member.filename
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(content)
            if destination.exists():
                # Original training roots can also contain last.pt; never remove or rewrite them.
                for name, digest in expected.items():
                    if name in {"README.md", "WEIGHTS-LICENSE.txt"}:
                        continue
                    target = destination / name
                    if not target.is_file() or hashes(target)["sha256"] != digest:
                        raise ValueError(
                            "Existing model directory differs; choose a fresh artifacts root"
                        )
                return
            stage.rename(destination)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", type=Path, default=ROOT / "artifacts")
    parser.add_argument("--archive", type=Path, help="Verify a local bundle instead of downloading")
    args = parser.parse_args()
    registry = json.loads((ROOT / "ml/pretrained/forecast-v1.json").read_text(encoding="utf-8"))
    archive = args.archive or args.artifacts / "downloads/morpholab-forecast-v1.zip"
    if args.archive is None:
        download(
            registry["url"],
            archive,
            registry["size_bytes"],
            "md5:" + registry["md5"],
            max_seconds=300,
        )
    install_bundle(archive, registry, args.artifacts / "training/forecast-v1")
    print("Verified model bundle installed or matching training cache reused; no weights executed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
