from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Asset, AuditEvent, Component, ReviewSignature, ReviewStatus, ReviewerRole


def required_approval_roles(asset: Asset) -> set[ReviewerRole]:
    confidence = asset.confidence or 0
    if asset.high_risk:
        return {ReviewerRole.MECHANICAL, ReviewerRole.CONTROLS}
    if confidence < 0.8:
        return {ReviewerRole.MECHANICAL, ReviewerRole.CONTROLS}
    if confidence <= 0.95:
        return {ReviewerRole.MECHANICAL}
    return set()


def signatures_for_revision(db: Session, asset: Asset) -> list[ReviewSignature]:
    return list(
        db.scalars(
            select(ReviewSignature).where(
                ReviewSignature.asset_id == asset.id,
                ReviewSignature.revision == asset.revision,
            )
        )
    )


def approvals_satisfied(db: Session, asset: Asset) -> bool:
    signatures = signatures_for_revision(db, asset)
    if len({signature.reviewer.casefold() for signature in signatures}) != len(signatures):
        return False
    roles = {signature.role for signature in signatures}
    return required_approval_roles(asset).issubset(roles) and bool(signatures)


def validate_reviewer(asset: Asset, role: ReviewerRole) -> None:
    required = required_approval_roles(asset)
    if not required:
        if role == ReviewerRole.ADMIN:
            raise HTTPException(status_code=403, detail="Administrator role cannot provide engineering validation.")
        return
    if role not in required:
        raise HTTPException(
            status_code=403,
            detail=f"This asset requires review by: {', '.join(sorted(item.value for item in required))}.",
        )


def append_audit(
    db: Session,
    asset: Asset,
    actor: str,
    role: str,
    action: str,
    comment: str | None,
    snapshot: dict | None = None,
) -> None:
    db.add(
        AuditEvent(
            asset_id=asset.id,
            actor=actor,
            role=role,
            action=action,
            comment=comment,
            revision=asset.revision,
            snapshot=snapshot or {},
        )
    )


def ensure_editable(asset: Asset) -> None:
    if asset.status == ReviewStatus.RELEASED:
        raise HTTPException(status_code=409, detail="Released assets are immutable; create a new revision.")


def revise_asset(asset: Asset) -> None:
    asset.revision += 1
    if asset.status != ReviewStatus.DRAFT:
        asset.status = ReviewStatus.PENDING_REVIEW


def ensure_asset(db: Session, asset_id: str) -> Asset:
    asset = db.get(Asset, asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found.")
    return asset


def component_snapshot(component: Component) -> dict:
    return {
        "id": component.id,
        "name": component.name,
        "component_type": component.component_type,
        "confidence": component.confidence,
        "description": component.description,
        "approved": component.approved,
    }
