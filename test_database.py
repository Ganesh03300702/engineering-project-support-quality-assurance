"""
Unit tests for database helper and schema management.
"""

import sqlite3
import pytest
from database import get_connection, db_transaction, execute_query, fetch_all, fetch_one, init_db, log_activity, reset_db


@pytest.fixture
def test_db(tmp_path):
    """Creates a clean temporary database for testing."""
    db_file = tmp_path / "test_app.db"
    init_db(db_file)
    return db_file


def test_init_db_creates_all_tables(test_db):
    """Verifies that all 7 required tables exist in the initialized database."""
    conn = get_connection(test_db)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row["name"] for row in cursor.fetchall()}
    conn.close()

    expected_tables = {
        "projects",
        "requirements",
        "tasks",
        "deliverables",
        "quality_checks",
        "issues",
        "activity_log",
    }
    assert expected_tables.issubset(tables)


def test_foreign_keys_enforced(test_db):
    """Verifies foreign key constraints prevent inserting orphans."""
    conn = get_connection(test_db)
    fk_status = conn.execute("PRAGMA foreign_keys;").fetchone()[0]
    conn.close()
    assert fk_status == 1

    # Attempt inserting a requirement referencing non-existent project_id 9999
    with pytest.raises(sqlite3.IntegrityError):
        execute_query(
            "INSERT INTO requirements (project_id, requirement_code, description) VALUES (?, ?, ?)",
            (9999, "REQ-ORPHAN", "Orphan Requirement"),
            db_path=test_db,
        )


def test_transaction_rollback_on_error(test_db):
    """Verifies rollback leaves database unchanged when an exception occurs inside transaction."""
    with pytest.raises(RuntimeError):
        with db_transaction(test_db) as conn:
            execute_query(
                "INSERT INTO projects (project_code, project_name, project_type, start_date, deadline) VALUES (?, ?, ?, ?, ?)",
                ("PRJ-FAIL", "Failing Project", "Type A", "2026-01-01", "2026-02-01"),
                conn=conn,
            )
            raise RuntimeError("Forced simulation error")

    row = fetch_one("SELECT * FROM projects WHERE project_code = ?", ("PRJ-FAIL",), db_path=test_db)
    assert row is None


def test_log_activity_records_entry(test_db):
    """Verifies that log_activity records audit trails."""
    log_activity("CREATE", "PROJECT", 101, "Test project created", db_path=test_db)
    rows = fetch_all("SELECT * FROM activity_log WHERE entity_id = ?", (101,), db_path=test_db)
    assert len(rows) == 1
    assert rows[0]["action_type"] == "CREATE"
    assert rows[0]["entity_type"] == "PROJECT"
    assert "Test project created" in rows[0]["description"]


def test_reset_db_clears_records(test_db):
    """Verifies that reset_db empties data and reapplies schema."""
    execute_query(
        "INSERT INTO projects (project_code, project_name, project_type, start_date, deadline) VALUES (?, ?, ?, ?, ?)",
        ("PRJ-TEMP", "Temp Project", "Type B", "2026-01-01", "2026-02-01"),
        db_path=test_db,
    )
    assert fetch_one("SELECT * FROM projects WHERE project_code = ?", ("PRJ-TEMP",), db_path=test_db) is not None

    reset_db(test_db)
    assert fetch_one("SELECT * FROM projects WHERE project_code = ?", ("PRJ-TEMP",), db_path=test_db) is None
    # Verify tables still exist
    projects = fetch_all("SELECT * FROM projects", db_path=test_db)
    assert len(projects) == 0
