"""
Unit tests for the 12-rule Quality Assurance Engine.
"""

from datetime import date, timedelta
import pytest
from database import init_db
from modules.projects import create_project
from modules.requirements import create_requirement
from modules.tasks import create_task
from modules.deliverables import create_deliverable
from modules.issues import create_issue
from modules.quality_checks import run_all_quality_checks, get_latest_quality_checks


@pytest.fixture
def test_db(tmp_path):
    db_file = tmp_path / "qa_test.db"
    init_db(db_file)
    return db_file


def test_qa_clean_empty_db_returns_pass(test_db):
    results = run_all_quality_checks(db_path=test_db)
    assert len(results) == 12
    # On an empty DB, all 12 system checks should report PASS
    for r in results:
        assert r["check_result"] == "PASS"


def test_qa_catches_invalid_dates(test_db):
    # Create project with deadline before start date directly
    from database import execute_query
    execute_query(
        """
        INSERT INTO projects (project_code, project_name, project_type, start_date, deadline, priority, status)
        VALUES ('PRJ-BAD-DATE', 'Bad Date Project', 'Equipment Inspection', '2026-06-01', '2026-01-01', 'Medium', 'Planned')
        """,
        db_path=test_db,
    )
    results = run_all_quality_checks(db_path=test_db)
    date_failures = [r for r in results if r["check_name"] == "Invalid Dates" and r["check_result"] == "FAIL"]
    assert len(date_failures) >= 1
    assert "deadline (2026-01-01) is before start date (2026-06-01)" in date_failures[0]["error_message"]


def test_qa_catches_missing_reviewer_for_submitted_deliverable(test_db):
    p_id = create_project({
        "project_code": "PRJ-QA1",
        "project_name": "QA Project 1",
        "project_type": "Equipment Inspection",
        "start_date": "2026-01-01",
        "deadline": "2026-06-01",
    }, db_path=test_db)

    create_deliverable({
        "project_id": p_id,
        "deliverable_code": "DEL-NOREV",
        "deliverable_name": "Submitted Without Reviewer",
        "deliverable_type": "Test Protocol",
        "version": "v1.0",
        "reviewer": "",  # Missing reviewer
        "review_status": "Submitted",
        "file_name": "doc.pdf",
    }, db_path=test_db)

    results = run_all_quality_checks(db_path=test_db)
    rev_failures = [r for r in results if r["check_name"] == "Missing Reviewer for Submitted Deliverables" and r["check_result"] == "FAIL"]
    assert len(rev_failures) == 1
    assert "DEL-NOREV" in rev_failures[0]["error_message"]


def test_qa_catches_overdue_tasks(test_db):
    p_id = create_project({
        "project_code": "PRJ-QA2",
        "project_name": "QA Project 2",
        "project_type": "Equipment Inspection",
        "start_date": "2026-01-01",
        "deadline": "2026-06-01",
    }, db_path=test_db)

    past_date = (date.today() - timedelta(days=7)).isoformat()
    create_task({
        "project_id": p_id,
        "task_code": "TSK-LATE",
        "task_description": "Overdue calibration task",
        "assigned_to": "Engineer Bob",
        "status": "In Progress",
        "due_date": past_date,
        "progress_percentage": 40,
    }, db_path=test_db)

    results = run_all_quality_checks(db_path=test_db)
    overdue_warns = [r for r in results if r["check_name"] == "Overdue Tasks" and r["check_result"] == "WARNING"]
    assert len(overdue_warns) == 1
    assert "TSK-LATE" in overdue_warns[0]["error_message"]


def test_qa_catches_clarification_needed_requirements(test_db):
    p_id = create_project({
        "project_code": "PRJ-QA3",
        "project_name": "QA Project 3",
        "project_type": "Documentation Standardization",
        "start_date": "2026-01-01",
        "deadline": "2026-06-01",
    }, db_path=test_db)

    create_requirement({
        "project_id": p_id,
        "requirement_code": "REQ-CLARIFY",
        "description": "Requirement awaiting client confirmation",
        "status": "Clarification Required",
        "clarification_question": "Need clarification on pressure sensor operating limits",
    }, db_path=test_db)

    results = run_all_quality_checks(db_path=test_db)
    clarify_warns = [r for r in results if r["check_name"] == "Open Requirements Requiring Clarification" and r["check_result"] == "WARNING"]
    assert len(clarify_warns) == 1
    assert "REQ-CLARIFY" in clarify_warns[0]["error_message"]


def test_qa_catches_missing_task_owners(test_db):
    p_id = create_project({
        "project_code": "PRJ-QA4",
        "project_name": "QA Project 4",
        "project_type": "Component Quality Review",
        "start_date": "2026-01-01",
        "deadline": "2026-06-01",
    }, db_path=test_db)

    create_task({
        "project_id": p_id,
        "task_code": "TSK-NO-OWNER",
        "task_description": "Active task with no assigned owner",
        "assigned_to": "",
        "status": "In Progress",
        "progress_percentage": 20,
    }, db_path=test_db)

    results = run_all_quality_checks(db_path=test_db)
    owner_warns = [r for r in results if r["check_name"] == "Missing Task Owners" and r["check_result"] == "WARNING"]
    assert len(owner_warns) == 1
    assert "TSK-NO-OWNER" in owner_warns[0]["error_message"]


def test_qa_catches_missing_acceptance_criteria(test_db):
    p_id = create_project({
        "project_code": "PRJ-QA5",
        "project_name": "QA Project 5",
        "project_type": "Equipment Inspection",
        "start_date": "2026-01-01",
        "deadline": "2026-06-01",
    }, db_path=test_db)

    create_requirement({
        "project_id": p_id,
        "requirement_code": "REQ-NO-AC",
        "description": "Approved requirement missing acceptance criteria",
        "acceptance_criteria": "",
        "status": "Approved",
    }, db_path=test_db)

    results = run_all_quality_checks(db_path=test_db)
    ac_warns = [r for r in results if r["check_name"] == "Missing Acceptance Criteria" and r["check_result"] == "WARNING"]
    assert len(ac_warns) == 1
    assert "REQ-NO-AC" in ac_warns[0]["error_message"]


def test_qa_persists_to_database_and_can_be_queried(test_db):
    run_all_quality_checks(db_path=test_db, save_to_db=True)
    saved = get_latest_quality_checks(db_path=test_db)
    assert len(saved) == 12
    pass_checks = get_latest_quality_checks(result_filter="PASS", db_path=test_db)
    assert len(pass_checks) == 12
