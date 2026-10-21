"""Bounded local data access; independent of HTTP request handling."""

from __future__ import annotations

import io
import json
import threading
import zipfile
from collections import OrderedDict
from pathlib import Path
from typing import Any

import numpy as np
import yaml
from PIL import Image

from scripts.audit_data import normalize_annotation, read_stack, safe_members, sha256_file

PRIMARY_DATASET = "drosophila_wound_zenodo_7660424"
RECOVERY = ["uv run python scripts/download_data.py", "uv run python scripts/audit_data.py"]
NAMES = {
    PRIMARY_DATASET: "Drosophila embryonic laser-wound videos",
    "in_vitro_wound_gigadb_100118": "In vitro wound-healing time-lapse experiments",
    "collective_cell_migration_bbbc019v2": "BBBC019v2 static collective migration",
}


class DataError(Exception):
    def __init__(self, code: str, message: str, status: int = 503) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status


class DataStore:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.archive = self.root / "artifacts/raw/zenodo_7660424/Dataset.zip"
        self._verified_fingerprint: tuple[int, int, int] | None = None
        self._cache: OrderedDict[str, tuple[np.ndarray, np.ndarray, float, float]] = OrderedDict()
        self._lock = threading.RLock()
        self._json_cache: dict[str, tuple[tuple[int, int], Any]] = {}
        self._rows_source: Any = None
        self._rows_grouped: dict[str, list[dict[str, Any]]] = {}

    def _json(self, relative: str) -> Any:
        try:
            with self._lock:
                path = self.root / relative
                info = path.stat()
                fingerprint = (info.st_size, info.st_mtime_ns)
                cached = self._json_cache.get(relative)
                if cached and cached[0] == fingerprint:
                    return cached[1]
                value = json.loads(path.read_text(encoding="utf-8"))
                self._json_cache[relative] = fingerprint, value
                return value
        except (OSError, ValueError) as error:
            raise DataError(
                "AUDIT_UNAVAILABLE", "Local audit is missing or invalid; run data audit."
            ) from error

    def registry(self) -> list[dict[str, Any]]:
        try:
            value = yaml.safe_load(
                (self.root / "datasets/registry.yaml").read_text(encoding="utf-8")
            )
            return list(value["datasets"])
        except (OSError, ValueError, KeyError, TypeError, yaml.YAMLError) as error:
            raise DataError("REGISTRY_UNAVAILABLE", "Dataset registry is unavailable.") from error

    def summary(self) -> dict[str, Any]:
        return self._json("datasets/audits/zenodo-7660424-summary.json")

    def verified_archive(self) -> None:
        with self._lock:
            try:
                info = self.archive.stat()
                fingerprint = (info.st_size, info.st_mtime_ns, info.st_ctime_ns)
                if self._verified_fingerprint == fingerprint:
                    return
                self._cache.clear()
                self._verified_fingerprint = None
                expected = self.summary()["archive_sha256"]
                if sha256_file(self.archive) != expected:
                    raise DataError(
                        "ARCHIVE_CHECKSUM_MISMATCH", "Local archive failed SHA256 verification."
                    )
                with zipfile.ZipFile(self.archive) as archive:
                    safe_members(archive)
                self._verified_fingerprint = fingerprint
            except DataError:
                raise
            except (OSError, ValueError, KeyError, zipfile.BadZipFile) as error:
                raise DataError(
                    "DATA_UNAVAILABLE", "Verified local dataset archive is unavailable."
                ) from error

    def audit(self) -> dict[str, Any]:
        value = self._json("artifacts/audit/content-audit.json")
        if value.get("archive_sha256") != self.summary()["archive_sha256"]:
            raise DataError("AUDIT_HASH_MISMATCH", "Local audit does not match the pinned archive.")
        return value

    def frame_rows(self) -> dict[str, list[dict[str, Any]]]:
        self.audit()
        rows = self._json("artifacts/audit/frame-manifest.json")
        if rows is self._rows_source:
            return self._rows_grouped
        grouped: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            grouped.setdefault(row["sequence_id"], []).append(row)
        for sequence in self.summary()["sequences"]:
            sequence_rows = grouped.get(sequence["sequence_id"], [])
            if [row["time_index"] for row in sequence_rows] != list(range(sequence["frame_count"])):
                raise DataError("AUDIT_INCOMPLETE", "Audit lacks contiguous source frame records.")
        self._rows_source, self._rows_grouped = rows, grouped
        return grouped

    def prepared_qc(self) -> dict[str, dict[str, Any]]:
        if not (self.root / "artifacts/processed/manifest.json").exists():
            return {}
        prepared = self._json("artifacts/processed/manifest.json")
        if prepared["source_archive"]["sha256"] != self.summary()["archive_sha256"]:
            raise DataError(
                "PREPARATION_MISMATCH", "Prepared QC does not match the source archive."
            )
        return {item["sequence_id"]: item for item in prepared["sequences"]}

    def available(self) -> tuple[bool, str | None]:
        try:
            self.verified_archive()
            self.audit()
            self.frame_rows()
        except DataError as error:
            return False, error.code
        return True, None

    def datasets(self) -> list[dict[str, Any]]:
        available, _ = self.available()
        items = []
        for entry in self.registry():
            is_primary = entry["id"] == PRIMARY_DATASET
            summary = self.summary() if is_primary else {}
            items.append(
                {
                    "id": entry["id"],
                    "name": NAMES.get(entry["id"], entry["id"]),
                    "biology_domain": entry.get("biology_domain"),
                    "domain": entry.get("biology_domain"),
                    "source_url": entry.get("record_url"),
                    "doi": entry.get("doi"),
                    "license": entry.get("license"),
                    "sequence_count": summary.get("sequence_count"),
                    "frame_count": summary.get("frame_pair_count"),
                    "local_available": available if is_primary else False,
                    "annotation_type": entry.get("annotation_type"),
                    "model_status": "untrained",
                    "reported_frame_interval_min": entry.get("reported_frame_interval_min"),
                    "verified_frame_interval_min": None,
                    "official_split": None,
                }
            )
        return items

    def splits(self) -> dict[str, str]:
        path = self.root / "datasets/splits/morpholab-split-v1.json"
        if not path.exists():
            return {}
        value = self._json("datasets/splits/morpholab-split-v1.json")
        # The frozen preparation protocol may represent records or split groups.
        if isinstance(value.get("sequences"), list):
            return {item["sequence_id"]: item["project_split"] for item in value["sequences"]}
        if isinstance(value.get("assignments"), dict):
            return value["assignments"]
        if isinstance(value.get("splits"), dict):
            return {item: split for split, ids in value["splits"].items() for item in ids}
        raise DataError("SPLIT_UNAVAILABLE", "Project split file has an unsupported format.")

    def sequences(self, dataset_id: str) -> list[dict[str, Any]]:
        if dataset_id not in {item["id"] for item in self.registry()}:
            raise DataError("DATASET_NOT_FOUND", "Dataset does not exist.", 404)
        if dataset_id != PRIMARY_DATASET:
            return []
        splits = self.splits()
        prepared = self.prepared_qc()
        try:
            frames = self.frame_rows()
        except DataError:
            frames = {}
        items = []
        for entry in self.summary()["sequences"]:
            rows = frames.get(entry["sequence_id"])
            items.append(
                {
                    "id": entry["sequence_id"],
                    "dataset_id": dataset_id,
                    "frame_count": entry["frame_count"],
                    "height": entry["image_shape"][1],
                    "width": entry["image_shape"][2],
                    "image_dtype": entry["image_dtype"],
                    "annotation_type": "skeletonized_wound_boundary",
                    "project_split": splits.get(entry["sequence_id"], "unassigned"),
                    "official_split": None,
                    "qc_valid_count": prepared[entry["sequence_id"]]["valid_frame_count"]
                    if entry["sequence_id"] in prepared
                    else sum(
                        row["single_closed_curve_candidate"] and not row["touches_border"]
                        for row in rows
                    )
                    if rows is not None
                    else None,
                    "qc_definition": "ADR-0001 source contour and 64x64 target checks"
                    if entry["sequence_id"] in prepared
                    else "source-only: closed curve and no border contact; target QC pending",
                    "timestamp_min": None,
                    "provenance": "REAL_OBSERVED",
                }
            )
        return items

    def sequence(self, sequence_id: str) -> dict[str, Any]:
        for item in self.sequences(PRIMARY_DATASET):
            if item["id"] == sequence_id:
                return item
        raise DataError("SEQUENCE_NOT_FOUND", "Sequence does not exist.", 404)

    def sequence_detail(self, sequence_id: str) -> dict[str, Any]:
        item = self.sequence(sequence_id)
        self.verified_archive()
        rows = self.frame_rows().get(sequence_id, [])
        prepared = self.prepared_qc().get(sequence_id)
        invalid = set(prepared["invalid_frame_indices"]) if prepared else None
        if [row["time_index"] for row in rows] != list(range(item["frame_count"])):
            raise DataError("AUDIT_INCOMPLETE", "Audit does not contain contiguous frame records.")
        return {
            **item,
            "frames": [
                {
                    "frame_index": row["time_index"],
                    "timestamp_min": None,
                    "qc_valid": row["time_index"] not in invalid
                    if invalid is not None
                    else bool(row["single_closed_curve_candidate"] and not row["touches_border"]),
                    "touches_border": row["touches_border"],
                }
                for row in rows
            ],
            "display": {
                "observed": "derived 8-bit display; sequence-wide 1/99.5 percentile contrast",
                "annotation": "original nonzero thin contour, displayed as white on black",
                "overlay": "observed display with original thin contour in #D4DCA5",
                "source_dtype": item["image_dtype"],
                "training_normalization": False,
            },
            "model_status": "untrained",
        }

    def stack(self, sequence_id: str) -> tuple[np.ndarray, np.ndarray, float, float]:
        item = self.sequence(sequence_id)
        with self._lock:
            self.verified_archive()
            self.audit()
            if sequence_id in self._cache:
                self._cache.move_to_end(sequence_id)
                return self._cache[sequence_id]
            try:
                with zipfile.ZipFile(self.archive) as archive:
                    members = safe_members(archive)
                    image, _ = read_stack(archive, members[f"Videos/{sequence_id}.tif"])
                    annotation, _ = read_stack(archive, members[f"Segmentations/{sequence_id}.tif"])
                    binary, _ = normalize_annotation(annotation)
                if image.shape != (item["frame_count"], item["height"], item["width"]):
                    raise ValueError("image shape mismatch")
                if annotation.shape != image.shape:
                    raise ValueError("annotation shape mismatch")
                if str(image.dtype) != item["image_dtype"]:
                    raise ValueError("source image dtype mismatch")
                low, high = np.percentile(image, [1, 99.5])
                image.setflags(write=False)
                binary.setflags(write=False)
                result = image, binary, float(low), float(high)
                self._cache[sequence_id] = result
                if len(self._cache) > 4:
                    self._cache.popitem(last=False)
                return result
            except (KeyError, OSError, ValueError, zipfile.BadZipFile) as error:
                raise DataError(
                    "DATA_INVALID", "Local sequence failed safe decoding or shape checks."
                ) from error

    def frame_png(self, sequence_id: str, frame_index: int, layer: str) -> bytes:
        item = self.sequence(sequence_id)
        if frame_index < 0 or frame_index >= item["frame_count"]:
            raise DataError("FRAME_NOT_FOUND", "Frame index is outside this sequence.", 404)
        image, annotation, low, high = self.stack(sequence_id)
        gray = np.clip(
            (image[frame_index].astype(np.float64) - low) / max(high - low, 1) * 255, 0, 255
        )
        pixels = gray.astype(np.uint8)
        if layer == "annotation":
            pixels = annotation[frame_index].astype(np.uint8) * 255
        elif layer == "overlay":
            pixels = np.repeat(pixels[..., None], 3, axis=2)
            pixels[annotation[frame_index]] = [212, 220, 165]
        output = io.BytesIO()
        Image.fromarray(pixels).save(output, format="PNG")
        return output.getvalue()
