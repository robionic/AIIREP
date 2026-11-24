from sqlalchemy import select

from app.database import Base, SessionLocal, engine
from app.models import AnalysisJob, Asset, Component, JobStatus, ReviewStatus

Base.metadata.create_all(bind=engine)

with SessionLocal() as db:
    existing = db.scalar(select(Asset).where(Asset.title == "Illustrative conveyor transfer demo"))
    if existing is None:
        asset = Asset(
            title="Illustrative conveyor transfer demo",
            source_url="https://example.com/conveyor-demo.mp4",
            source_type="url",
            status=ReviewStatus.PENDING_REVIEW,
            confidence=0.87,
            discipline="Mechanical",
            description="Seed record for demonstrating engineering review. Findings are illustrative and are not AI detections.",
            mechanism_graph={
                "nodes": [{"id": "motor", "label": "Motor"}, {"id": "belt", "label": "Conveyor belt"}],
                "edges": [{"source": "motor", "target": "belt", "label": "power transmission"}],
            },
            kinematic_model={"joints": [{"type": "revolute", "axis": [0, 0, 1], "source": "illustrative"}]},
            extracted_metadata={"source": "seed", "illustrative": True},
        )
        db.add(asset)
        db.flush()
        db.add(
            Component(
                asset_id=asset.id,
                name="Drive motor (illustrative)",
                component_type="Motor",
                confidence=0.87,
                description="Seed demonstration item; verify against actual video before approval.",
                approved=False,
                relationships=["Conveyor belt"],
            )
        )
        db.add(AnalysisJob(asset_id=asset.id, status=JobStatus.QUEUED, stage="demo_seed"))
        db.commit()
        print(f"Seeded illustrative asset: {asset.id}")
    else:
        print(f"Seed asset already exists: {existing.id}")
