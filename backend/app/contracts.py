"""Typed public prediction contracts; independent of HTTP and optional Torch."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, StringConstraints, model_validator

from backend.app.prediction import PredictionRequest

ModelId = Literal[
    "persistence", "constant_normal_speed", "nca", "nca_regularized", "convgru", "nca_h1"
]
JobStatus = Literal["queued", "running", "succeeded", "failed", "cancelled"]
DatasetId = Literal["drosophila_wound_zenodo_7660424"]
Provenance = Literal[
    "REAL_OBSERVED", "HUMAN_ANNOTATION", "MODEL_PREDICTION", "SYNTHETIC", "IN_SILICO"
]
Sha256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
GitSha = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{40}$")]
Identifier = Annotated[str, StringConstraints(min_length=1, max_length=200)]
Timestamp = Annotated[
    str, StringConstraints(pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|\+00:00)$")
]
Finite = Annotated[float, Field(allow_inf_nan=False)]
Nonnegative = Annotated[float, Field(ge=0, allow_inf_nan=False)]
Probability = Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Selection(Contract):
    criterion: Literal["validation_supervised_loss"]
    loss: Nonnegative | None
    step: Annotated[int, Field(ge=0)] | None


class RegisteredModel(Contract):
    id: ModelId
    label: str
    kind: Literal["baseline", "trained"]
    variant: ModelId | None
    seed: int | None
    trained: bool
    available: bool
    selection: Selection | None
    checkpoint_sha256: Sha256 | None
    run_id: Identifier | None = None
    model_git_sha: GitSha | None = None
    parameter_count: Annotated[int, Field(gt=0)] | None = None
    unavailable_reason: str | None = None


class SafeError(Contract):
    code: Identifier
    message: str
    details: JsonValue = None
    trace_id: str | None = None
    type: str | None = None


class PredictionJob(Contract):
    id: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$")]
    status: JobStatus
    request: PredictionRequest
    created_at_utc: Timestamp
    updated_at_utc: Timestamp
    cancel_requested: bool
    error: SafeError | None
    result_available: bool


class LeadMetrics(Contract):
    iou: Probability
    dice: Probability
    area_mae: Annotated[float, Field(ge=0, le=4096, allow_inf_nan=False)]
    signed_area_error: Annotated[float, Field(ge=-4096, le=4096, allow_inf_nan=False)]
    mean_boundary_distance: Nonnegative
    hausdorff95: Nonnegative
    empty_boundary_mismatch: bool


class ImageAsset(Contract):
    url: Annotated[
        str,
        StringConstraints(
            pattern=r"^/api/v1/jobs/[0-9a-f-]{36}/frames/(?:[1-9]|1[0-9]|2[0-4])\?layer=(?:prediction|target|error)$"
        ),
    ]
    sha256: Sha256


class FrameImages(Contract):
    prediction: ImageAsset
    target: ImageAsset | None
    error: ImageAsset | None


class PredictionFrame(Contract):
    lead: Annotated[int, Field(ge=1, le=24)]
    source_frame_index: Annotated[int, Field(ge=0)]
    contours: list[list[Annotated[list[Finite], Field(min_length=2, max_length=2)]]]
    region_area: Annotated[int, Field(ge=0, le=4096)]
    target_area: Annotated[int, Field(ge=0, le=4096)] | None
    target_valid: bool
    metrics: LeadMetrics | None
    images: FrameImages

    @model_validator(mode="after")
    def target_consistency(self) -> PredictionFrame:
        values = (self.target_area, self.metrics, self.images.target, self.images.error)
        if self.target_valid != all(value is not None for value in values):
            raise ValueError("Valid targets require area, metrics and target/error assets")
        if not self.target_valid and any(value is not None for value in values):
            raise ValueError("Invalid targets must keep target data null")
        return self


class Grid(Contract):
    width: Literal[64]
    height: Literal[64]
    contour_coordinates: Literal["working-grid pixel centers"]


class PredictionSource(Contract):
    source_id: Literal["zenodo:7660424"]
    sequence_id: str
    archive_sha256: Sha256
    manifest_sha256: Sha256
    npz_sha256: Sha256
    original_width: Literal[128]
    original_height: Literal[128]
    project_split: Literal["train", "validation", "test"]


class InferenceEnvironment(Contract):
    deterministic: bool
    cpu_threads: Annotated[int, Field(ge=1)]
    convolution_fp32_precision: Literal["ieee"]


class Envelope(Contract):
    schema_version: Literal["1"]
    provenance: Provenance | None
    dataset_id: str | None
    model_id: ModelId | None
    run_id: Identifier | None
    created_at_utc: Timestamp


class ImplementationIdentity(Contract):
    git_sha: GitSha | None
    git_dirty: bool | None
    files_sha256: dict[str, Sha256]
    environment: dict[str, str | None]


class PredictionResult(Envelope):
    provenance: Literal["MODEL_PREDICTION"]
    dataset_id: DatasetId
    model_id: ModelId
    job_id: str
    status: Literal["succeeded"]
    request: PredictionRequest
    grid: Grid
    source: PredictionSource
    model: RegisteredModel
    frames: Annotated[list[PredictionFrame], Field(min_length=1, max_length=24)]
    target_provenance: Literal["DERIVED_ANNOTATION"]
    device: Literal["cpu"]
    precision: Literal["fp32"]
    inference_environment: InferenceEnvironment
    implementation: ImplementationIdentity | None = None

    @model_validator(mode="after")
    def request_consistency(self) -> PredictionResult:
        if len(self.frames) != self.request.horizon:
            raise ValueError("Result frame count differs from requested horizon")
        if self.model_id != self.request.model_id or self.model.id != self.model_id:
            raise ValueError("Result model differs from request")
        if self.source.sequence_id != self.request.sequence_id:
            raise ValueError("Result sequence differs from request")
        start = self.request.observation_start + self.request.observations
        for index, frame in enumerate(self.frames):
            if frame.lead != index + 1 or frame.source_frame_index != start + index:
                raise ValueError("Result frames must preserve requested source chronology")
        return self


class JobEnvelope(Envelope):
    job: PredictionJob


class ModelListEnvelope(Envelope):
    items: Annotated[list[RegisteredModel], Field(max_length=6)]


class ExperimentListEnvelope(Envelope):
    items: Annotated[list[PredictionJob], Field(max_length=100)]


class ErrorEnvelope(Envelope):
    error: SafeError


class MetadataRecord(Contract):
    """Preserve shareable metadata without weakening the consumed fields."""

    model_config = ConfigDict(extra="allow", strict=True)
    __pydantic_extra__: dict[str, JsonValue] = Field(init=False)


class DatasetRecord(MetadataRecord):
    id: str
    name: str
    biology_domain: str
    source_url: str
    doi: str | None
    license: str | None
    sequence_count: Annotated[int, Field(ge=0)] | None
    frame_count: Annotated[int, Field(ge=0)] | None
    local_available: bool
    annotation_type: str
    model_status: Literal["trained", "untrained"]


class SequenceRecord(MetadataRecord):
    id: str
    dataset_id: str
    frame_count: Annotated[int, Field(gt=0)]
    width: Annotated[int, Field(gt=0)]
    height: Annotated[int, Field(gt=0)]
    project_split: str | None
    official_split: str | None
    qc_valid_count: Annotated[int, Field(ge=0)] | None
    qc_definition: str | None = None


class FrameRecord(MetadataRecord):
    frame_index: Annotated[int, Field(ge=0)]
    timestamp_min: Finite | None
    qc_valid: bool
    touches_border: bool


class DatasetListEnvelope(Envelope):
    items: list[DatasetRecord]


class DatasetEnvelope(Envelope, DatasetRecord):
    model_config = ConfigDict(extra="allow", strict=True)


class SequenceListEnvelope(Envelope):
    items: list[SequenceRecord]


class SequenceEnvelope(Envelope, SequenceRecord):
    model_config = ConfigDict(extra="allow", strict=True)
    dataset_id: str
    frames: list[FrameRecord]
