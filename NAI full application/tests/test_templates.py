import pytest
from app.db.database import (
    init_db, save_template, list_templates, get_template, delete_template,
    save_run, delete_run,
)
from app.models.session import ProFormaSession


@pytest.fixture
def db():
    conn = init_db(":memory:")
    yield conn
    conn.close()


def test_save_and_list_template(db, basic_session):
    tid = save_template("Office Standard", basic_session, conn=db)
    rows = list_templates(conn=db)
    assert len(rows) == 1
    assert rows[0]["template_name"] == "Office Standard"
    assert rows[0]["building_name"] == "Test Tower"
    assert rows[0]["id"] == tid


def test_get_template_restores_session(db, basic_session):
    tid = save_template("Test Tmpl", basic_session, conn=db)
    row = get_template(tid, conn=db)
    restored = ProFormaSession.from_json(row["inputs_json"])
    assert restored.building_name == "Test Tower"
    assert len(restored.tenants) == 1


def test_get_template_returns_none_for_missing(db):
    assert get_template(999, conn=db) is None


def test_delete_template(db, basic_session):
    tid = save_template("Temp", basic_session, conn=db)
    delete_template(tid, conn=db)
    assert list_templates(conn=db) == []


def test_duplicate_template_names_allowed(db, basic_session):
    save_template("Same", basic_session, conn=db)
    save_template("Same", basic_session, conn=db)
    assert len(list_templates(conn=db)) == 2


def test_deleting_run_does_not_affect_templates(db, basic_session):
    save_template("Keeper", basic_session, conn=db)
    run_id = save_run(basic_session, "/tmp/x.xlsx", 0.0, 0.0, conn=db)
    delete_run(run_id, conn=db)
    assert len(list_templates(conn=db)) == 1


def test_list_templates_ordered_newest_first(db, basic_session):
    id1 = save_template("First", basic_session, conn=db)
    id2 = save_template("Second", basic_session, conn=db)
    rows = list_templates(conn=db)
    assert rows[0]["id"] == id2
    assert rows[1]["id"] == id1
