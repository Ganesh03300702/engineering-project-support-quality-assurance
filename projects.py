"""
Projects Management Module
Handles CRUD operations, search, filters, validation, dependency checks, and audit logging for Projects.
"""

from typing import Any, Dict, List, Optional, Union
from pathlib import Path

from config import logger
from database import execute_query, fetch_all, fetch_one, log_activity, db_transaction
from utils.validators import validate_project_data


def get_project_dependencies_count(project_id: int, db_path: Optional[Union[str, Path]] = None) -> Dict[str, int]:
    """Counts related child records across requirements, tasks, deliverables, and issues."""
    counts = {
        "requirements": 0,
        "tasks": 0,
        "deliverables": 0,
        "issues": 0,
    }
    r = fetch_one("SELECT COUNT(*) as count FROM requirements WHERE project_id = ?", (project_id,), db_path=db_path)
    if r:
        counts["requirements"] = r["count"]

    t = fetch_one("SELECT COUNT(*) as count FROM tasks WHERE project_id = ?", (project_id,), db_path=db_path)
    if t:
        counts["tasks"] = t["count"]

    d = fetch_one("SELECT COUNT(*) as count FROM deliverables WHERE project_id = ?", (project_id,), db_path=db_path)
    if d:
        counts["deliverables"] = d["count"]

    i = fetch_one("SELECT COUNT(*) as count FROM issues WHERE project_id = ?", (project_id,), db_path=db_path)
    if i:
        counts["issues"] = i["count"]

    counts["total"] = sum(counts.values())
    return counts


def create_project(data: Dict[str, Any], db_path: Optional[Union[str, Path]] = None) -> int:
    """Validates and creates a new project record, logging the activity."""
    is_valid, errors = validate_project_data(data)
    if not is_valid:
        raise ValueError("; ".join(errors))

    # Check for duplicate project code
    existing = fetch_one("SELECT project_id FROM projects WHERE project_code = ?", (data["project_code"].strip(),), db_path=db_path)
    if existing:
        raise ValueError(f"Project code '{data['project_code']}' already exists.")

    sql = """
        INSERT INTO projects (
            project_code, project_name, project_type, description,
            stakeholder, team_lead, start_date, deadline, priority, status,
            created_at, updated_at
        ) VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
            datetime('now', 'localtime'), datetime('now', 'localtime')
        )
    """
    params = (
        data["project_code"].strip(),
        data["project_name"].strip(),
        data["project_type"].strip(),
        data.get("description", "").strip() if data.get("description") else None,
        data.get("stakeholder", "").strip() if data.get("stakeholder") else None,
        data.get("team_lead", "").strip() if data.get("team_lead") else None,
        data["start_date"],
        data["deadline"],
        data.get("priority", "Medium"),
        data.get("status", "Planned"),
    )

    with db_transaction(db_path) as conn:
        project_id = execute_query(sql, params, conn=conn)
        log_activity(
            action_type="CREATE",
            entity_type="PROJECT",
            entity_id=project_id,
            description=f"Created project {data['project_code']} ({data['project_name']})",
            conn=conn,
        )

    logger.info(f"Created project {data['project_code']} with ID {project_id}")
    return project_id


def get_project(project_id: int, db_path: Optional[Union[str, Path]] = None) -> Optional[Dict[str, Any]]:
    """Retrieves a single project by its primary key ID."""
    sql = "SELECT * FROM projects WHERE project_id = ?"
    return fetch_one(sql, (project_id,), db_path=db_path)


def get_project_by_code(project_code: str, db_path: Optional[Union[str, Path]] = None) -> Optional[Dict[str, Any]]:
    """Retrieves a single project by its unique code."""
    sql = "SELECT * FROM projects WHERE project_code = ?"
    return fetch_one(sql, (project_code.strip(),), db_path=db_path)


def get_all_projects(
    status_filter: Optional[str] = None,
    priority_filter: Optional[str] = None,
    search_term: Optional[str] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> List[Dict[str, Any]]:
    """Retrieves all projects matching optional filters and search terms."""
    sql = "SELECT * FROM projects WHERE 1=1"
    params: List[Any] = []

    if status_filter and status_filter != "All":
        sql += " AND status = ?"
        params.append(status_filter)

    if priority_filter and priority_filter != "All":
        sql += " AND priority = ?"
        params.append(priority_filter)

    if search_term and search_term.strip():
        term = f"%{search_term.strip()}%"
        sql += " AND (project_code LIKE ? OR project_name LIKE ? OR description LIKE ? OR stakeholder LIKE ? OR team_lead LIKE ?)"
        params.extend([term, term, term, term, term])

    sql += " ORDER BY project_id DESC"
    return fetch_all(sql, params, db_path=db_path)


def update_project(project_id: int, data: Dict[str, Any], db_path: Optional[Union[str, Path]] = None) -> bool:
    """Validates and updates an existing project record."""
    current = get_project(project_id, db_path=db_path)
    if not current:
        raise ValueError(f"Project with ID {project_id} not found.")

    is_valid, errors = validate_project_data(data)
    if not is_valid:
        raise ValueError("; ".join(errors))

    # Check for duplicate project code if changed
    existing = fetch_one(
        "SELECT project_id FROM projects WHERE project_code = ? AND project_id != ?",
        (data["project_code"].strip(), project_id),
        db_path=db_path,
    )
    if existing:
        raise ValueError(f"Project code '{data['project_code']}' is already in use by another project.")

    sql = """
        UPDATE projects SET
            project_code = ?,
            project_name = ?,
            project_type = ?,
            description = ?,
            stakeholder = ?,
            team_lead = ?,
            start_date = ?,
            deadline = ?,
            priority = ?,
            status = ?,
            updated_at = datetime('now', 'localtime')
        WHERE project_id = ?
    """
    params = (
        data["project_code"].strip(),
        data["project_name"].strip(),
        data["project_type"].strip(),
        data.get("description", "").strip() if data.get("description") else None,
        data.get("stakeholder", "").strip() if data.get("stakeholder") else None,
        data.get("team_lead", "").strip() if data.get("team_lead") else None,
        data["start_date"],
        data["deadline"],
        data.get("priority", "Medium"),
        data.get("status", "Planned"),
        project_id,
    )

    with db_transaction(db_path) as conn:
        execute_query(sql, params, conn=conn)
        log_activity(
            action_type="UPDATE",
            entity_type="PROJECT",
            entity_id=project_id,
            description=f"Updated project {data['project_code']} (Status: {data.get('status')})",
            conn=conn,
        )

    logger.info(f"Updated project ID {project_id}")
    return True


def delete_project(project_id: int, cascade: bool = False, db_path: Optional[Union[str, Path]] = None) -> bool:
    """
    Deletes a project record. If cascade=False, raises ValueError if dependent records exist.
    If cascade=True, safe cascade deletion is performed.
    """
    current = get_project(project_id, db_path=db_path)
    if not current:
        raise ValueError(f"Project with ID {project_id} not found.")

    deps = get_project_dependencies_count(project_id, db_path=db_path)
    if not cascade and deps["total"] > 0:
        detail = ", ".join(f"{k}: {v}" for k, v in deps.items() if k != "total" and v > 0)
        raise ValueError(
            f"Cannot delete project '{current['project_code']}' because it has dependent records ({detail}). "
            "Please delete or reassign them first, or confirm cascade deletion."
        )

    with db_transaction(db_path) as conn:
        # If cascading manually or relying on foreign key cascade
        execute_query("DELETE FROM projects WHERE project_id = ?", (project_id,), conn=conn)
        log_activity(
            action_type="DELETE",
            entity_type="PROJECT",
            entity_id=project_id,
            description=f"Deleted project {current['project_code']} ({current['project_name']})",
            conn=conn,
        )

    logger.info(f"Deleted project ID {project_id}")
    return True
