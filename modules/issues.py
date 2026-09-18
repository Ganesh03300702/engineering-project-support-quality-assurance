"""
Issues and Clarification Tracking Module
Handles CRUD operations, severity tracking, resolutions, and overdue issue monitoring.
"""

from datetime import date
from typing import Any, Dict, List, Optional, Union
from pathlib import Path

from config import logger
from database import execute_query, fetch_all, fetch_one, log_activity, db_transaction
from utils.validators import validate_issue_data, parse_date


def create_issue(data: Dict[str, Any], db_path: Optional[Union[str, Path]] = None) -> int:
    """Validates and registers a new engineering issue or clarification."""
    is_valid, errors = validate_issue_data(data)
    if not is_valid:
        raise ValueError("; ".join(errors))

    # Verify project exists
    project = fetch_one("SELECT project_id, project_code FROM projects WHERE project_id = ?", (data["project_id"],), db_path=db_path)
    if not project:
        raise ValueError(f"Project with ID {data['project_id']} does not exist.")

    # Check requirement if provided
    req_id = data.get("related_requirement_id")
    if req_id:
        req = fetch_one("SELECT requirement_id FROM requirements WHERE requirement_id = ? AND project_id = ?", (req_id, data["project_id"]), db_path=db_path)
        if not req:
            raise ValueError(f"Requirement with ID {req_id} does not belong to project ID {data['project_id']}.")

    # Check task if provided
    task_id = data.get("related_task_id")
    if task_id:
        tsk = fetch_one("SELECT task_id FROM tasks WHERE task_id = ? AND project_id = ?", (task_id, data["project_id"]), db_path=db_path)
        if not tsk:
            raise ValueError(f"Task with ID {task_id} does not belong to project ID {data['project_id']}.")

    # Check duplicate issue code
    existing = fetch_one("SELECT issue_id FROM issues WHERE issue_code = ?", (data["issue_code"].strip(),), db_path=db_path)
    if existing:
        raise ValueError(f"Issue code '{data['issue_code']}' already exists.")

    sql = """
        INSERT INTO issues (
            project_id, issue_code, related_requirement_id, related_task_id,
            description, severity, owner, status, target_date, resolution_notes,
            created_at, updated_at
        ) VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
            datetime('now', 'localtime'), datetime('now', 'localtime')
        )
    """
    params = (
        data["project_id"],
        data["issue_code"].strip(),
        req_id if req_id else None,
        task_id if task_id else None,
        data["description"].strip(),
        data.get("severity", "Medium"),
        data.get("owner", "").strip() if data.get("owner") else None,
        data.get("status", "Open"),
        data.get("target_date"),
        data.get("resolution_notes", "").strip() if data.get("resolution_notes") else None,
    )

    with db_transaction(db_path) as conn:
        issue_id = execute_query(sql, params, conn=conn)
        log_activity(
            action_type="CREATE",
            entity_type="ISSUE",
            entity_id=issue_id,
            description=f"Created issue {data['issue_code']} in project {project['project_code']}",
            conn=conn,
        )

    logger.info(f"Created issue {data['issue_code']} with ID {issue_id}")
    return issue_id


def get_issue(issue_id: int, db_path: Optional[Union[str, Path]] = None) -> Optional[Dict[str, Any]]:
    """Retrieves a single issue by ID with joined project, requirement, and task codes."""
    sql = """
        SELECT i.*, p.project_code, p.project_name, r.requirement_code, t.task_code
        FROM issues i
        JOIN projects p ON i.project_id = p.project_id
        LEFT JOIN requirements r ON i.related_requirement_id = r.requirement_id
        LEFT JOIN tasks t ON i.related_task_id = t.task_id
        WHERE i.issue_id = ?
    """
    return fetch_one(sql, (issue_id,), db_path=db_path)


def get_issue_by_code(issue_code: str, db_path: Optional[Union[str, Path]] = None) -> Optional[Dict[str, Any]]:
    """Retrieves a single issue by code."""
    sql = """
        SELECT i.*, p.project_code, p.project_name, r.requirement_code, t.task_code
        FROM issues i
        JOIN projects p ON i.project_id = p.project_id
        LEFT JOIN requirements r ON i.related_requirement_id = r.requirement_id
        LEFT JOIN tasks t ON i.related_task_id = t.task_id
        WHERE i.issue_code = ?
    """
    return fetch_one(sql, (issue_code.strip(),), db_path=db_path)


def get_issues(
    project_id: Optional[int] = None,
    severity_filter: Optional[str] = None,
    status_filter: Optional[str] = None,
    owner_filter: Optional[str] = None,
    overdue_only: bool = False,
    search_term: Optional[str] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> List[Dict[str, Any]]:
    """Retrieves issues with comprehensive filters and overdue checks."""
    sql = """
        SELECT i.*, p.project_code, p.project_name, r.requirement_code, t.task_code
        FROM issues i
        JOIN projects p ON i.project_id = p.project_id
        LEFT JOIN requirements r ON i.related_requirement_id = r.requirement_id
        LEFT JOIN tasks t ON i.related_task_id = t.task_id
        WHERE 1=1
    """
    params: List[Any] = []

    if project_id:
        sql += " AND i.project_id = ?"
        params.append(project_id)

    if severity_filter and severity_filter != "All":
        sql += " AND i.severity = ?"
        params.append(severity_filter)

    if status_filter and status_filter != "All":
        sql += " AND i.status = ?"
        params.append(status_filter)

    if owner_filter and owner_filter != "All":
        sql += " AND i.owner = ?"
        params.append(owner_filter)

    today_str = date.today().isoformat()
    if overdue_only:
        sql += " AND i.target_date IS NOT NULL AND i.target_date < ? AND i.status NOT IN ('Resolved', 'Closed')"
        params.append(today_str)

    if search_term and search_term.strip():
        term = f"%{search_term.strip()}%"
        sql += " AND (i.issue_code LIKE ? OR i.description LIKE ? OR i.owner LIKE ? OR i.resolution_notes LIKE ?)"
        params.extend([term, term, term, term])

    sql += " ORDER BY i.issue_id DESC"
    rows = fetch_all(sql, params, db_path=db_path)

    for row in rows:
        d = parse_date(row.get("target_date"))
        row["is_overdue"] = bool(d and d < date.today() and row.get("status") not in ("Resolved", "Closed"))

    return rows


def update_issue(issue_id: int, data: Dict[str, Any], db_path: Optional[Union[str, Path]] = None) -> bool:
    """Validates and updates an existing issue."""
    current = get_issue(issue_id, db_path=db_path)
    if not current:
        raise ValueError(f"Issue with ID {issue_id} not found.")

    is_valid, errors = validate_issue_data(data)
    if not is_valid:
        raise ValueError("; ".join(errors))

    # Verify project
    project = fetch_one("SELECT project_id FROM projects WHERE project_id = ?", (data["project_id"],), db_path=db_path)
    if not project:
        raise ValueError(f"Project with ID {data['project_id']} does not exist.")

    req_id = data.get("related_requirement_id")
    if req_id:
        req = fetch_one("SELECT requirement_id FROM requirements WHERE requirement_id = ? AND project_id = ?", (req_id, data["project_id"]), db_path=db_path)
        if not req:
            raise ValueError(f"Requirement with ID {req_id} does not belong to project ID {data['project_id']}.")

    task_id = data.get("related_task_id")
    if task_id:
        tsk = fetch_one("SELECT task_id FROM tasks WHERE task_id = ? AND project_id = ?", (task_id, data["project_id"]), db_path=db_path)
        if not tsk:
            raise ValueError(f"Task with ID {task_id} does not belong to project ID {data['project_id']}.")

    # Check for duplicate code
    existing = fetch_one(
        "SELECT issue_id FROM issues WHERE issue_code = ? AND issue_id != ?",
        (data["issue_code"].strip(), issue_id),
        db_path=db_path,
    )
    if existing:
        raise ValueError(f"Issue code '{data['issue_code']}' is already in use by another issue.")

    sql = """
        UPDATE issues SET
            project_id = ?,
            issue_code = ?,
            related_requirement_id = ?,
            related_task_id = ?,
            description = ?,
            severity = ?,
            owner = ?,
            status = ?,
            target_date = ?,
            resolution_notes = ?,
            updated_at = datetime('now', 'localtime')
        WHERE issue_id = ?
    """
    params = (
        data["project_id"],
        data["issue_code"].strip(),
        req_id if req_id else None,
        task_id if task_id else None,
        data["description"].strip(),
        data.get("severity", "Medium"),
        data.get("owner", "").strip() if data.get("owner") else None,
        data.get("status", "Open"),
        data.get("target_date"),
        data.get("resolution_notes", "").strip() if data.get("resolution_notes") else None,
        issue_id,
    )

    with db_transaction(db_path) as conn:
        execute_query(sql, params, conn=conn)
        log_activity(
            action_type="UPDATE",
            entity_type="ISSUE",
            entity_id=issue_id,
            description=f"Updated issue {data['issue_code']} (Status: {data.get('status')})",
            conn=conn,
        )

    logger.info(f"Updated issue ID {issue_id}")
    return True


def delete_issue(issue_id: int, db_path: Optional[Union[str, Path]] = None) -> bool:
    """Deletes an issue and logs the action."""
    current = get_issue(issue_id, db_path=db_path)
    if not current:
        raise ValueError(f"Issue with ID {issue_id} not found.")

    with db_transaction(db_path) as conn:
        execute_query("DELETE FROM issues WHERE issue_id = ?", (issue_id,), conn=conn)
        log_activity(
            action_type="DELETE",
            entity_type="ISSUE",
            entity_id=issue_id,
            description=f"Deleted issue {current['issue_code']}",
            conn=conn,
        )

    logger.info(f"Deleted issue ID {issue_id}")
    return True
