"""
Deliverables Management Module
Handles CRUD operations, revision tracking, review workflows, and deliverable status metrics.
"""

from typing import Any, Dict, List, Optional, Union
from pathlib import Path

from config import logger
from database import execute_query, fetch_all, fetch_one, log_activity, db_transaction
from utils.validators import validate_deliverable_data


def create_deliverable(data: Dict[str, Any], db_path: Optional[Union[str, Path]] = None) -> int:
    """Validates and registers a new engineering deliverable."""
    is_valid, errors = validate_deliverable_data(data)
    if not is_valid:
        raise ValueError("; ".join(errors))

    # Verify project exists
    project = fetch_one("SELECT project_id, project_code FROM projects WHERE project_id = ?", (data["project_id"],), db_path=db_path)
    if not project:
        raise ValueError(f"Project with ID {data['project_id']} does not exist.")

    # Check for duplicate deliverable code
    existing = fetch_one("SELECT deliverable_id FROM deliverables WHERE deliverable_code = ?", (data["deliverable_code"].strip(),), db_path=db_path)
    if existing:
        raise ValueError(f"Deliverable code '{data['deliverable_code']}' already exists.")

    sql = """
        INSERT INTO deliverables (
            project_id, deliverable_code, deliverable_name, deliverable_type,
            version, prepared_by, reviewer, planned_date, submission_date,
            review_status, file_name, comments, created_at, updated_at
        ) VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
            datetime('now', 'localtime'), datetime('now', 'localtime')
        )
    """
    params = (
        data["project_id"],
        data["deliverable_code"].strip(),
        data["deliverable_name"].strip(),
        data.get("deliverable_type", "").strip() if data.get("deliverable_type") else None,
        data.get("version", "v1.0").strip(),
        data.get("prepared_by", "").strip() if data.get("prepared_by") else None,
        data.get("reviewer", "").strip() if data.get("reviewer") else None,
        data.get("planned_date"),
        data.get("submission_date"),
        data.get("review_status", "Draft"),
        data.get("file_name", "").strip() if data.get("file_name") else None,
        data.get("comments", "").strip() if data.get("comments") else None,
    )

    with db_transaction(db_path) as conn:
        del_id = execute_query(sql, params, conn=conn)
        log_activity(
            action_type="CREATE",
            entity_type="DELIVERABLE",
            entity_id=del_id,
            description=f"Created deliverable {data['deliverable_code']} in project {project['project_code']}",
            conn=conn,
        )

    logger.info(f"Created deliverable {data['deliverable_code']} with ID {del_id}")
    return del_id


def get_deliverable(deliverable_id: int, db_path: Optional[Union[str, Path]] = None) -> Optional[Dict[str, Any]]:
    """Retrieves a single deliverable by ID with joined project information."""
    sql = """
        SELECT d.*, p.project_code, p.project_name
        FROM deliverables d
        JOIN projects p ON d.project_id = p.project_id
        WHERE d.deliverable_id = ?
    """
    return fetch_one(sql, (deliverable_id,), db_path=db_path)


def get_deliverable_by_code(deliverable_code: str, db_path: Optional[Union[str, Path]] = None) -> Optional[Dict[str, Any]]:
    """Retrieves a single deliverable by code."""
    sql = """
        SELECT d.*, p.project_code, p.project_name
        FROM deliverables d
        JOIN projects p ON d.project_id = p.project_id
        WHERE d.deliverable_code = ?
    """
    return fetch_one(sql, (deliverable_code.strip(),), db_path=db_path)


def get_deliverables(
    project_id: Optional[int] = None,
    review_status_filter: Optional[str] = None,
    deliverable_type_filter: Optional[str] = None,
    pending_review_only: bool = False,
    rework_required_only: bool = False,
    search_term: Optional[str] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> List[Dict[str, Any]]:
    """Retrieves deliverables with various workflow filters."""
    sql = """
        SELECT d.*, p.project_code, p.project_name
        FROM deliverables d
        JOIN projects p ON d.project_id = p.project_id
        WHERE 1=1
    """
    params: List[Any] = []

    if project_id:
        sql += " AND d.project_id = ?"
        params.append(project_id)

    if review_status_filter and review_status_filter != "All":
        sql += " AND d.review_status = ?"
        params.append(review_status_filter)

    if deliverable_type_filter and deliverable_type_filter != "All":
        sql += " AND d.deliverable_type = ?"
        params.append(deliverable_type_filter)

    if pending_review_only:
        sql += " AND d.review_status IN ('Submitted', 'Under Review')"

    if rework_required_only:
        sql += " AND d.review_status = 'Rework Required'"

    if search_term and search_term.strip():
        term = f"%{search_term.strip()}%"
        sql += " AND (d.deliverable_code LIKE ? OR d.deliverable_name LIKE ? OR d.prepared_by LIKE ? OR d.reviewer LIKE ? OR d.file_name LIKE ?)"
        params.extend([term, term, term, term, term])

    sql += " ORDER BY d.deliverable_id DESC"
    return fetch_all(sql, params, db_path=db_path)


def update_deliverable(deliverable_id: int, data: Dict[str, Any], db_path: Optional[Union[str, Path]] = None) -> bool:
    """Validates and updates an existing deliverable record."""
    current = get_deliverable(deliverable_id, db_path=db_path)
    if not current:
        raise ValueError(f"Deliverable with ID {deliverable_id} not found.")

    is_valid, errors = validate_deliverable_data(data)
    if not is_valid:
        raise ValueError("; ".join(errors))

    # Verify project exists
    project = fetch_one("SELECT project_id FROM projects WHERE project_id = ?", (data["project_id"],), db_path=db_path)
    if not project:
        raise ValueError(f"Project with ID {data['project_id']} does not exist.")

    # Check for duplicate code
    existing = fetch_one(
        "SELECT deliverable_id FROM deliverables WHERE deliverable_code = ? AND deliverable_id != ?",
        (data["deliverable_code"].strip(), deliverable_id),
        db_path=db_path,
    )
    if existing:
        raise ValueError(f"Deliverable code '{data['deliverable_code']}' is already in use by another deliverable.")

    sql = """
        UPDATE deliverables SET
            project_id = ?,
            deliverable_code = ?,
            deliverable_name = ?,
            deliverable_type = ?,
            version = ?,
            prepared_by = ?,
            reviewer = ?,
            planned_date = ?,
            submission_date = ?,
            review_status = ?,
            file_name = ?,
            comments = ?,
            updated_at = datetime('now', 'localtime')
        WHERE deliverable_id = ?
    """
    params = (
        data["project_id"],
        data["deliverable_code"].strip(),
        data["deliverable_name"].strip(),
        data.get("deliverable_type", "").strip() if data.get("deliverable_type") else None,
        data.get("version", "v1.0").strip(),
        data.get("prepared_by", "").strip() if data.get("prepared_by") else None,
        data.get("reviewer", "").strip() if data.get("reviewer") else None,
        data.get("planned_date"),
        data.get("submission_date"),
        data.get("review_status", "Draft"),
        data.get("file_name", "").strip() if data.get("file_name") else None,
        data.get("comments", "").strip() if data.get("comments") else None,
        deliverable_id,
    )

    with db_transaction(db_path) as conn:
        execute_query(sql, params, conn=conn)
        log_activity(
            action_type="UPDATE",
            entity_type="DELIVERABLE",
            entity_id=deliverable_id,
            description=f"Updated deliverable {data['deliverable_code']} (Status: {data.get('review_status')}, Ver: {data.get('version')})",
            conn=conn,
        )

    logger.info(f"Updated deliverable ID {deliverable_id}")
    return True


def delete_deliverable(deliverable_id: int, db_path: Optional[Union[str, Path]] = None) -> bool:
    """Deletes a deliverable and logs the action."""
    current = get_deliverable(deliverable_id, db_path=db_path)
    if not current:
        raise ValueError(f"Deliverable with ID {deliverable_id} not found.")

    with db_transaction(db_path) as conn:
        execute_query("DELETE FROM deliverables WHERE deliverable_id = ?", (deliverable_id,), conn=conn)
        log_activity(
            action_type="DELETE",
            entity_type="DELIVERABLE",
            entity_id=deliverable_id,
            description=f"Deleted deliverable {current['deliverable_code']}",
            conn=conn,
        )

    logger.info(f"Deleted deliverable ID {deliverable_id}")
    return True
