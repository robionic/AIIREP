from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from app.models import JobStatus, ReviewStatus, ReviewerRole


class AssetCreate(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    source_url: HttpUrl
    discipline: str = Field(default="Mechanical", max_length=40)
    high_risk: bool = False


class ComponentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    component_type: str = Field(min_length=1, max_length=80)
    confidence: float = Field(default=0, ge=0, le=1)
    description: str | None = None
    bounding_box: dict[str, float] | None = None
    relationships: list[str] = Field(default_factory=list)


class ComponentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    component_type: str | None = Field(default=None, min_length=1, max_length=80)
    confidence: float | None = Field(default=None, ge=0, le=1)
    description: str | None = None
    approved: bool | None = None


class MechanismGraphUpdate(BaseModel):
    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]


class KinematicModelUpdate(BaseModel):
    joints: list[dict[str, Any]]
    constraints: list[dict[str, Any]] = Field(default_factory=list)


class DecisionRequest(BaseModel):
    actor: str = Field(min_length=1, max_length=200)
    role: ReviewerRole
    action: str = Field(pattern="^(approve|approve_with_changes|reject)$")
    comment: str = Field(min_length=1, max_length=5000)


class SignatureRequest(BaseModel):
    reviewer: str = Field(min_length=1, max_length=200)
    role: ReviewerRole
    comment: str = Field(min_length=1, max_length=5000)


class ReleaseRequest(BaseModel):
    actor: str = Field(min_length=1, max_length=200)
    role: ReviewerRole
    comment: str = Field(min_length=1, max_length=5000)


class JobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    status: JobStatus
    stage: str
    error: str | None
    created_at: datetime
    completed_at: datetime | None


class ComponentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    component_type: str
    confidence: float
    description: str | None
    bounding_box: dict[str, float] | None
    approved: bool
    relationships: list[str]


class AssetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    title: str
    source_url: str | None
    source_type: str
    thumbnail_url: str | None
    status: ReviewStatus
    confidence: float | None
    discipline: str
    high_risk: bool
    description: str | None
    mechanism_graph: dict[str, Any] | None
    kinematic_model: dict[str, Any] | None
    extracted_metadata: dict[str, Any]
    revision: int
    created_at: datetime
    components: list[ComponentRead] = Field(default_factory=list)
    jobs: list[JobRead] = Field(default_factory=list)


class AuditRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    actor: str
    role: str
    action: str
    comment: str | None
    revision: int
    snapshot: dict[str, Any]
    created_at: datetime
