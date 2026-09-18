"""
Task Management Module
Handles CRUD operations, task tracking, progress updates, overdue detection, and metrics.
"""

from datetime import date
from typing import Any, Dict, List, Optional, Union
from pathlib import Path

from config import logger
from database import execute_query, fetch_all, fetch_one, log_activity, db_transaction
from utils.validators import validate_task_data, validate_progress, parse_date


def create_task(data: Dict[str, Any], db_path: Optional[Union[str, Path]] = None) -> int:
    """Validates and creates a new task record."""
    is_valid, errors = validate_task_data(data)
    if not is_valid:
        raise ValueError("; ".join(errors))

    # Check project exists
    project = fetch_one("SELECT project_id, project_code FROM projects WHERE project_id = ?", (data["project_id"],), db_path=db_path)
    if not project:
        raise ValueError(f"Project with ID {data['project_id']} does not exist.")

    # Check requirement exists if provided
    req_id = data.get("requirement_id")
    if req_id:
        req = fetch_one("SELECT requirement_id FROM requirements WHERE requirement_id = ? AND project_id = ?", (req_id, data["project_id"]), db_path=db_path)
        if not req:
            raise ValueError(f"Requirement with ID {req_id} does not belong to project ID {data['project_id']}.")

    # Check duplicate task code
    existing = fetch_one("SELECT task_id FROM tasks WHERE task_code = ?", (data["task_code"].strip(),), db_path=db_path)
    if existing:
        raise ValueError(f"Task code '{data['task_code']}' already exists.")

    progress = int(data.get("progress_percentage", 0))
    status = data.get("status", "Not Started")
    # Auto adjust progress if completed
    if status == "Completed" and progress < 100:
        progress = 100

    sql = """
        INSERT INTO tasks (
            project_id, requirement_id, task_code, task_description,
            assigned_to, priority, start_date, due_date, status,
            progress_percentage, notes, created_at, updated_at
        ) VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
            datetime('now', 'localtime'), datetime('now', 'localtime')
        )
    """
    params = (
        data["project_id"],
        req_id if req_id else None,
        data["task_code"].strip(),
        data["task_description"].strip(),
        data.get("assigned_to", "").strip() if data.get("assigned_to") else None,
        data.get("priority", "Medium"),
        data.get("start_date"),
        data.get("due_date"),
        status,
        progress,
        data.get("notes", "").strip() if data.get("notes") else None,
    )

    with db_transaction(db_path) as conn:
        task_id = execute_query(sql, params, conn=conn)
        log_activity(
            action_type="CREATE",
            entity_type="TASK",
            entity_id=task_id,
            description=f"Created task {data['task_code']} in project {project['project_code']}",
            conn=conn,
        )

    logger.info(f"Created task {data['task_code']} with ID {task_id}")
    return task_id


def get_task(task_id: int, db_path: Optional[Union[str, Path]] = None) -> Optional[Dict[str, Any]]:
    """Retrieves a single task by ID with joined project and requirement codes."""
    sql = """
        SELECT t.*, p.project_code, p.project_name, r.requirement_code
        FROM tasks t
        JOIN projects p ON t.project_id = p.project_id
        LEFT JOIN requirements r ON t.requirement_id = r.requirement_id
        WHERE t.task_id = ?
    """
    return fetch_one(sql, (task_id,), db_path=db_path)


def get_task_by_code(task_code: str, db_path: Optional[Union[str, Path]] = None) -> Optional[Dict[str, Any]]:
    """Retrieves a single task by unique code."""
    sql = """
        SELECT t.*, p.project_code, p.project_name, r.requirement_code
        FROM tasks t
        JOIN projects p ON t.project_id = p.project_id
        LEFT JOIN requirements r ON t.requirement_id = r.requirement_id
        WHERE t.task_code = ?
    """
    return fetch_one(sql, (task_code.strip(),), db_path=db_path)


def get_tasks(
    project_id: Optional[int] = None,
    status_filter: Optional[str] = None,
    priority_filter: Optional[str] = None,
    assigned_to_filter: Optional[str] = None,
    overdue_only: bool = False,
    search_term: Optional[str] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> List[Dict[str, Any]]:
    """Retrieves tasks with comprehensive filters, search, and overdue calculation."""
    sql = """
        SELECT t.*, p.project_code, p.project_name, r.requirement_code
        FROM tasks t
        JOIN projects p ON t.project_id = p.project_id
        LEFT JOIN requirements r ON t.requirement_id = r.requirement_id
        WHERE 1=1
    """
    params: List[Any] = []

    if project_id:
        sql += " AND t.project_id = ?"
        params.append(project_id)

    if status_filter and status_filter != "All":
        sql += " AND t.status = ?"
        params.append(status_filter)

    if priority_filter and priority_filter != "All":
        sql += " AND t.priority = ?"
        params.append(priority_filter)

    if assigned_to_filter and assigned_to_filter != "All":
        sql += " AND t.assigned_to = ?"
        params.append(assigned_to_filter)

    today_str = date.today().isoformat()
    if overdue_only:
        sql += " AND t.due_date IS NOT NULL AND t.due_date < ? AND t.status != 'Completed'"
        params.append(today_str)

    if search_term and search_term.strip():
        term = f"%{search_term.strip()}%"
        sql += " AND (t.task_code LIKE ? OR t.task_description LIKE ? OR t.assigned_to LIKE ? OR t.notes LIKE ?)"
        params.extend([term, term, term, term])

    sql += " ORDER BY t.task_id DESC"
    rows = fetch_all(sql, params, db_path=db_path)

    # Annotate overdue status
    for row in rows:
        d = parse_date(row.get("due_date"))
        row["is_overdue"] = bool(d and d < date.today() and row.get("status") != "Completed")

    return rows


def update_task(task_id: int, data: Dict[str, Any], db_path: Optional[Union[str, Path]] = None) -> bool:
    """Validates and updates an existing task."""
    current = get_task(task_id, db_path=db_path)
    if not current:
        raise ValueError(f"Task with ID {task_id} not found.")

    is_valid, errors = validate_task_data(data)
    if not is_valid:
        raise ValueError("; ".join(errors))

    project = fetch_one("SELECT project_id FROM projects WHERE project_id = ?", (data["project_id"],), db_path=db_path)
    if not project:
        raise ValueError(f"Project with ID {data['project_id']} does not exist.")

    req_id = data.get("requirement_id")
    if req_id:
        req = fetch_one("SELECT requirement_id FROM requirements WHERE requirement_id = ? AND project_id = ?", (req_id, data["project_id"]), db_path=db_path)
        if not req:
            raise ValueError(f"Requirement with ID {req_id} does not belong to project ID {data['project_id']}.")

    # Check for duplicate code
    existing = fetch_one(
        "SELECT task_id FROM tasks WHERE task_code = ? AND task_id != ?",
        (data["task_code"].strip(), task_id),
        db_path=db_path,
    )
    if existing:
        raise ValueError(f"Task code '{data['task_code']}' is already in use by another task.")

    progress = int(data.get("progress_percentage", 0))
    status = data.get("status", "Not Started")
    if status == "Completed" and progress < 100:
        progress = 100

    sql = """
        UPDATE tasks SET
            project_id = ?,
            requirement_id = ?,
            task_code = ?,
            task_description = ?,
            assigned_to = ?,
            priority = ?,
            start_date = ?,
            due_date = ?,
            status = ?,
            progress_percentage = ?,
            notes = ?,
            updated_at = datetime('now', 'localtime')
        WHERE task_id = ?
    """
    params = (
        data["project_id"],
        req_id if req_id else None,
        data["task_code"].strip(),
        data["task_description"].strip(),
        data.get("assigned_to", "").strip() if data.get("assigned_to") else None,
        data.get("priority", "Medium"),
        data.get("start_date"),
        data.get("due_date"),
        status,
        progress,
        data.get("notes", "").strip() if data.get("notes") else None,
        task_id,
    )

    with db_transaction(db_path) as conn:
        execute_query(sql, params, conn=conn)
        log_activity(
            action_type="UPDATE",
            entity_type="TASK",
            entity_id=task_id,
            description=f"Updated task {data['task_code']} (Status: {status}, Progress: {progress}%)",
            conn=conn,
        )

    logger.info(f"Updated task ID {task_id}")
    return True


def update_task_progress(
    task_id: int,
    progress: int,
    status: Optional[str] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> bool:
    """Quick helper to update progress percentage and optionally status."""
    ok, msg = validate_progress(progress)
    if not ok:
        raise ValueError(msg)

    current = get_task(task_id, db_path=db_path)
    if not current:
        raise ValueError(f"Task with ID {task_id} not found.")

    new_status = status or current["status"]
    if progress == 100 and new_status != "Completed":
        new_status = "Completed"
    elif progress < 100 and new_status == "Completed":
        new_status = "In Progress"

    sql = """
        UPDATE tasks SET
            progress_percentage = ?,
            status = ?,
            updated_at = datetime('now', 'localtime')
        WHERE task_id = ?
    """
    with db_transaction(db_path) as conn:
        execute_query(sql, (progress, new_status, task_id), conn=conn)
        log_activity(
            action_type="STATUS_CHANGE",
            entity_type="TASK",
            entity_id=task_id,
            description=f"Task {current['task_code']} updated to {progress}% ({new_status})",
            conn=conn,
        )
    return True


def delete_task(task_id: int, db_path: Optional[Union[str, Path]] = None) -> bool:
    """Deletes a task and logs the action."""
    current = get_task(task_id, db_path=db_path)
    if not current:
        raise ValueError(f"Task with ID {task_id} not found.")

    with db_transaction(db_path) as conn:
        execute_query("DELETE FROM tasks WHERE task_id = ?", (task_id,), conn=conn)
        log_activity(
            action_type="DELETE",
            entity_type="TASK",
            entity_id=task_id,
            description=f"Deleted task {current['task_code']}",
            conn=conn,
        )

    logger.info(f"Deleted task ID {task_id}")
    return True


def get_task_summary(project_id: Optional[int] = None, db_path: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
    """Calculates high-level task metrics for dashboards and reports."""
    tasks = get_tasks(project_id=project_id, db_path=db_path)
    total = len(tasks)
    if total == 0:
        return {
            "total": 0,
            "completed": 0,
            "in_progress": 0,
            "not_started": 0,
            "blocked": 0,
            "under_review": 0,
            "overdue": 0,
            "avg_progress": 0.0,
        }

    completed = sum(1 for t in tasks if t["status"] == "Completed")
    in_progress = sum(1 for t in tasks if t["status"] == "In Progress")
    not_started = sum(1 for t in tasks if t["status"] == "Not Started")
    blocked = sum(1 for t in tasks if t["status"] == "Blocked")
    under_review = sum(1 for t in tasks if t["status"] == "Under Review")
    overdue = sum(1 for t in tasks if t.get("is_overdue", False))
    avg_progress = sum(t["progress_percentage"] for t in tasks) / total

    return {
        "total": total,
        "completed": completed,
        "in_progress": in_progress,
        "not_started": not_started,
        "blocked": blocked,
        "under_review": under_review,
        "overdue": overdue,
        "avg_progress": round(avg_progress, 1),
    }
