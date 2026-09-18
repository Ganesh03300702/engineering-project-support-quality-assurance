"""
Comprehensive CRUD tests for Projects, Requirements, Tasks, Deliverables, and Issues.
"""

from datetime import date, timedelta
import pytest
from database import init_db
from modules.projects import (
    create_project,
    get_project,
    get_all_projects,
    update_project,
    delete_project,
)
from modules.requirements import (
    create_requirement,
    get_requirement,
    get_requirements,
    update_requirement,
    delete_requirement,
)
from modules.tasks import (
    create_task,
    get_task,
    get_tasks,
    update_task,
    update_task_progress,
    delete_task,
    get_task_summary,
)
from modules.deliverables import (
    create_deliverable,
    get_deliverable,
    get_deliverables,
    update_deliverable,
    delete_deliverable,
)
from modules.issues import (
    create_issue,
    get_issue,
    get_issues,
    update_issue,
    delete_issue,
)


@pytest.fixture
def test_db(tmp_path):
    db_file = tmp_path / "crud_test.db"
    init_db(db_file)
    return db_file


def test_project_crud_and_duplicate_rejection(test_db):
    data = {
        "project_code": "PRJ-T1",
        "project_name": "Test Project 1",
        "project_type": "Equipment Inspection",
        "start_date": "2026-01-01",
        "deadline": "2026-06-01",
        "priority": "High",
        "status": "Active",
    }
    p_id = create_project(data, db_path=test_db)
    assert p_id > 0

    # Duplicate code rejection
    with pytest.raises(ValueError, match="already exists"):
        create_project(data, db_path=test_db)

    # Read
    project = get_project(p_id, db_path=test_db)
    assert project["project_name"] == "Test Project 1"

    # Update
    update_project(p_id, {**data, "project_name": "Updated Project Name"}, db_path=test_db)
    updated = get_project(p_id, db_path=test_db)
    assert updated["project_name"] == "Updated Project Name"

    # Delete
    assert delete_project(p_id, db_path=test_db) is True
    assert get_project(p_id, db_path=test_db) is None


def test_project_deletion_blocked_by_dependencies(test_db):
    p_id = create_project({
        "project_code": "PRJ-DEP",
        "project_name": "Dependency Parent",
        "project_type": "Equipment Inspection",
        "start_date": "2026-01-01",
        "deadline": "2026-06-01",
    }, db_path=test_db)

    create_requirement({
        "project_id": p_id,
        "requirement_code": "REQ-CHILD",
        "description": "Child requirement",
    }, db_path=test_db)

    # Deletion without cascade must fail
    with pytest.raises(ValueError, match="Cannot delete project .* dependent records"):
        delete_project(p_id, cascade=False, db_path=test_db)

    # Cascade deletion should succeed
    assert delete_project(p_id, cascade=True, db_path=test_db) is True
    assert get_project(p_id, db_path=test_db) is None


def test_requirement_crud(test_db):
    p_id = create_project({
        "project_code": "PRJ-REQ",
        "project_name": "Req Parent",
        "project_type": "Equipment Inspection",
        "start_date": "2026-01-01",
        "deadline": "2026-06-01",
    }, db_path=test_db)

    req_data = {
        "project_id": p_id,
        "requirement_code": "REQ-001",
        "description": "Initial requirement description",
        "acceptance_criteria": "Must pass 50 cycles",
        "status": "Open",
        "priority": "High",
    }
    r_id = create_requirement(req_data, db_path=test_db)
    assert r_id > 0

    req = get_requirement(r_id, db_path=test_db)
    assert req["requirement_code"] == "REQ-001"
    assert req["project_code"] == "PRJ-REQ"

    # Filter requirements
    all_reqs = get_requirements(project_id=p_id, status_filter="Open", db_path=test_db)
    assert len(all_reqs) == 1

    # Update
    update_requirement(r_id, {**req_data, "status": "Approved"}, db_path=test_db)
    updated = get_requirement(r_id, db_path=test_db)
    assert updated["status"] == "Approved"

    # Delete
    assert delete_requirement(r_id, db_path=test_db) is True
    assert get_requirement(r_id, db_path=test_db) is None


def test_task_crud_and_progress_validation(test_db):
    p_id = create_project({
        "project_code": "PRJ-TSK",
        "project_name": "Task Parent",
        "project_type": "Equipment Inspection",
        "start_date": "2026-01-01",
        "deadline": "2026-06-01",
    }, db_path=test_db)

    task_data = {
        "project_id": p_id,
        "task_code": "TSK-001",
        "task_description": "Execute torque test",
        "assigned_to": "Engineer Alex",
        "priority": "High",
        "start_date": "2026-01-05",
        "due_date": "2026-01-20",
        "status": "In Progress",
        "progress_percentage": 25,
    }
    t_id = create_task(task_data, db_path=test_db)
    assert t_id > 0

    task = get_task(t_id, db_path=test_db)
    assert task["task_code"] == "TSK-001"
    assert task["progress_percentage"] == 25

    # Update task progress helper
    update_task_progress(t_id, progress=100, db_path=test_db)
    task_done = get_task(t_id, db_path=test_db)
    assert task_done["progress_percentage"] == 100
    assert task_done["status"] == "Completed"

    # Summary metrics
    summary = get_task_summary(project_id=p_id, db_path=test_db)
    assert summary["total"] == 1
    assert summary["completed"] == 1
    assert summary["avg_progress"] == 100.0

    # Delete
    assert delete_task(t_id, db_path=test_db) is True
    assert get_task(t_id, db_path=test_db) is None


def test_deliverable_crud_and_review_workflow(test_db):
    p_id = create_project({
        "project_code": "PRJ-DEL",
        "project_name": "Deliverable Parent",
        "project_type": "Documentation Standardization",
        "start_date": "2026-01-01",
        "deadline": "2026-06-01",
    }, db_path=test_db)

    deliv_data = {
        "project_id": p_id,
        "deliverable_code": "DEL-001",
        "deliverable_name": "Calibration Protocol",
        "deliverable_type": "Test Protocol",
        "version": "v1.0",
        "prepared_by": "Dr. Miller",
        "reviewer": "Sarah Chen",
        "planned_date": "2026-02-01",
        "submission_date": "2026-02-01",
        "review_status": "Submitted",
        "file_name": "Calib_Protocol_v1.0.pdf",
    }
    d_id = create_deliverable(deliv_data, db_path=test_db)
    assert d_id > 0

    d = get_deliverable(d_id, db_path=test_db)
    assert d["deliverable_code"] == "DEL-001"

    # Pending review filter
    pending = get_deliverables(project_id=p_id, pending_review_only=True, db_path=test_db)
    assert len(pending) == 1

    # Update to Approved
    update_deliverable(d_id, {**deliv_data, "review_status": "Approved"}, db_path=test_db)
    approved = get_deliverable(d_id, db_path=test_db)
    assert approved["review_status"] == "Approved"

    # Delete
    assert delete_deliverable(d_id, db_path=test_db) is True
    assert get_deliverable(d_id, db_path=test_db) is None


def test_issue_crud_and_overdue_tracking(test_db):
    p_id = create_project({
        "project_code": "PRJ-ISS",
        "project_name": "Issue Parent",
        "project_type": "Component Quality Review",
        "start_date": "2026-01-01",
        "deadline": "2026-06-01",
    }, db_path=test_db)

    past_date = (date.today() - timedelta(days=5)).isoformat()
    issue_data = {
        "project_id": p_id,
        "issue_code": "ISS-001",
        "description": "Bearing vibration frequency exceeds specification",
        "severity": "Critical",
        "owner": "David Kim",
        "status": "Open",
        "target_date": past_date,
    }
    i_id = create_issue(issue_data, db_path=test_db)
    assert i_id > 0

    issue = get_issue(i_id, db_path=test_db)
    assert issue["severity"] == "Critical"

    # Overdue filter
    overdue_issues = get_issues(project_id=p_id, overdue_only=True, db_path=test_db)
    assert len(overdue_issues) == 1
    assert overdue_issues[0]["is_overdue"] is True

    # Resolve issue
    update_issue(i_id, {**issue_data, "status": "Resolved", "resolution_notes": "Damper installed"}, db_path=test_db)
    resolved = get_issue(i_id, db_path=test_db)
    assert resolved["status"] == "Resolved"

    # Delete
    assert delete_issue(i_id, db_path=test_db) is True
    assert get_issue(i_id, db_path=test_db) is None
