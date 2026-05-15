# tests/test_database.py
import pytest
import sqlite3
from app.db.database import init_db, save_run, list_runs, get_run, delete_run
from app.models.session import ProFormaSession


@pytest.fixture
def db():
    conn = init_db(":memory:")
    yield conn
    conn.close()


def test_save_and_list(db, basic_session):
    save_run(basic_session, "/tmp/test.xlsx", 150000.0, 2300000.0, conn=db)
    runs = list_runs(conn=db)
    assert len(runs) == 1
    assert runs[0]["building_name"] == "Test Tower"
    assert runs[0]["noi_y1"] == pytest.approx(150000.0)


def test_get_run_restores_session(db, basic_session):
    run_id = save_run(basic_session, "/tmp/test.xlsx", 150000.0, 2300000.0, conn=db)
    row = get_run(run_id, conn=db)
    restored = ProFormaSession.from_json(row["inputs_json"])
    assert restored.building_name == "Test Tower"
    assert len(restored.tenants) == 1


def test_delete_run(db, basic_session):
    run_id = save_run(basic_session, "/tmp/test.xlsx", 0, 0, conn=db)
    delete_run(run_id, conn=db)
    assert list_runs(conn=db) == []


def test_list_runs_ordered_newest_first(db, basic_session):
    save_run(basic_session, "/a.xlsx", 1.0, 1.0, conn=db)
    save_run(basic_session, "/b.xlsx", 2.0, 2.0, conn=db)
    runs = list_runs(conn=db)
    assert runs[0]["noi_y1"] == pytest.approx(2.0)
