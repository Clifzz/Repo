# tests/test_session.py
from app.models.session import ProFormaSession
from app.models.tenant import TenantModel


def test_json_round_trip(basic_session):
    restored = ProFormaSession.from_json(basic_session.to_json())
    assert restored.building_name == basic_session.building_name
    assert restored.cap_rate == basic_session.cap_rate
    assert len(restored.tenants) == 1
    assert restored.tenants[0].name == "Acme Corp"


def test_empty_tenants():
    s = ProFormaSession()
    restored = ProFormaSession.from_json(s.to_json())
    assert restored.tenants == []
