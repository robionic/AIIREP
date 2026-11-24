from app.models import Asset, ReviewerRole
from app.workflow import required_approval_roles


def test_confidence_escalation_requires_mechanical_and_controls_below_80_percent():
    asset = Asset(confidence=0.79, high_risk=False)
    assert required_approval_roles(asset) == {ReviewerRole.MECHANICAL, ReviewerRole.CONTROLS}


def test_confidence_escalation_requires_mechanical_from_80_through_95_percent():
    for confidence in (0.8, 0.95):
        asset = Asset(confidence=confidence, high_risk=False)
        assert required_approval_roles(asset) == {ReviewerRole.MECHANICAL}


def test_confidence_above_95_percent_allows_single_qualified_reviewer():
    asset = Asset(confidence=0.951, high_risk=False)
    assert required_approval_roles(asset) == set()


def test_high_risk_asset_requires_four_eye_approval_at_any_confidence():
    asset = Asset(confidence=0.99, high_risk=True)
    assert required_approval_roles(asset) == {ReviewerRole.MECHANICAL, ReviewerRole.CONTROLS}
