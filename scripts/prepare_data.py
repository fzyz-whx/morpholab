"""Prepare all 62 verified Zenodo sequences under ADR-0001, with frozen project splits."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
import zipfile
from collections import Counter
from importlib import import_module
from pathlib import Path
from typing import Any

import numpy as np
from morpholab_ml.data.preparation import (
    PROTOCOL,
    QC_PARAMETERS,
    prepare_sequence,
    reference_fingerprint,
    split_assignments,
    window_starts,
)

# Support both `python -m scripts.prepare_data` and direct `python scripts/prepare_data.py`.
audit_source = import_module("scripts.audit_data" if __package__ else "audit_data")
EXPECTED_SHA256 = audit_source.EXPECTED_SHA256
SOURCE_ID = audit_source.SOURCE_ID
paired_members = audit_source.paired_members
read_stack = audit_source.read_stack
safe_members = audit_source.safe_members
sha256_file = audit_source.sha256_file

ROOT = Path(__file__).resolve().parents[1]


def write_json(path: Path, value: Any) -> None:
    payload = json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_text(encoding="utf-8") == payload:
        return
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(payload, encoding="utf-8")
    temporary.replace(path)


def member_hash(archive: zipfile.ZipFile, info: zipfile.ZipInfo) -> str:
    digest = hashlib.sha256()
    with archive.open(info) as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(archive_path: Path, output: Path, freeze_path: Path) -> dict[str, Any]:
    if sha256_file(archive_path) != EXPECTED_SHA256:
        raise ValueError("Source archive SHA256 differs from audited fixed source")
    sequences = []
    split_records = []
    reason_counts: Counter[str] = Counter()
    fingerprints = {}
    with zipfile.ZipFile(archive_path) as archive:
        members = safe_members(archive)
        pairs, unexpected = paired_members(members)
        if unexpected or any(set(pair) != {"image", "annotation"} for pair in pairs.values()):
            raise ValueError(
                "Archive has unexpected or unpaired sources; no sequences may be dropped"
            )
        assignments = split_assignments(list(pairs))
        for sequence_id in sorted(pairs):
            pair = pairs[sequence_id]
            image, image_axes = read_stack(archive, members[pair["image"]])
            annotation, annotation_axes = read_stack(archive, members[pair["annotation"]])
            arrays, qc = prepare_sequence(image, annotation)
            fingerprints[sequence_id] = reference_fingerprint(image)
            relative = f"sequences/{sequence_id}.npz"
            destination = output / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            temporary = destination.with_suffix(".npz.tmp")
            with temporary.open("wb") as stream:
                np.savez_compressed(stream, **arrays)
            output_hash = sha256_file(temporary)
            if destination.exists() and sha256_file(destination) == output_hash:
                temporary.unlink()
            else:
                temporary.replace(destination)
            source = {
                "image_member": pair["image"],
                "annotation_member": pair["annotation"],
                "image_member_sha256": member_hash(archive, members[pair["image"]]),
                "annotation_member_sha256": member_hash(archive, members[pair["annotation"]]),
                "image_axes": image_axes,
                "annotation_axes": annotation_axes,
            }
            invalid = [entry for entry in qc if not entry["valid"]]
            for entry in invalid:
                reason_counts.update(entry["reasons"])
            record = {
                "sequence_id": sequence_id,
                "experiment_id": sequence_id,
                "grouping_basis": "source_sequence_proxy",
                "project_split": assignments[sequence_id],
                "official_split": None,
                "frame_count": len(image),
                "valid_frame_count": int(arrays["valid"].sum()),
                "invalid_frame_indices": [entry["source_frame_index"] for entry in invalid],
                "invalid_frame_qc": invalid,
                "npz_relpath": relative,
                "output_file_sha256": output_hash,
                "source": source,
                "timestamp_min": None,
                "pixel_size_um": None,
                "provenance": "REAL_OBSERVED",
                "target_provenance": "DERIVED_ANNOTATION",
                "arrays": {
                    name: {"shape": list(array.shape), "dtype": str(array.dtype)}
                    for name, array in arrays.items()
                },
                "windows": {
                    f"L4_H{horizon}_stride1": len(window_starts(arrays["valid"], 4, horizon))
                    for horizon in (4, 12, 24)
                },
            }
            sequences.append(record)
            split_records.append(
                {
                    "sequence_id": sequence_id,
                    "project_split": assignments[sequence_id],
                    "official_split": None,
                    "source_image_member_sha256": source["image_member_sha256"],
                    "source_annotation_member_sha256": source["annotation_member_sha256"],
                }
            )
            print(
                f"{sequence_id}: {record['valid_frame_count']}/{len(image)} valid, "
                f"split={record['project_split']}",
                flush=True,
            )
    manifest = {
        "schema_version": "morpholab-preparation-v1",
        "protocol": PROTOCOL,
        "source_archive": {"source_id": SOURCE_ID, "sha256": EXPECTED_SHA256},
        "biology_domain": "drosophila_embryo_in_vivo_laser_wound",
        "qc_parameters": QC_PARAMETERS,
        "split_counts": dict(Counter(assignments.values())),
        "totals": {
            "sequences": len(sequences),
            "frames": sum(record["frame_count"] for record in sequences),
            "valid_frames": sum(record["valid_frame_count"] for record in sequences),
            "invalid_reason_counts": dict(reason_counts),
        },
        "sequences": sequences,
    }
    freeze = {
        "protocol": PROTOCOL,
        "official_split": None,
        "source_id": SOURCE_ID,
        "source_archive_sha256": EXPECTED_SHA256,
        "grouping_basis": "source_sequence_proxy",
        "rule": (
            "Test01..05 holdout; remaining IDs sorted by sha256(protocol + ':' + ID); "
            "first 12 validation, rest train"
        ),
        "sequences": split_records,
    }
    if freeze_path.exists() and json.loads(freeze_path.read_text(encoding="utf-8")) != freeze:
        raise ValueError("Frozen split differs; use a new protocol instead of overwriting history")
    write_json(freeze_path, freeze)
    write_json(output / "manifest.json", manifest)
    candidates = []
    ids = sorted(fingerprints)
    for index, left in enumerate(ids):
        for right in ids[index + 1 :]:
            a, b = fingerprints[left], fingerprints[right]
            if a is None or b is None:
                continue
            similarity = float(np.clip(np.dot(a, b), -1, 1))
            if similarity >= 0.995:
                candidates.append(
                    {
                        "left": left,
                        "right": right,
                        "cosine_similarity": similarity,
                        "cross_project_split": assignments[left] != assignments[right],
                    }
                )
    write_json(
        output / "near-duplicate-screen.json",
        {
            "method": "first/middle/last image 16x16 block means; per-frame centered unit norm",
            "threshold": 0.995,
            "split_changed": False,
            "limitations": (
                "Heuristic candidates only; no proof of biological independence. "
                "May miss shifts, crops or different temporal sampling and flag similar views."
            ),
            "unscorable_sequence_ids": [key for key in ids if fingerprints[key] is None],
            "candidate_pairs": candidates,
        },
    )
    print(f"Near-duplicate heuristic candidates: {len(candidates)}; split unchanged", flush=True)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--archive", type=Path, default=ROOT / "artifacts/raw/zenodo_7660424/Dataset.zip"
    )
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/processed")
    parser.add_argument(
        "--freeze", type=Path, default=ROOT / "datasets/splits/morpholab-split-v1.json"
    )
    args = parser.parse_args()
    started = time.monotonic()
    try:
        manifest = run(args.archive, args.output, args.freeze)
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        print(f"Preparation failed: {type(exc).__name__}: {exc}", flush=True)
        return 1
    print(json.dumps(manifest["totals"], sort_keys=True), flush=True)
    print(f"Elapsed: {time.monotonic() - started:.3f}s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
