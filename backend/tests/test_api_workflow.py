import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app


@pytest.fixture
def client():
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session = sessionmaker(bind=test_engine, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(bind=test_engine)

    def override_get_db():
        with testing_session() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()


def test_low_confidence_asset_requires_two_independent_reviews_and_component_validation(client):
    created = client.post(
        "/api/assets",
        json={
            "title": "Transfer line",
            "source_url": "https://media.example.org/line.mp4",
            "discipline": "Mechanical",
        },
    )
    assert created.status_code == 201
    asset = created.json()
    asset_id = asset["id"]
    assert asset["status"] == "Draft"
    assert len(asset["jobs"]) == 1

    response = client.post(f"/api/assets/{asset_id}/components", json={
        "name": "Drive motor",
        "component_type": "Motor",
        "confidence": 0.72,
    })
    assert response.status_code == 201
    component_id = response.json()["id"]
    client.patch(f"/api/assets/{asset_id}/components/{component_id}", json={"approved": True})
    client.post(f"/api/assets/{asset_id}/submit")

    mechanical = client.post(f"/api/assets/{asset_id}/decision", json={
        "actor": "Morgan",
        "role": "Mechanical Engineer",
        "action": "approve",
        "comment": "Mechanical review complete.",
    })
    assert mechanical.status_code == 200
    assert mechanical.json()["status"] == "Pending Review"

    duplicate_reviewer = client.post(f"/api/assets/{asset_id}/decision", json={
        "actor": "Morgan",
        "role": "Controls Engineer",
        "action": "approve",
        "comment": "Second role by the same person.",
    })
    assert duplicate_reviewer.status_code == 409

    controls = client.post(f"/api/assets/{asset_id}/decision", json={
        "actor": "Casey",
        "role": "Controls Engineer",
        "action": "approve",
        "comment": "Controls review complete.",
    })
    assert controls.status_code == 200
    assert controls.json()["status"] == "Approved"

    released = client.post(f"/api/assets/{asset_id}/release", json={
        "actor": "Sam",
        "role": "Senior Reviewer",
        "comment": "Release authorized.",
    })
    assert released.status_code == 200
    assert released.json()["status"] == "Released"
    assert len(client.get("/api/library").json()) == 1

    audit = client.get(f"/api/assets/{asset_id}/audit")
    assert audit.status_code == 200
    actions = [event["action"] for event in audit.json()]
    assert "component_corrected" in actions
    assert actions.count("approve") == 2
    assert "released" in actions
