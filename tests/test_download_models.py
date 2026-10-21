"""Synthetic byte bundles test safe installation; they are never loaded as models."""

import hashlib
import json
import zipfile

import pytest

from scripts.download_data import hashes
from scripts.download_models import install_bundle


@pytest.fixture
def bundle(tmp_path):
    files = {"matrix.json": b"{}", "README.md": b"SYNTHETIC", "WEIGHTS-LICENSE.txt": b"fixture"}
    for variant in ("nca", "nca_regularized", "convgru", "nca_h1"):
        for seed in (17, 29, 43):
            for name in ("best.pt", "run.json", "history.json"):
                files[f"{variant}_seed{seed}/{name}"] = b"SYNTHETIC fixture bytes"
    archive = tmp_path / "fixture.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zipped:
        for name, content in files.items():
            zipped.writestr(name, content)
    registry = {
        "size_bytes": archive.stat().st_size,
        "sha256": hashes(archive)["sha256"],
        "uncompressed_bytes": sum(map(len, files.values())),
        "files": {name: hashlib.sha256(content).hexdigest() for name, content in files.items()},
    }
    return archive, registry, tmp_path / "installed"


def test_install_is_verified_idempotent_and_preserves_extra_files(bundle):
    archive, registry, destination = bundle
    install_bundle(archive, registry, destination)
    (destination / "last.pt").write_bytes(b"existing extra checkpoint")
    install_bundle(archive, registry, destination)
    assert (destination / "last.pt").read_bytes() == b"existing extra checkpoint"
    assert len(list(destination.glob("*/best.pt"))) == 12


@pytest.mark.parametrize("corruption", ["archive", "member", "path", "budget", "overwrite"])
def test_refuses_corrupt_or_unsafe_install_without_overwriting(bundle, corruption):
    archive, registry, destination = bundle
    if corruption == "archive":
        registry["sha256"] = "0" * 64
    elif corruption == "member":
        registry["files"]["nca_seed17/best.pt"] = "0" * 64
    elif corruption == "path":
        registry["files"]["../escape.pt"] = registry["files"].pop("nca_seed17/best.pt")
    elif corruption == "budget":
        registry["uncompressed_bytes"] = 100 * 1024 * 1024
    else:
        destination.mkdir()
        (destination / "matrix.json").write_text("PRESERVE ME")
    with pytest.raises(ValueError):
        install_bundle(archive, registry, destination)
    if corruption == "overwrite":
        assert (destination / "matrix.json").read_text() == "PRESERVE ME"
    else:
        assert not destination.exists()
    assert not (destination.parent / "escape.pt").exists()


def test_published_registry_matches_public_training_hashes():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    registry = json.loads((root / "ml/pretrained/forecast-v1.json").read_text())
    records = json.loads((root / "docs/research/results/training-budget-v1.json").read_text())
    for run in records["runs"]:
        assert registry["files"][run["run_id"] + "/best.pt"] == run["checkpoint_sha256"]["best.pt"]
