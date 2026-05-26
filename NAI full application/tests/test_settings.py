import pytest
from app.db.database import init_db
from app.db.settings import get_setting, set_setting


@pytest.fixture
def db(tmp_path):
    return init_db(str(tmp_path / "test.db"))


def test_get_missing_key_returns_none(db):
    assert get_setting("missing", conn=db) is None


def test_get_missing_key_returns_provided_default(db):
    assert get_setting("missing", default="fallback", conn=db) == "fallback"


def test_set_and_get_roundtrip(db):
    set_setting("foo", "bar", conn=db)
    assert get_setting("foo", conn=db) == "bar"


def test_set_overwrites_existing(db):
    set_setting("key", "v1", conn=db)
    set_setting("key", "v2", conn=db)
    assert get_setting("key", conn=db) == "v2"


def test_multiple_keys_are_independent(db):
    set_setting("a", "1", conn=db)
    set_setting("b", "2", conn=db)
    assert get_setting("a", conn=db) == "1"
    assert get_setting("b", conn=db) == "2"
