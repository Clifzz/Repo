import pytest
from app.db.draft import save_draft, load_draft, clear_draft, _draft_path
from app.models.session import ProFormaSession


@pytest.fixture
def tmp_draft(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    yield


def test_round_trip(tmp_draft, basic_session):
    save_draft(basic_session)
    restored = load_draft()
    assert restored is not None
    assert restored.building_name == "Test Tower"
    assert len(restored.tenants) == 1
    assert restored.tenants[0].name == "Acme Corp"


def test_load_returns_none_when_missing(tmp_draft):
    assert load_draft() is None


def test_clear_removes_draft(tmp_draft, basic_session):
    save_draft(basic_session)
    clear_draft()
    assert load_draft() is None


def test_load_returns_none_on_corrupt_json(tmp_draft):
    p = _draft_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("not valid json", encoding="utf-8")
    assert load_draft() is None


def test_save_overwrites_previous(tmp_draft, basic_session):
    save_draft(basic_session)
    basic_session.building_name = "Updated Tower"
    save_draft(basic_session)
    restored = load_draft()
    assert restored.building_name == "Updated Tower"
