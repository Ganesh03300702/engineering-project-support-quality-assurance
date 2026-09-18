"""
Unit tests for data validation functions.
"""

from utils.validators import (
    validate_required_string,
    validate_code,
    validate_date_order,
    validate_progress,
    validate_project_data,
    validate_requirement_data,
    validate_task_data,
    validate_deliverable_data,
    validate_issue_data,
)


def test_validate_required_string():
    ok, _ = validate_required_string("Valid String", "Field")
    assert ok is True

    ok, msg = validate_required_string("   ", "Field")
    assert ok is False
    assert "cannot be empty" in msg

    ok, msg = validate_required_string(None, "Field")
    assert ok is False


def test_validate_code():
    assert validate_code("PRJ-001")[0] is True
    assert validate_code("REQ_102")[0] is True
    assert validate_code("TSK-ALPHA-9")[0] is True

    # Disallowed special characters
    assert validate_code("PRJ#001")[0] is False
    assert validate_code("PRJ 001")[0] is False
    assert validate_code("")[0] is False


def test_validate_date_order():
    ok, _ = validate_date_order("2026-01-01", "2026-01-10")
    assert ok is True

    ok, _ = validate_date_order("2026-01-01", "2026-01-01")
    assert ok is True

    ok, msg = validate_date_order("2026-02-01", "2026-01-01")
    assert ok is False
    assert "cannot be before" in msg

    ok, msg = validate_date_order("not-a-date", "2026-01-01")
    assert ok is False


def test_validate_progress():
    assert validate_progress(0)[0] is True
    assert validate_progress(50)[0] is True
    assert validate_progress(100)[0] is True

    assert validate_progress(-5)[0] is False
    assert validate_progress(105)[0] is False
    assert validate_progress("abc")[0] is False


def test_validate_project_data():
    valid = {
        "project_code": "PRJ-999",
        "project_name": "Turbine Blade Fatigue Testing",
        "project_type": "Equipment Inspection",
        "start_date": "2026-01-01",
        "deadline": "2026-06-01",
        "status": "Active",
        "priority": "High",
    }
    assert validate_project_data(valid)[0] is True

    # Bad deadline before start date
    invalid = valid.copy()
    invalid["deadline"] = "2025-12-31"
    assert validate_project_data(invalid)[0] is False

    # Missing project name
    invalid2 = valid.copy()
    invalid2["project_name"] = "  "
    assert validate_project_data(invalid2)[0] is False


def test_validate_task_data():
    valid = {
        "project_id": 1,
        "task_code": "TSK-001",
        "task_description": "Run finite element simulation",
        "status": "In Progress",
        "priority": "Medium",
        "progress_percentage": 50,
    }
    assert validate_task_data(valid)[0] is True

    # Invalid progress
    invalid = valid.copy()
    invalid["progress_percentage"] = 150
    assert validate_task_data(invalid)[0] is False


def test_validate_deliverable_data():
    valid = {
        "project_id": 1,
        "deliverable_code": "DEL-001",
        "deliverable_name": "Fatigue Analysis Report",
        "version": "v1.0",
        "review_status": "Draft",
    }
    assert validate_deliverable_data(valid)[0] is True

    # Invalid review status
    invalid = valid.copy()
    invalid["review_status"] = "UnknownStatus"
    assert validate_deliverable_data(invalid)[0] is False


def test_validate_issue_data():
    valid = {
        "project_id": 1,
        "issue_code": "ISS-001",
        "description": "Sensor drift in chamber B",
        "severity": "High",
        "status": "Open",
    }
    assert validate_issue_data(valid)[0] is True

    invalid = valid.copy()
    invalid["severity"] = "UltraExtreme"
    assert validate_issue_data(invalid)[0] is False
