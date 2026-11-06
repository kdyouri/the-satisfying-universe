from decimal import Decimal
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CreativeBrief(StrictModel):
    concept: str = Field(min_length=3, max_length=300)
    category: str = Field(min_length=3, max_length=100)
    title: str = Field(min_length=3, max_length=100)
    description: str = Field(min_length=1, max_length=2000)
    hashtags: list[str] = Field(max_length=12)
    video_prompt: str = Field(min_length=30, max_length=12000)
    duration_seconds: int = Field(ge=15, le=20)
    aspect_ratio: Literal["9:16"] = "9:16"
    style: str = "ultra-realistic macro photography"


class QualityScores(StrictModel):
    visual_realism: int = Field(ge=0, le=25)
    motion_quality: int = Field(ge=0, le=20)
    aesthetic_quality: int = Field(ge=0, le=20)
    prompt_compliance: int = Field(ge=0, le=20)
    technical_quality: int = Field(ge=0, le=15)
    technical_pass: bool
    severe_defects: list[str] = Field(default_factory=list)

    @property
    def total(self) -> int:
        return sum(
            (
                self.visual_realism,
                self.motion_quality,
                self.aesthetic_quality,
                self.prompt_compliance,
                self.technical_quality,
            )
        )

    @property
    def approved(self) -> bool:
        return self.technical_pass and not self.severe_defects and self.total >= 80


class ReviewIssue(StrictModel):
    start_seconds: float = Field(ge=0, le=20.05, allow_inf_nan=False)
    end_seconds: float = Field(ge=0, le=20.05, allow_inf_nan=False)
    severity: Literal["minor", "major"]
    visibility: Literal["normal_playback", "inspection_only", "uncertain"]
    remedy: Literal["local_edit", "manual_review"]
    description: str = Field(min_length=5, max_length=500)
    evidence: str = Field(min_length=10, max_length=1000)

    @model_validator(mode="after")
    def ordered_interval(self):
        if self.end_seconds < self.start_seconds:
            raise ValueError("Issue end must follow its start")
        return self


class PracticalReview(QualityScores):
    issues: list[ReviewIssue] = Field(default_factory=list, max_length=20)
    audio_coherence: Literal["coherent", "problem", "not_observable"]

    def decision(self, *, technical_pass: bool, duration_seconds: float) -> str:
        if not technical_pass:
            return "technical_failed"
        if any(issue.end_seconds > duration_seconds + 1 / 30 for issue in self.issues):
            return "manual_review"
        major = [
            issue
            for issue in self.issues
            if issue.severity == "major" and issue.visibility == "normal_playback"
        ]
        if major:
            return (
                "local_edit"
                if all(issue.remedy == "local_edit" for issue in major)
                else "manual_review"
            )
        if (
            self.total < 80
            or not self.technical_pass
            or self.severe_defects
            or self.audio_coherence != "coherent"
            or any(issue.visibility == "uncertain" for issue in self.issues)
        ):
            return "manual_review"
        return "accepted"

    @property
    def approved(self) -> bool:
        return (
            self.decision(technical_pass=self.technical_pass, duration_seconds=20.05) == "accepted"
        )


class ClipRequest(StrictModel):
    model: str
    prompt: str = Field(min_length=30)
    duration: int = Field(gt=0)
    resolution: str
    aspect_ratio: Literal["9:16"] = "9:16"
    generate_audio: bool = False


class VideoCapability(BaseModel):
    # Providers may add fields; known fields are validated, unknowns are preserved in evidence.
    id: str
    supported_durations: list[int]
    supported_resolutions: list[str]
    supported_aspect_ratios: list[str]
    generate_audio: bool | None = None
    pricing_skus: dict[str, Decimal] | None = None

    def validate_request(self, request: ClipRequest) -> None:
        if request.model != self.id:
            raise ValueError("Model capability does not match request")
        if request.generate_audio and self.generate_audio is not True:
            raise ValueError("Audio generation support is not verified")
        for field, allowed in (
            ("duration", self.supported_durations),
            ("resolution", self.supported_resolutions),
            ("aspect_ratio", self.supported_aspect_ratios),
        ):
            if getattr(request, field) not in allowed:
                raise ValueError(f"Unsupported {field}: {getattr(request, field)}")


class VideoProvider(Protocol):
    """Contract only. No live implementation or paid call in milestone 1."""

    def capabilities(self) -> list[VideoCapability]: ...
    def submit(self, request: ClipRequest, operation_key: str) -> str: ...
    def poll(self, remote_job_id: str) -> dict: ...
    def download(self, remote_job_id: str, destination: str) -> str: ...


class Publisher(Protocol):
    """Implement separately per platform, with reconciliation before upload retry."""

    def verify_access(self, account_id: str) -> dict: ...
    def publish(self, video_id: str, account_id: str) -> dict: ...
    def reconcile(self, publication_id: str) -> dict: ...
