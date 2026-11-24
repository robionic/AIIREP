import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ReviewStatus(str, enum.Enum):
    DRAFT = "Draft"
    PENDING_REVIEW = "Pending Review"
    APPROVED_WITH_CHANGES = "Approved With Changes"
    APPROVED = "Approved"
    REJECTED = "Rejected"
    RELEASED = "Released"


class JobStatus(str, enum.Enum):
    QUEUED = "Queued"
    PROCESSING = "Processing"
    COMPLETED = "Completed"
    FAILED = "Failed"


class ReviewerRole(str, enum.Enum):
    MECHANICAL = "Mechanical Engineer"
    CONTROLS = "Controls Engineer"
    ELECTRICAL = "Electrical Engineer"
    AUTOMATION = "Automation Engineer"
    ROBOTICS = "Robotics Engineer"
    SENIOR = "Senior Reviewer"
    ADMIN = "Administrator"


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(2048))
    source_type: Mapped[str] = mapped_column(String(30), default="url", nullable=False)
    media_path: Mapped[str | None] = mapped_column(String(1024))
    thumbnail_url: Mapped[str | None] = mapped_column(String(2048))
    status: Mapped[ReviewStatus] = mapped_column(Enum(ReviewStatus), default=ReviewStatus.DRAFT, index=True)
    confidence: Mapped[float | None] = mapped_column(Float)
    discipline: Mapped[str] = mapped_column(String(40), default="Mechanical", index=True)
    high_risk: Mapped[bool] = mapped_column(Boolean, default=False)
    description: Mapped[str | None] = mapped_column(Text)
    mechanism_graph: Mapped[dict | None] = mapped_column(JSON)
    kinematic_model: Mapped[dict | None] = mapped_column(JSON)
    extracted_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    revision: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    components: Mapped[list["Component"]] = relationship(back_populates="asset", cascade="all, delete-orphan")
    jobs: Mapped[list["AnalysisJob"]] = relationship(back_populates="asset", cascade="all, delete-orphan")
    signatures: Mapped[list["ReviewSignature"]] = relationship(back_populates="asset", cascade="all, delete-orphan")


class Component(Base):
    __tablename__ = "components"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    asset_id: Mapped[str] = mapped_column(ForeignKey("assets.id"), index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    component_type: Mapped[str] = mapped_column(String(80), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    bounding_box: Mapped[dict | None] = mapped_column(JSON)
    description: Mapped[str | None] = mapped_column(Text)
    approved: Mapped[bool] = mapped_column(Boolean, default=False)
    relationships: Mapped[list] = mapped_column(JSON, default=list)
    asset: Mapped[Asset] = relationship(back_populates="components")


class AnalysisJob(Base):
    __tablename__ = "analysis_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    asset_id: Mapped[str] = mapped_column(ForeignKey("assets.id"), index=True)
    status: Mapped[JobStatus] = mapped_column(Enum(JobStatus), default=JobStatus.QUEUED, index=True)
    stage: Mapped[str] = mapped_column(String(80), default="queued")
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    asset: Mapped[Asset] = relationship(back_populates="jobs")


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    asset_id: Mapped[str] = mapped_column(ForeignKey("assets.id"), index=True)
    actor: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[str] = mapped_column(String(80), nullable=False)
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)


class ReviewSignature(Base):
    __tablename__ = "review_signatures"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    asset_id: Mapped[str] = mapped_column(ForeignKey("assets.id"), index=True)
    reviewer: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[ReviewerRole] = mapped_column(Enum(ReviewerRole), nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[str] = mapped_column(Text, nullable=False)
    approved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    asset: Mapped[Asset] = relationship(back_populates="signatures")
