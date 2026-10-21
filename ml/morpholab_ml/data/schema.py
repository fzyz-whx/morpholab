"""Contracts for observed sequences; construction does not access the filesystem.

File SHA256 fields hash the encoded file bytes, never a decoded pixel array.
Unknown physical scale and time remain None. Audit records may be unassigned;
call validate_trainable() before feeding a collection to training/evaluation.
"""

from __future__ import annotations

import hashlib
from enum import StrEnum
from pathlib import Path, PurePosixPath
from typing import Annotated, Literal, Self

from PIL import Image
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

Nonempty = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
FileSHA256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]


class AnnotationType(StrEnum):
    SKELETON = "skeleton"
    JUNCTION_SKELETON = "junction_skeleton"
    BOUNDARY = "boundary"
    REGION_MASK = "region_mask"


class AnnotationProvenance(StrEnum):
    SOURCE_ANNOTATION = "source_annotation"
    DERIVED_ANNOTATION = "derived_annotation"
    MANUAL_ANNOTATION = "manual_annotation"


class Split(StrEnum):
    TRAIN = "train"
    VALIDATION = "validation"
    TEST = "test"
    UNASSIGNED = "unassigned"


class GroupingBasis(StrEnum):
    BIOLOGICAL_EXPERIMENT = "biological_experiment"
    SOURCE_SEQUENCE_PROXY = "source_sequence_proxy"


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, frozen=True)


class FrameRecord(Contract):
    frame_index: int = Field(ge=0, strict=True)
    source_frame_index: int = Field(ge=0, strict=True)
    timestamp_min: float | None = None
    image_relpath: str
    annotation_relpath: str
    image_file_sha256: FileSHA256
    annotation_file_sha256: FileSHA256
    annotation_type: AnnotationType
    height: int = Field(gt=0, strict=True)
    width: int = Field(gt=0, strict=True)
    pixel_size_um: float | None = Field(default=None, gt=0)
    provenance: Literal["REAL_OBSERVED"]
    annotation_provenance: AnnotationProvenance
    annotation_source: Nonempty

    @field_validator("image_relpath", "annotation_relpath")
    @classmethod
    def safe_relative_path(cls, value: str) -> str:
        path = PurePosixPath(value)
        if (
            not value
            or "\\" in value
            or ":" in value
            or "\x00" in value
            or path.is_absolute()
            or any(part in ("", ".", "..") for part in value.split("/"))
        ):
            raise ValueError("Use a safe, canonical POSIX relative file path")
        return value


class SequenceRecord(Contract):
    sequence_id: Nonempty
    experiment_id: Nonempty
    dataset_id: Nonempty
    biology_domain: Nonempty
    grouping_basis: GroupingBasis
    split: Split = Split.UNASSIGNED
    frames: tuple[FrameRecord, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_frame_order(self) -> Self:
        shape = (self.frames[0].height, self.frames[0].width)
        last_time: float | None = None
        for index, frame in enumerate(self.frames):
            if (frame.height, frame.width) != shape:
                raise ValueError("All frames of a sequence must have identical dimensions")
            if index:
                previous = self.frames[index - 1]
                if frame.frame_index != previous.frame_index + 1:
                    raise ValueError("frame_index must be strictly increasing and continuous")
                if frame.source_frame_index != previous.source_frame_index + 1:
                    raise ValueError(
                        "source_frame_index must be strictly increasing and continuous"
                    )
            if frame.timestamp_min is not None:
                if last_time is not None and frame.timestamp_min <= last_time:
                    raise ValueError("Known timestamps must be strictly increasing")
                last_time = frame.timestamp_min
        return self

    def validate_trainable(self) -> Self:
        if self.split == Split.UNASSIGNED:
            raise ValueError(f"Unassigned sequence cannot be used for training: {self.sequence_id}")
        return self

    def validate_files(self, root: Path) -> Self:
        root = _validated_root(root)
        for frame in self.frames:
            for relative_path, expected_hash in (
                (frame.image_relpath, frame.image_file_sha256),
                (frame.annotation_relpath, frame.annotation_file_sha256),
            ):
                path = (root / relative_path).resolve(strict=True)
                if not path.is_relative_to(root) or not path.is_file():
                    raise ValueError(f"File escapes dataset root or is not a file: {relative_path}")
                actual_hash = hashlib.sha256()
                with path.open("rb") as stream:
                    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                        actual_hash.update(chunk)
                if actual_hash.hexdigest() != expected_hash:
                    raise ValueError(f"File SHA256 mismatch: {relative_path}")
                with Image.open(path) as image:
                    image.load()
                    if image.size != (frame.width, frame.height):
                        raise ValueError(f"Decoded image dimensions mismatch: {relative_path}")
        return self


def _validated_root(root: Path) -> Path:
    resolved = Path(root).resolve(strict=True)
    if not resolved.is_dir():
        raise ValueError("Dataset root must be an existing directory")
    return resolved


class DatasetCollection(Contract):
    sequences: tuple[SequenceRecord, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_grouping(self) -> Self:
        sequence_ids: set[str] = set()
        groups: dict[str, Split] = {}
        for sequence in self.sequences:
            if sequence.sequence_id in sequence_ids:
                raise ValueError(f"Duplicate sequence ID: {sequence.sequence_id}")
            sequence_ids.add(sequence.sequence_id)
            previous = groups.setdefault(sequence.experiment_id, sequence.split)
            if previous != sequence.split:
                raise ValueError(f"Experiment crosses splits: {sequence.experiment_id}")
        return self

    def validate_trainable(self) -> Self:
        for sequence in self.sequences:
            sequence.validate_trainable()
        return self

    def validate_files(self, root: Path) -> Self:
        root = _validated_root(root)
        for sequence in self.sequences:
            sequence.validate_files(root)
        return self
