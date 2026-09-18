"""
Requirements Management Module
Handles CRUD operations, search, filters, validation, and clarification tracking for Requirements.
"""

from typing import Any, Dict, List, Optional, Union
from pathlib import Path

from config import logger
from database import execute_query, fetch_all, fetch_one, log_activity, db_transaction
from utils.validators import validate_requirement_data


def create_requirement(data: Dict[str, Any], db_path: Optional[Union[str, Path]] = None) -> int:
    """Validates and creates a new requirement record, linking it to a project."""
    is_valid, errors = validate_requirement_data(data)
    if not is_valid:
        raise ValueError("; ".join(errors))

    # Verify project exists
    project = fetch_one("SELECT project_id, project_code FROM projects WHERE project_id = ?", (data["project_id"],), db_path=db_path)
    if not project:
        raise ValueError(f"Project with ID {data['project_id']} does not exist.")

    # Check for duplicate requirement code
    existing = fetch_one("SELECT requirement_id FROM requirements WHERE requirement_code = ?", (data["requirement_code"].strip(),), db_path=db_path)
    if existing:
        raise ValueError(f"Requirement code '{data['requirement_code']}' already exists.")

    sql = """
        INSERT INTO requirements (
            project_id, requirement_code, description, acceptance_criteria,
            priority, status, clarification_question, owner, due_date,
            created_at, updated_at
        ) VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?,
            datetime('now', 'localtime'), datetime('now', 'localtime')
        )
    """
    params = (
        data["project_id"],
        data["requirement_code"].strip(),
        data["description"].strip(),
        data.get("acceptance_criteria", "").strip() if data.get("acceptance_criteria") else None,
        data.get("priority", "Medium"),
        data.get("status", "Open"),
        data.get("clarification_question", "").strip() if data.get("clarification_question") else None,
        data.get("owner", "").strip() if data.get("owner") else None,
        data.get("due_date"),
    )

    with db_transaction(db_path) as conn:
        req_id = execute_query(sql, params, conn=conn)
        log_activity(
            action_type="CREATE",
            entity_type="REQUIREMENT",
            entity_id=req_id,
            description=f"Created requirement {data['requirement_code']} in project {project['project_code']}",
            conn=conn,
        )

    logger.info(f"Created requirement {data['requirement_code']} with ID {req_id}")
    return req_id


def get_requirement(requirement_id: int, db_path: Optional[Union[str, Path]] = None) -> Optional[Dict[str, Any]]:
    """Retrieves a single requirement by its primary key ID, joining project details."""
    sql = """
        SELECT r.*, p.project_code, p.project_name
        FROM requirements r
        JOIN projects p ON r.project_id = p.project_id
        WHERE r.requirement_id = ?
    """
    return fetch_one(sql, (requirement_id,), db_path=db_path)


def get_requirement_by_code(requirement_code: str, db_path: Optional[Union[str, Path]] = None) -> Optional[Dict[str, Any]]:
    """Retrieves a single requirement by its unique code."""
    sql = """
        SELECT r.*, p.project_code, p.project_name
        FROM requirements r
        JOIN projects p ON r.project_id = p.project_id
        WHERE r.requirement_code = ?
    """
    return fetch_one(sql, (requirement_code.strip(),), db_path=db_path)


def get_requirements(
    project_id: Optional[int] = None,
    status_filter: Optional[str] = None,
    priority_filter: Optional[str] = None,
    search_term: Optional[str] = None,
    needs_clarification_only: bool = False,
    db_path: Optional[Union[str, Path]] = None,
) -> List[Dict[str, Any]]:
    """Retrieves requirements with rich filtering, searching, and project joins."""
    sql = """
        SELECT r.*, p.project_code, p.project_name
        FROM requirements r
        JOIN projects p ON r.project_id = p.project_id
        WHERE 1=1
    """
    params: List[Any] = []

    if project_id:
        sql += " AND r.project_id = ?"
        params.append(project_id)

    if status_filter and status_filter != "All":
        sql += " AND r.status = ?"
        params.append(status_filter)

    if priority_filter and priority_filter != "All":
        sql += " AND r.priority = ?"
        params.append(priority_filter)

    if needs_clarification_only:
        sql += " AND (r.status = 'Clarification Required' OR (r.clarification_question IS NOT NULL AND TRIM(r.clarification_question) != ''))"

    if search_term and search_term.strip():
        term = f"%{search_term.strip()}%"
        sql += " AND (r.requirement_code LIKE ? OR r.description LIKE ? OR r.acceptance_criteria LIKE ? OR r.owner LIKE ?)"
        params.extend([term, term, term, term])

    sql += " ORDER BY r.requirement_id DESC"
    return fetch_all(sql, params, db_path=db_path)


def update_requirement(requirement_id: int, data: Dict[str, Any], db_path: Optional[Union[str, Path]] = None) -> bool:
    """Validates and updates an existing requirement."""
    current = get_requirement(requirement_id, db_path=db_path)
    if not current:
        raise ValueError(f"Requirement with ID {requirement_id} not found.")

    is_valid, errors = validate_requirement_data(data)
    if not is_valid:
        raise ValueError("; ".join(errors))

    # Verify project exists
    project = fetch_one("SELECT project_id, project_code FROM projects WHERE project_id = ?", (data["project_id"],), db_path=db_path)
    if not project:
        raise ValueError(f"Project with ID {data['project_id']} does not exist.")

    # Check for duplicate requirement code if changed
    existing = fetch_one(
        "SELECT requirement_id FROM requirements WHERE requirement_code = ? AND requirement_id != ?",
        (data["requirement_code"].strip(), requirement_id),
        db_path=db_path,
    )
    if existing:
        raise ValueError(f"Requirement code '{data['requirement_code']}' is already in use by another requirement.")

    sql = """
        UPDATE requirements SET
            project_id = ?,
            requirement_code = ?,
            description = ?,
            acceptance_criteria = ?,
            priority = ?,
            status = ?,
            clarification_question = ?,
            owner = ?,
            due_date = ?,
            updated_at = datetime('now', 'localtime')
        WHERE requirement_id = ?
    """
    params = (
        data["project_id"],
        data["requirement_code"].strip(),
        data["description"].strip(),
        data.get("acceptance_criteria", "").strip() if data.get("acceptance_criteria") else None,
        data.get("priority", "Medium"),
        data.get("status", "Open"),
        data.get("clarification_question", "").strip() if data.get("clarification_question") else None,
        data.get("owner", "").strip() if data.get("owner") else None,
        data.get("due_date"),
        requirement_id,
    )

    with db_transaction(db_path) as conn:
        execute_query(sql, params, conn=conn)
        log_activity(
            action_type="UPDATE",
            entity_type="REQUIREMENT",
            entity_id=requirement_id,
            description=f"Updated requirement {data['requirement_code']} (Status: {data.get('status')})",
            conn=conn,
        )

    logger.info(f"Updated requirement ID {requirement_id}")
    return True


def delete_requirement(requirement_id: int, db_path: Optional[Union[str, Path]] = None) -> bool:
    """Deletes a requirement and logs the action."""
    current = get_requirement(requirement_id, db_path=db_path)
    if not current:
        raise ValueError(f"Requirement with ID {requirement_id} not found.")

    with db_transaction(db_path) as conn:
        execute_query("DELETE FROM requirements WHERE requirement_id = ?", (requirement_id,), conn=conn)
        log_activity(
            action_type="DELETE",
            entity_type="REQUIREMENT",
            entity_id=requirement_id,
            description=f"Deleted requirement {current['requirement_code']}",
            conn=conn,
        )

    logger.info(f"Deleted requirement ID {requirement_id}")
    return True
