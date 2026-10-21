"""Audit paired TIFF stacks without extracting or executing archive members.

The source describes videos: stack slices are explicitly treated as ordered time
indices, even when ImageJ axes say channels/depth. Physical times and official
train/validation/test assignments remain unknown. Filled regions are diagnostic
derivations, never relabeled as original annotations or exported as ground truth.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import re
import stat
import zipfile
from collections import defaultdict
from pathlib import Path, PurePosixPath
from typing import Any

import numpy as np
import tifffile
from PIL import Image, ImageDraw
from scipy import ndimage

MAX_MEMBER_BYTES = 128 * 1024 * 1024
MAX_TOTAL_BYTES = 1024 * 1024 * 1024
MAX_MEMBERS = 1000
MAX_RATIO = 500
SOURCE_ID = "zenodo:7660424"
EXPECTED_SHA256 = "0f74010ea3eb5820176c1c04a1804928efe23002dde3c2429e1c90defb497e57"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def safe_members(archive: zipfile.ZipFile) -> dict[str, zipfile.ZipInfo]:
    """Validate all members before reading; directories are never extracted."""
    infos = archive.infolist()
    if len(infos) > MAX_MEMBERS:
        raise ValueError("archive member count exceeds limit")
    total = 0
    members: dict[str, zipfile.ZipInfo] = {}
    canonical: set[str] = set()
    for info in infos:
        path = PurePosixPath(info.filename)
        if (
            "\\" in info.orig_filename
            or path.is_absolute()
            or ".." in path.parts
            or ":" in info.filename
            or "\x00" in info.orig_filename
            or not path.parts
        ):
            raise ValueError("unsafe archive member path")
        name = path.as_posix().rstrip("/").casefold()
        if name in canonical:
            raise ValueError("duplicate archive member path")
        canonical.add(name)
        mode = info.external_attr >> 16
        if stat.S_ISLNK(mode) or info.flag_bits & 1:
            raise ValueError("symlink or encrypted archive member is unsupported")
        total += info.file_size
        if info.file_size > MAX_MEMBER_BYTES or total > MAX_TOTAL_BYTES:
            raise ValueError("archive uncompressed size exceeds limit")
        if info.file_size > max(info.compress_size, 1) * MAX_RATIO:
            raise ValueError("archive compression ratio exceeds limit")
        if not info.is_dir():
            members[info.filename] = info
    return members


def read_stack(archive: zipfile.ZipFile, info: zipfile.ZipInfo) -> tuple[np.ndarray, str]:
    with archive.open(info) as stream:
        payload = stream.read(MAX_MEMBER_BYTES + 1)
    if len(payload) > MAX_MEMBER_BYTES or len(payload) != info.file_size:
        raise ValueError("archive member length mismatch")
    with tifffile.TiffFile(io.BytesIO(payload), is_ome=False) as tiff:
        if len(tiff.series) != 1:
            raise ValueError("TIFF must contain one unambiguous series")
        series = tiff.series[0]
        if (
            len(series.shape) != 3
            or math.prod(series.shape) * series.dtype.itemsize > MAX_MEMBER_BYTES
        ):
            raise ValueError("TIFF must be a bounded three-dimensional stack")
        if series.dtype.kind not in "buif":
            raise ValueError("unsupported TIFF pixel type")
        axes = series.axes
        array = series.asarray()
    if array.nbytes > MAX_MEMBER_BYTES or not np.isfinite(array).all():
        raise ValueError("TIFF has excessive decoded size or non-finite pixels")
    return array, axes


def normalize_annotation(array: np.ndarray) -> tuple[np.ndarray, list[int]]:
    values = np.unique(array)
    if not np.isin(values, [0, 1, 255]).all() or (1 in values and 255 in values):
        raise ValueError("annotation is not a consistent supported binary encoding")
    return array != 0, [int(value) for value in values]


def frame_hash(array: np.ndarray) -> str:
    """Hash C-order pixel bytes; dtype and shape accompany every hash."""
    return hashlib.sha256(np.ascontiguousarray(array).tobytes()).hexdigest()


def annotation_metrics(mask: np.ndarray) -> dict[str, Any]:
    neighbors = ndimage.convolve(
        mask.astype(np.uint8), np.ones((3, 3), dtype=np.uint8), mode="constant"
    ) - mask.astype(np.uint8)
    components = int(ndimage.label(mask, np.ones((3, 3)))[1])
    filled = ndimage.binary_fill_holes(mask)
    holes = filled & ~mask
    # Filling uses 4-connected background; foreground components use 8-connectivity.
    hole_count = int(ndimage.label(holes)[1])
    pixels = int(mask.sum())
    endpoints = int(((neighbors == 1) & mask).sum())
    branch_pixels = int(((neighbors >= 3) & mask).sum())
    edge = np.concatenate((mask[0], mask[-1], mask[1:-1, 0], mask[1:-1, -1]))
    return {
        "annotation_nonzero_pixels": pixels,
        "components_8_connected": components,
        "endpoints_8_neighbor": endpoints,
        "branch_pixels_8_neighbor": branch_pixels,
        "isolated_pixels": int(((neighbors == 0) & mask).sum()),
        "filled_area_pixels_derived": int(filled.sum()),
        "enclosed_background_components_4_connected": hole_count,
        "border_annotation_pixels": int(edge.sum()),
        "touches_border": bool(edge.any()),
        "empty_annotation": pixels == 0,
        "single_closed_curve_candidate": bool(
            pixels and components == 1 and endpoints == 0 and branch_pixels == 0 and hole_count == 1
        ),
    }


def sequence_order(sequence_id: str) -> tuple[str, int]:
    match = re.fullmatch(r"([A-Za-z]+)(\d+)", sequence_id)
    if match is None:
        raise ValueError("unexpected sequence identifier")
    return match.group(1), int(match.group(2))


def paired_members(
    members: dict[str, zipfile.ZipInfo],
) -> tuple[dict[str, dict[str, str]], list[str]]:
    pairs: dict[str, dict[str, str]] = defaultdict(dict)
    unexpected = []
    for name in members:
        path = PurePosixPath(name)
        if (
            len(path.parts) != 2
            or path.parts[0] not in {"Videos", "Segmentations"}
            or path.suffix.lower() not in {".tif", ".tiff"}
            or re.fullmatch(r"(?:WHu?|Test)\d+", path.stem) is None
        ):
            unexpected.append(name)
            continue
        role = "image" if path.parts[0] == "Videos" else "annotation"
        if role in pairs[path.stem]:
            raise ValueError("ambiguous sequence pair")
        pairs[path.stem][role] = name
    return dict(pairs), unexpected


def save_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def sample_sequence(
    sequence_id: str,
    image: np.ndarray,
    annotation: np.ndarray,
    sample_dir: Path,
    image_member: str,
    annotation_member: str,
) -> tuple[list[dict[str, Any]], list[Image.Image]]:
    records = []
    tiles = []
    destination = sample_dir / sequence_id
    destination.mkdir(parents=True, exist_ok=True)
    low, high = np.percentile(image[:6], [1, 99.5])
    for index in range(min(6, len(image))):
        original = image[index]
        label = annotation[index]
        if original.dtype != np.uint16 or label.dtype != np.uint8:
            raise ValueError("PNG samples require source uint16 images and uint8 annotations")
        image_path = destination / f"t{index:04d}_image.png"
        annotation_path = destination / f"t{index:04d}_annotation.png"
        Image.fromarray(original).save(image_path)
        Image.fromarray(label).save(annotation_path)
        # Verify pixel-preserving PNG export rather than assuming a successful save.
        with Image.open(image_path) as saved:
            if not np.array_equal(np.asarray(saved), original):
                raise ValueError("image PNG pixel round-trip mismatch")
        with Image.open(annotation_path) as saved:
            if not np.array_equal(np.asarray(saved), label):
                raise ValueError("annotation PNG pixel round-trip mismatch")
        records.append(
            {
                "source_id": SOURCE_ID,
                "sequence_id": sequence_id,
                "time_index": index,
                "frame_index": index,
                "source_frame_index": index,
                "physical_time_seconds": None,
                "split": "unknown",
                "provenance": "REAL_OBSERVED",
                "annotation_provenance": "source_annotation",
                "annotation_source": "original publisher TIFF slice; encoding retained",
                "image_dtype": str(original.dtype),
                "annotation_dtype": str(label.dtype),
                "frame_shape": list(original.shape),
                "image_member": image_member,
                "annotation_member": annotation_member,
                "image_pixels_sha256": frame_hash(original),
                "annotation_pixels_sha256": frame_hash(label),
                "image_png": image_path.relative_to(sample_dir).as_posix(),
                "annotation_png": annotation_path.relative_to(sample_dir).as_posix(),
                "image_png_sha256": sha256_file(image_path),
                "annotation_png_sha256": sha256_file(annotation_path),
                "image_file_sha256": sha256_file(image_path),
                "annotation_file_sha256": sha256_file(annotation_path),
            }
        )
        gray = np.clip((original.astype(np.float64) - low) / max(high - low, 1) * 255, 0, 255)
        display = np.repeat(gray.astype(np.uint8)[..., None], 3, axis=2)
        display[label != 0] = [255, 90, 40]
        tile = Image.new("RGB", (256, 284), "#151b22")
        tile.paste(Image.fromarray(display).resize((256, 256)), (0, 28))
        ImageDraw.Draw(tile).text(
            (5, 7), f"{sequence_id} t={index} OBSERVED+ANNOTATION", fill="white"
        )
        tiles.append(tile)
    return records, tiles


def duplicate_groups(rows: list[dict[str, Any]], role: str) -> dict[str, Any]:
    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        digest = (
            row["annotation_binary_sha256"]
            if role == "annotation_binary"
            else row[f"{role}_pixels_sha256"]
        )
        dtype = "uint8" if role == "annotation_binary" else row[f"{role}_dtype"]
        key = (digest, dtype, str(row["frame_shape"]))
        groups[key].append(row)
    cross_sequence = []
    within_sequence_repeated_frames = 0
    for (digest, dtype, shape), group in groups.items():
        sequences = {row["sequence_id"] for row in group}
        if len(group) > 1:
            within_sequence_repeated_frames += len(group) - len(sequences)
        if len(sequences) > 1:
            cross_sequence.append(
                {
                    "sha256": digest,
                    "dtype": dtype,
                    "frame_shape": shape,
                    "empty_annotation": all(row["empty_annotation"] for row in group)
                    if role.startswith("annotation")
                    else None,
                    "occurrences": [
                        {"sequence_id": row["sequence_id"], "time_index": row["time_index"]}
                        for row in group
                    ],
                }
            )
    return {
        "cross_sequence_group_count": len(cross_sequence),
        "cross_sequence_groups": cross_sequence,
        "within_sequence_repeated_frame_count": within_sequence_repeated_frames,
        "interpretation": (
            "Exact pixel equality only. Annotation equality (especially empty or unchanged labels) "
            "does not establish shared experimental origin or split leakage. "
            "Official splits unknown."
        ),
    }


def audit_archive(
    archive_path: Path,
    output_dir: Path,
    sample_dir: Path,
    sample_ids: tuple[str, ...] = ("WH01", "WHu01"),
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    sequences: list[dict[str, Any]] = []
    samples: list[dict[str, Any]] = []
    tiles: list[Image.Image] = []
    archive_sha = sha256_file(archive_path)
    with zipfile.ZipFile(archive_path) as archive:
        archive_member_count = len(archive.infolist())
        archive_uncompressed_bytes = sum(info.file_size for info in archive.infolist())
        members = safe_members(archive)
        pairs, unexpected = paired_members(members)
        for sequence_id in sorted(pairs, key=sequence_order):
            pair = pairs[sequence_id]
            record: dict[str, Any] = {
                "sequence_id": sequence_id,
                "source_id": SOURCE_ID,
                "split": "unknown",
                "name_hint": "candidate_test" if sequence_id.startswith("Test") else None,
                "image_member": pair.get("image"),
                "annotation_member": pair.get("annotation"),
                "status": "failed",
                "issues": [],
                "physical_frame_interval_seconds": None,
                "pixel_size_um": None,
            }
            sequences.append(record)
            if set(pair) != {"image", "annotation"}:
                record["issues"].append("missing image/annotation pair")
                continue
            try:
                image, image_axes = read_stack(archive, members[pair["image"]])
                annotation, annotation_axes = read_stack(archive, members[pair["annotation"]])
                record.update(
                    image_shape=list(image.shape),
                    annotation_shape=list(annotation.shape),
                    image_dtype=str(image.dtype),
                    annotation_dtype=str(annotation.dtype),
                    image_declared_axes=image_axes,
                    annotation_declared_axes=annotation_axes,
                    axis_interpretation="stack-as-time from source video; slice order retained",
                )
                if image.shape != annotation.shape:
                    raise ValueError("image/annotation stack shape mismatch")
                binary, values = normalize_annotation(annotation)
                record["annotation_values"] = values
                sequence_rows = []
                for index, (frame, label, mask) in enumerate(
                    zip(image, annotation, binary, strict=True)
                ):
                    row = {
                        "source_id": SOURCE_ID,
                        "sequence_id": sequence_id,
                        "time_index": index,
                        "physical_time_seconds": None,
                        "split": "unknown",
                        "image_member": pair["image"],
                        "annotation_member": pair["annotation"],
                        "frame_shape": list(frame.shape),
                        "image_dtype": str(frame.dtype),
                        "annotation_dtype": str(label.dtype),
                        "image_pixels_sha256": frame_hash(frame),
                        "annotation_pixels_sha256": frame_hash(label),
                        "annotation_binary_sha256": frame_hash(mask.astype(np.uint8)),
                        **annotation_metrics(mask),
                    }
                    rows.append(row)
                    sequence_rows.append(row)
                record.update(
                    status="parsed",
                    frame_count=len(image),
                    first_time_index=0,
                    last_time_index=len(image) - 1,
                    empty_frame_count=sum(row["empty_annotation"] for row in sequence_rows),
                    border_frame_count=sum(row["touches_border"] for row in sequence_rows),
                    closed_curve_candidate_count=sum(
                        row["single_closed_curve_candidate"] for row in sequence_rows
                    ),
                    endpoint_frame_count=sum(
                        row["endpoints_8_neighbor"] > 0 for row in sequence_rows
                    ),
                    multiple_component_frame_count=sum(
                        row["components_8_connected"] > 1 for row in sequence_rows
                    ),
                    branch_frame_count=sum(
                        row["branch_pixels_8_neighbor"] > 0 for row in sequence_rows
                    ),
                    annotation_pixels_range=[
                        min(row["annotation_nonzero_pixels"] for row in sequence_rows),
                        max(row["annotation_nonzero_pixels"] for row in sequence_rows),
                    ],
                    filled_area_range_derived=[
                        min(row["filled_area_pixels_derived"] for row in sequence_rows),
                        max(row["filled_area_pixels_derived"] for row in sequence_rows),
                    ],
                )
                if sequence_id in sample_ids:
                    if len(image) < 6:
                        record["issues"].append("sample has fewer than six consecutive frames")
                    extracted, panels = sample_sequence(
                        sequence_id,
                        image,
                        annotation,
                        sample_dir,
                        pair["image"],
                        pair["annotation"],
                    )
                    samples.extend(extracted)
                    tiles.extend(panels)
            except (ValueError, OSError, tifffile.TiffFileError) as error:
                record["status"] = "failed"
                record["issues"].append(str(error))
    report = {
        "schema_version": "0.1",
        "source_id": SOURCE_ID,
        "archive_sha256": archive_sha,
        "matches_known_download_sha256": archive_sha == EXPECTED_SHA256,
        "archive_member_count": archive_member_count,
        "archive_file_member_count": len(members),
        "archive_uncompressed_bytes": archive_uncompressed_bytes,
        "unexpected_members": unexpected,
        "sequence_count": len(sequences),
        "parsed_sequence_count": sum(item["status"] == "parsed" for item in sequences),
        "frame_pair_count": len(rows),
        "split_status": "unknown; no author-provided split mapping located in this archive",
        "time_semantics": {
            "index": "zero-based original TIFF slice order, explicitly interpreted as time",
            "reported_frame_interval_seconds": 60,
            "reported_interval_evidence": "source webpage; encoded per-frame timestamps unverified",
            "verified_physical_interval_seconds": None,
            "caution": "ImageJ axis metadata may encode channel/depth; it does not establish time",
        },
        "annotation_semantics": "Unresolved; inspect statistics and original-overlay QA before ADR",
        "metric_definitions": {
            "normalization": "0 background; original 1 or 255 foreground; source bytes retained",
            "connectivity": "foreground 8-neighbor; fill/holes background 4-neighbor",
            "endpoints": "foreground pixels with exactly one foreground 8-neighbor",
            "branch_pixels": "foreground pixels with >=3 foreground 8-neighbors; not skeletonized",
            "filled_area": "scipy.ndimage.binary_fill_holes area; derived QC, not ground truth",
            "closed_curve_candidate": "one component, no endpoints/branches, one enclosed hole",
            "hashes": "SHA256 of C-order source pixel bytes; shape/dtype required for comparison",
        },
        "totals": {
            key: sum(int(row[key]) for row in rows)
            for key in ["empty_annotation", "touches_border", "single_closed_curve_candidate"]
        },
        "sequences": sequences,
        "duplicates": {
            role: duplicate_groups(rows, role)
            for role in ("image", "annotation", "annotation_binary")
        },
        "sample_sequence_ids": sorted({row["sequence_id"] for row in samples}),
        "qa_display": (
            "first six consecutive slices; 1/99.5 percentiles per sample for display only; "
            "orange original nonzero annotation over observed image; no filled labels exported"
        ),
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    save_json(output_dir / "content-audit.json", report)
    save_json(output_dir / "frame-manifest.json", rows)
    if rows:
        with (output_dir / "frame-manifest.csv").open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    save_json(sample_dir / "sample-manifest.json", samples)
    if tiles:
        sheet = Image.new("RGB", (6 * 256, math.ceil(len(tiles) / 6) * 284), "#151b22")
        for index, tile in enumerate(tiles):
            sheet.paste(tile, ((index % 6) * 256, (index // 6) * 284))
        sheet.save(output_dir / "annotation-contact-sheet.png")
    return report


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--archive", type=Path, default=root / "artifacts/raw/zenodo_7660424/Dataset.zip"
    )
    parser.add_argument("--output", type=Path, default=root / "artifacts/audit")
    parser.add_argument("--sample", type=Path, default=root / "artifacts/sample")
    args = parser.parse_args()
    try:
        report = audit_archive(args.archive, args.output, args.sample)
    except (ValueError, OSError, zipfile.BadZipFile) as error:
        print(f"Content audit failed: {error}")
        return 1
    print(
        f"Parsed {report['parsed_sequence_count']}/{report['sequence_count']} sequences; "
        f"{report['frame_pair_count']} paired frames. Splits and supervision remain unconfirmed."
    )
    return int(
        report["parsed_sequence_count"] != report["sequence_count"]
        or not report["matches_known_download_sha256"]
        or bool(report["unexpected_members"])
    )


if __name__ == "__main__":
    raise SystemExit(main())
