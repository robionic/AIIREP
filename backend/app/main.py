import mimetypes
from pathlib import Path
from urllib.parse import urlparse
import uuid

from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.config import settings
from app.database import Base, engine, get_db
from app.models import (
    AnalysisJob,
    Asset,
    AuditEvent,
    Component,
    JobStatus,
    ReviewSignature,
    ReviewStatus,
    ReviewerRole,
)
from app.schemas import (
    AssetCreate,
    AssetRead,
    AuditRead,
    ComponentCreate,
    ComponentRead,
    ComponentUpdate,
    DecisionRequest,
    KinematicModelUpdate,
    MechanismGraphUpdate,
    ReleaseRequest,
    SignatureRequest,
)
from app.workflow import (
    append_audit,
    approvals_satisfied,
    component_snapshot,
    ensure_asset,
    ensure_editable,
    required_approval_roles,
    revise_asset,
    signatures_for_revision,
    validate_reviewer,
)

Base.metadata.create_all(bind=engine)
app = FastAPI(title=settings.app_name, version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIRECTORY = Path(settings.storage_path).resolve()
UPLOAD_DIRECTORY.mkdir(parents=True, exist_ok=True)


def asset_query():
    return select(Asset).options(selectinload(Asset.components), selectinload(Asset.jobs))


def require_supported_url(source_url: str) -> None:
    parsed = urlparse(source_url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        raise HTTPException(status_code=422, detail="Only public HTTP(S) video URLs are supported.")
    host = parsed.hostname.lower()
    supported = (
        host == "youtube.com"
        or host.endswith(".youtube.com")
        or host == "youtu.be"
        or host == "vimeo.com"
        or host.endswith(".vimeo.com")
        or parsed.path.lower().endswith((".mp4", ".mov", ".webm"))
    )
    if not supported:
        raise HTTPException(status_code=422, detail="Use a YouTube, Vimeo, or direct video URL.")


def create_asset_job(db: Session, asset: Asset) -> AnalysisJob:
    job = AnalysisJob(asset_id=asset.id)
    db.add(job)
    append_audit(
        db,
        asset,
        actor="system",
        role="System",
        action="asset_created",
        comment="Analysis job created. No AI output is approved automatically.",
        snapshot={"source_type": asset.source_type},
    )
    db.commit()
    db.refresh(asset)
    return job


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/api/assets", response_model=AssetRead, status_code=201)
def create_asset(payload: AssetCreate, db: Session = Depends(get_db)):
    source_url = str(payload.source_url)
    require_supported_url(source_url)
    asset = Asset(
        title=payload.title.strip(),
        source_url=source_url,
        source_type="url",
        discipline=payload.discipline,
        high_risk=payload.high_risk,
    )
    db.add(asset)
    db.flush()
    create_asset_job(db, asset)
    return db.scalar(asset_query().where(Asset.id == asset.id))


@app.post("/api/assets/upload", response_model=AssetRead, status_code=201)
async def upload_asset(
    file: UploadFile = File(...),
    discipline: str = Query(default="Mechanical", max_length=40),
    high_risk: bool = False,
    db: Session = Depends(get_db),
):
    extension = Path(file.filename or "").suffix.lower()
    if extension not in {".mp4", ".mov", ".webm", ".m4v"}:
        raise HTTPException(status_code=415, detail="Upload an MP4, MOV, WEBM, or M4V video.")
    asset_id = str(uuid.uuid4())
    target = UPLOAD_DIRECTORY / f"{asset_id}{extension}"
    size = 0
    try:
        with target.open("wb") as output:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > settings.max_upload_bytes:
                    raise HTTPException(status_code=413, detail="Video exceeds the configured upload limit.")
                output.write(chunk)
    except Exception:
        target.unlink(missing_ok=True)
        raise
    finally:
        await file.close()

    asset = Asset(
        id=asset_id,
        title=Path(file.filename or "Uploaded video").stem[:240],
        source_type="upload",
        media_path=str(target),
        discipline=discipline,
        high_risk=high_risk,
    )
    db.add(asset)
    db.flush()
    create_asset_job(db, asset)
    return db.scalar(asset_query().where(Asset.id == asset.id))


@app.get("/api/assets", response_model=list[AssetRead])
def list_assets(
    status: ReviewStatus | None = None,
    discipline: str | None = None,
    db: Session = Depends(get_db),
):
    query = asset_query().order_by(Asset.created_at.desc())
    if status:
        query = query.where(Asset.status == status)
    if discipline:
        query = query.where(Asset.discipline == discipline)
    return list(db.scalars(query))


@app.get("/api/library", response_model=list[AssetRead])
def released_library(db: Session = Depends(get_db)):
    return list(
        db.scalars(
            asset_query()
            .where(Asset.status == ReviewStatus.RELEASED)
            .order_by(Asset.updated_at.desc())
        )
    )


@app.get("/api/assets/{asset_id}", response_model=AssetRead)
def get_asset(asset_id: str, db: Session = Depends(get_db)):
    asset = db.scalar(asset_query().where(Asset.id == asset_id))
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found.")
    return asset


@app.get("/api/assets/{asset_id}/media")
def get_uploaded_media(asset_id: str, db: Session = Depends(get_db)):
    asset = ensure_asset(db, asset_id)
    if not asset.media_path:
        raise HTTPException(status_code=404, detail="This asset does not have an uploaded media file.")
    media_path = Path(asset.media_path).resolve()
    if not media_path.is_relative_to(UPLOAD_DIRECTORY) or not media_path.is_file():
        raise HTTPException(status_code=404, detail="Uploaded media is unavailable.")
    return FileResponse(
        media_path,
        media_type=mimetypes.guess_type(media_path.name)[0] or "application/octet-stream",
        filename=media_path.name,
        content_disposition_type="inline",
    )


@app.post("/api/assets/{asset_id}/submit", response_model=AssetRead)
def submit_for_review(asset_id: str, db: Session = Depends(get_db)):
    asset = ensure_asset(db, asset_id)
    ensure_editable(asset)
    if asset.status not in {ReviewStatus.DRAFT, ReviewStatus.REJECTED}:
        raise HTTPException(status_code=409, detail="Only draft or rejected assets can be resubmitted.")
    if asset.status == ReviewStatus.REJECTED:
        asset.revision += 1
    asset.status = ReviewStatus.PENDING_REVIEW
    append_audit(db, asset, "submitter", "System", "submitted_for_review", None)
    db.commit()
    return db.scalar(asset_query().where(Asset.id == asset_id))


@app.post("/api/assets/{asset_id}/components", response_model=ComponentRead, status_code=201)
def add_component(
    asset_id: str,
    payload: ComponentCreate,
    actor: str = Query(default="Engineering reviewer", min_length=1, max_length=200),
    role: ReviewerRole = Query(default=ReviewerRole.MECHANICAL),
    db: Session = Depends(get_db),
):
    asset = ensure_asset(db, asset_id)
    ensure_editable(asset)
    component = Component(asset_id=asset.id, **payload.model_dump())
    db.add(component)
    revise_asset(asset)
    append_audit(db, asset, actor, role.value, "component_added", "Added component.", payload.model_dump())
    db.commit()
    db.refresh(component)
    return component


@app.patch("/api/assets/{asset_id}/components/{component_id}", response_model=ComponentRead)
def update_component(
    asset_id: str,
    component_id: str,
    payload: ComponentUpdate,
    actor: str = Query(default="Engineering reviewer", min_length=1, max_length=200),
    role: ReviewerRole = Query(default=ReviewerRole.MECHANICAL),
    db: Session = Depends(get_db),
):
    asset = ensure_asset(db, asset_id)
    ensure_editable(asset)
    component = db.get(Component, component_id)
    if component is None or component.asset_id != asset.id:
        raise HTTPException(status_code=404, detail="Component not found.")
    before = component_snapshot(component)
    changes = payload.model_dump(exclude_unset=True)
    for key, value in changes.items():
        setattr(component, key, value)
    revise_asset(asset)
    append_audit(db, asset, actor, role.value, "component_corrected", None, {"before": before, "after": changes})
    db.commit()
    db.refresh(component)
    return component


@app.delete("/api/assets/{asset_id}/components/{component_id}", status_code=204)
def delete_component(
    asset_id: str,
    component_id: str,
    actor: str = Query(default="Engineering reviewer", min_length=1, max_length=200),
    role: ReviewerRole = Query(default=ReviewerRole.MECHANICAL),
    db: Session = Depends(get_db),
):
    asset = ensure_asset(db, asset_id)
    ensure_editable(asset)
    component = db.get(Component, component_id)
    if component is None or component.asset_id != asset.id:
        raise HTTPException(status_code=404, detail="Component not found.")
    snapshot = component_snapshot(component)
    db.delete(component)
    revise_asset(asset)
    append_audit(db, asset, actor, role.value, "component_deleted", None, snapshot)
    db.commit()


@app.put("/api/assets/{asset_id}/mechanism", response_model=AssetRead)
def update_mechanism(
    asset_id: str,
    payload: MechanismGraphUpdate,
    actor: str = Query(min_length=1, max_length=200),
    db: Session = Depends(get_db),
):
    asset = ensure_asset(db, asset_id)
    ensure_editable(asset)
    node_ids = [str(node.get("id", "")) for node in payload.nodes]
    if not all(node_ids) or len(node_ids) != len(set(node_ids)):
        raise HTTPException(status_code=422, detail="Mechanism nodes must have unique, non-empty IDs.")
    if any(edge.get("source") not in node_ids or edge.get("target") not in node_ids for edge in payload.edges):
        raise HTTPException(status_code=422, detail="Every mechanism connection must reference an existing node.")
    before = asset.mechanism_graph
    asset.mechanism_graph = payload.model_dump()
    revise_asset(asset)
    append_audit(
        db,
        asset,
        actor,
        "Mechanical Engineer",
        "mechanism_graph_corrected",
        None,
        {"before": before, "after": payload.model_dump()},
    )
    db.commit()
    return db.scalar(asset_query().where(Asset.id == asset_id))


@app.put("/api/assets/{asset_id}/kinematics", response_model=AssetRead)
def update_kinematics(
    asset_id: str,
    payload: KinematicModelUpdate,
    actor: str = Query(min_length=1, max_length=200),
    db: Session = Depends(get_db),
):
    asset = ensure_asset(db, asset_id)
    ensure_editable(asset)
    allowed_joints = {"fixed", "revolute", "prismatic", "cylindrical", "spherical", "planar", "helical"}
    for joint in payload.joints:
        if str(joint.get("type", "")).lower() not in allowed_joints:
            raise HTTPException(status_code=422, detail=f"Joint type must be one of: {', '.join(sorted(allowed_joints))}.")
    before = asset.kinematic_model
    asset.kinematic_model = payload.model_dump()
    revise_asset(asset)
    append_audit(
        db,
        asset,
        actor,
        "Mechanical Engineer",
        "kinematic_model_corrected",
        None,
        {"before": before, "after": payload.model_dump()},
    )
    db.commit()
    return db.scalar(asset_query().where(Asset.id == asset_id))


@app.post("/api/assets/{asset_id}/decision", response_model=AssetRead)
def review_decision(asset_id: str, payload: DecisionRequest, db: Session = Depends(get_db)):
    asset = ensure_asset(db, asset_id)
    ensure_editable(asset)
    if asset.status != ReviewStatus.PENDING_REVIEW:
        raise HTTPException(status_code=409, detail="Asset must be pending review before a decision.")

    if payload.action == "reject":
        asset.status = ReviewStatus.REJECTED
    else:
        validate_reviewer(asset, payload.role)
        signatures = signatures_for_revision(db, asset)
        if any(signature.reviewer.casefold() == payload.actor.casefold() for signature in signatures):
            raise HTTPException(status_code=409, detail="Each approval must be from an independent reviewer.")
        db.add(
            ReviewSignature(
                asset_id=asset.id,
                reviewer=payload.actor,
                role=payload.role,
                revision=asset.revision,
                comment=payload.comment,
            )
        )
        db.flush()
        if payload.action == "approve_with_changes":
            asset.status = ReviewStatus.APPROVED_WITH_CHANGES
        elif approvals_satisfied(db, asset):
            asset.status = ReviewStatus.APPROVED
        else:
            asset.status = ReviewStatus.PENDING_REVIEW

    append_audit(
        db,
        asset,
        payload.actor,
        payload.role.value,
        payload.action,
        payload.comment,
        {"required_roles": [role.value for role in sorted(required_approval_roles(asset), key=lambda role: role.value)]},
    )
    db.commit()
    return db.scalar(asset_query().where(Asset.id == asset_id))


@app.post("/api/assets/{asset_id}/signatures", response_model=AssetRead)
def add_signature(asset_id: str, payload: SignatureRequest, db: Session = Depends(get_db)):
    asset = ensure_asset(db, asset_id)
    ensure_editable(asset)
    if asset.status not in {ReviewStatus.PENDING_REVIEW, ReviewStatus.APPROVED_WITH_CHANGES}:
        raise HTTPException(status_code=409, detail="Asset is not accepting validation signatures.")
    validate_reviewer(asset, payload.role)
    signatures = signatures_for_revision(db, asset)
    if any(signature.reviewer.casefold() == payload.reviewer.casefold() for signature in signatures):
        raise HTTPException(status_code=409, detail="Each approval must be from an independent reviewer.")
    db.add(
        ReviewSignature(
            asset_id=asset.id,
            reviewer=payload.reviewer,
            role=payload.role,
            revision=asset.revision,
            comment=payload.comment,
        )
    )
    db.flush()
    append_audit(db, asset, payload.reviewer, payload.role.value, "signed_validation", payload.comment)
    if approvals_satisfied(db, asset):
        asset.status = ReviewStatus.APPROVED
    db.commit()
    return db.scalar(asset_query().where(Asset.id == asset_id))


@app.post("/api/assets/{asset_id}/release", response_model=AssetRead)
def release_asset(asset_id: str, payload: ReleaseRequest, db: Session = Depends(get_db)):
    asset = ensure_asset(db, asset_id)
    if payload.role not in {ReviewerRole.SENIOR, ReviewerRole.ADMIN}:
        raise HTTPException(status_code=403, detail="Only a Senior Reviewer or Administrator may release an asset.")
    if asset.status != ReviewStatus.APPROVED:
        raise HTTPException(status_code=409, detail="Only approved assets may be released.")
    if not approvals_satisfied(db, asset):
        raise HTTPException(status_code=409, detail="Required independent engineering signatures are missing.")
    unapproved = list(db.scalars(select(Component).where(Component.asset_id == asset.id, Component.approved.is_(False))))
    if unapproved:
        raise HTTPException(status_code=409, detail="All detected components must be explicitly approved before release.")
    asset.status = ReviewStatus.RELEASED
    append_audit(db, asset, payload.actor, payload.role.value, "released", payload.comment)
    db.commit()
    return db.scalar(asset_query().where(Asset.id == asset_id))


@app.get("/api/assets/{asset_id}/audit", response_model=list[AuditRead])
def audit_history(asset_id: str, db: Session = Depends(get_db)):
    ensure_asset(db, asset_id)
    return list(
        db.scalars(
            select(AuditEvent)
            .where(AuditEvent.asset_id == asset_id)
            .order_by(AuditEvent.created_at.asc(), AuditEvent.id.asc())
        )
    )


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str, db: Session = Depends(get_db)):
    job = db.get(AnalysisJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Analysis job not found.")
    return {
        "id": job.id,
        "asset_id": job.asset_id,
        "status": job.status,
        "stage": job.stage,
        "error": job.error,
        "created_at": job.created_at,
        "completed_at": job.completed_at,
        "message": "Configure a vision inference provider and worker to execute analysis.",
    }


@app.get("/api/review/queue", response_model=list[AssetRead])
def review_queue(
    discipline: str | None = None,
    db: Session = Depends(get_db),
):
    query = asset_query().where(Asset.status == ReviewStatus.PENDING_REVIEW).order_by(Asset.created_at.asc())
    if discipline:
        query = query.where(Asset.discipline == discipline)
    return list(db.scalars(query))
