"""
Quality Assurance Engine
Implements 12 comprehensive automated engineering audit checks against the SQLite database.
Generates auditable findings with PASS, FAIL, and WARNING statuses.
"""

from datetime import date, datetime
from typing import Any, Dict, List, Optional, Union
from pathlib import Path

from config import logger
from database import execute_query, fetch_all, log_activity, db_transaction
from utils.constants import (
    PROJECT_STATUSES,
    PROJECT_PRIORITIES,
    REQUIREMENT_STATUSES,
    REQUIREMENT_PRIORITIES,
    TASK_STATUSES,
    TASK_PRIORITIES,
    DELIVERABLE_REVIEW_STATUSES,
    ISSUE_STATUSES,
    ISSUE_SEVERITIES,
)
from utils.validators import parse_date


def run_all_quality_checks(
    project_id: Optional[int] = None,
    save_to_db: bool = True,
    db_path: Optional[Union[str, Path]] = None,
) -> List[Dict[str, Any]]:
    """Executes all 12 quality assurance audit rules."""
    results: List[Dict[str, Any]] = []

    results.extend(_check_required_fields(project_id, db_path))
    results.extend(_check_duplicate_codes(project_id, db_path))
    results.extend(_check_invalid_project_references(project_id, db_path))
    results.extend(_check_invalid_dates(project_id, db_path))
    results.extend(_check_missing_reviewer_submitted_deliverables(project_id, db_path))
    results.extend(_check_incomplete_deliverable_info(project_id, db_path))
    results.extend(_check_invalid_task_progress(project_id, db_path))
    results.extend(_check_overdue_tasks(project_id, db_path))
    results.extend(_check_open_requirements_clarification(project_id, db_path))
    results.extend(_check_invalid_status_values(project_id, db_path))
    results.extend(_check_missing_task_owners(project_id, db_path))
    results.extend(_check_missing_acceptance_criteria(project_id, db_path))

    if save_to_db:
        _save_quality_checks(results, project_id, db_path)

    logger.info(f"QA Engine finished run: {len(results)} findings.")
    return results


def _save_quality_checks(
    results: List[Dict[str, Any]],
    project_id: Optional[int] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> None:
    """Stores latest quality check results in quality_checks table."""
    with db_transaction(db_path) as conn:
        if project_id:
            execute_query("DELETE FROM quality_checks WHERE project_id = ?", (project_id,), conn=conn)
        else:
            execute_query("DELETE FROM quality_checks", conn=conn)

        insert_sql = """
            INSERT INTO quality_checks (
                project_id, entity_type, entity_id, check_name,
                check_result, error_message, checked_at
            ) VALUES (?, ?, ?, ?, ?, ?, datetime('now', 'localtime'))
        """
        for r in results:
            execute_query(
                insert_sql,
                (
                    r.get("project_id"),
                    r["entity_type"],
                    r.get("entity_id"),
                    r["check_name"],
                    r["check_result"],
                    r["error_message"],
                ),
                conn=conn,
            )

        pass_count = sum(1 for r in results if r["check_result"] == "PASS")
        fail_count = sum(1 for r in results if r["check_result"] == "FAIL")
        warn_count = sum(1 for r in results if r["check_result"] == "WARNING")

        log_activity(
            action_type="QA_RUN",
            entity_type="QUALITY_CHECK",
            entity_id=project_id,
            description=f"QA Audit Run: {pass_count} Pass, {warn_count} Warning, {fail_count} Fail",
            conn=conn,
        )

# Rule 1: Required Fields
def _check_required_fields(project_id: Optional[int], db_path: Optional[Union[str, Path]]) -> List[Dict[str, Any]]:
    findings = []
    sql = "SELECT project_id, project_code, project_name, project_type, start_date, deadline FROM projects"
    if project_id:
        sql += f" WHERE project_id = {project_id}"
    projects = fetch_all(sql, db_path=db_path)
    for p in projects:
        missing = []
        if not p.get("project_code") or not str(p["project_code"]).strip():
            missing.append("Project Code")
        if not p.get("project_name") or not str(p["project_name"]).strip():
            missing.append("Project Name")
        if not p.get("project_type") or not str(p["project_type"]).strip():
            missing.append("Project Type")
        if not p.get("start_date"):
            missing.append("Start Date")
        if not p.get("deadline"):
            missing.append("Deadline")
        if missing:
            findings.append({
                "check_name": "Required Fields",
                "entity_type": "PROJECT",
                "entity_id": p["project_id"],
                "project_id": p["project_id"],
                "check_result": "FAIL",
                "error_message": f"Project {p.get('project_code', p['project_id'])} is missing: {', '.join(missing)}",
            })

    r_sql = "SELECT requirement_id, project_id, requirement_code, description FROM requirements"
    if project_id:
        r_sql += f" WHERE project_id = {project_id}"
    reqs = fetch_all(r_sql, db_path=db_path)
    for r in reqs:
        missing = []
        if not r.get("requirement_code") or not str(r["requirement_code"]).strip():
            missing.append("Requirement Code")
        if not r.get("description") or not str(r["description"]).strip():
            missing.append("Description")
        if missing:
            findings.append({
                "check_name": "Required Fields",
                "entity_type": "REQUIREMENT",
                "entity_id": r["requirement_id"],
                "project_id": r["project_id"],
                "check_result": "FAIL",
                "error_message": f"Requirement {r.get('requirement_code', r['requirement_id'])} is missing: {', '.join(missing)}",
            })

    if not findings:
        findings.append({
            "check_name": "Required Fields",
            "entity_type": "SYSTEM",
            "entity_id": None,
            "project_id": project_id,
            "check_result": "PASS",
            "error_message": "All required entity fields are populated.",
        })
    return findings


# Rule 2: Duplicate Codes
def _check_duplicate_codes(project_id: Optional[int], db_path: Optional[Union[str, Path]]) -> List[Dict[str, Any]]:
    findings = []
    tables = [
        ("projects", "project_code", "PROJECT", "project_id"),
        ("requirements", "requirement_code", "REQUIREMENT", "project_id"),
        ("tasks", "task_code", "TASK", "project_id"),
        ("deliverables", "deliverable_code", "DELIVERABLE", "project_id"),
        ("issues", "issue_code", "ISSUE", "project_id"),
    ]
    for table, col, entity_type, prj_col in tables:
        sql = f"SELECT {col}, COUNT(*) as cnt, {prj_col} FROM {table} GROUP BY {col} HAVING cnt > 1"
        rows = fetch_all(sql, db_path=db_path)
        for row in rows:
            findings.append({
                "check_name": "Duplicate Codes",
                "entity_type": entity_type,
                "entity_id": None,
                "project_id": row.get(prj_col),
                "check_result": "FAIL",
                "error_message": f"Duplicate code detected in {table}: '{row[col]}' occurs {row['cnt']} times.",
            })

    if not findings:
        findings.append({
            "check_name": "Duplicate Codes",
            "entity_type": "SYSTEM",
            "entity_id": None,
            "project_id": project_id,
            "check_result": "PASS",
            "error_message": "All entity codes are strictly unique.",
        })
    return findings


# Rule 3: Invalid Project References
def _check_invalid_project_references(project_id: Optional[int], db_path: Optional[Union[str, Path]]) -> List[Dict[str, Any]]:
    findings = []
    child_tables = [
        ("requirements", "requirement_id", "requirement_code", "REQUIREMENT"),
        ("tasks", "task_id", "task_code", "TASK"),
        ("deliverables", "deliverable_id", "deliverable_code", "DELIVERABLE"),
        ("issues", "issue_id", "issue_code", "ISSUE"),
    ]
    for table, id_col, code_col, entity_type in child_tables:
        sql = f"""
            SELECT c.{id_col}, c.{code_col}, c.project_id
            FROM {table} c
            LEFT JOIN projects p ON c.project_id = p.project_id
            WHERE p.project_id IS NULL
        """
        rows = fetch_all(sql, db_path=db_path)
        for r in rows:
            findings.append({
                "check_name": "Invalid Project References",
                "entity_type": entity_type,
                "entity_id": r[id_col],
                "project_id": r["project_id"],
                "check_result": "FAIL",
                "error_message": f"{entity_type} '{r[code_col]}' references non-existent project_id {r['project_id']}.",
            })

    if not findings:
        findings.append({
            "check_name": "Invalid Project References",
            "entity_type": "SYSTEM",
            "entity_id": None,
            "project_id": project_id,
            "check_result": "PASS",
            "error_message": "All foreign key references to projects are valid.",
        })
    return findings

# Rule 4: Invalid Dates
def _check_invalid_dates(project_id: Optional[int], db_path: Optional[Union[str, Path]]) -> List[Dict[str, Any]]:
    findings = []
    sql = "SELECT project_id, project_code, start_date, deadline FROM projects"
    if project_id:
        sql += f" WHERE project_id = {project_id}"
    projects = fetch_all(sql, db_path=db_path)
    for p in projects:
        sd = parse_date(p.get("start_date"))
        dd = parse_date(p.get("deadline"))
        if sd and dd and dd < sd:
            findings.append({
                "check_name": "Invalid Dates",
                "entity_type": "PROJECT",
                "entity_id": p["project_id"],
                "project_id": p["project_id"],
                "check_result": "FAIL",
                "error_message": f"Project {p['project_code']} deadline ({p['deadline']}) is before start date ({p['start_date']}).",
            })

    t_sql = "SELECT task_id, project_id, task_code, start_date, due_date FROM tasks WHERE start_date IS NOT NULL AND due_date IS NOT NULL"
    if project_id:
        t_sql += f" AND project_id = {project_id}"
    tasks = fetch_all(t_sql, db_path=db_path)
    for t in tasks:
        sd = parse_date(t.get("start_date"))
        dd = parse_date(t.get("due_date"))
        if sd and dd and dd < sd:
            findings.append({
                "check_name": "Invalid Dates",
                "entity_type": "TASK",
                "entity_id": t["task_id"],
                "project_id": t["project_id"],
                "check_result": "FAIL",
                "error_message": f"Task {t['task_code']} due date ({t['due_date']}) is before start date ({t['start_date']}).",
            })

    d_sql = "SELECT deliverable_id, project_id, deliverable_code, planned_date, submission_date FROM deliverables WHERE planned_date IS NOT NULL AND submission_date IS NOT NULL"
    if project_id:
        d_sql += f" AND project_id = {project_id}"
    delivs = fetch_all(d_sql, db_path=db_path)
    for d in delivs:
        pd = parse_date(d.get("planned_date"))
        sd = parse_date(d.get("submission_date"))
        if pd and sd and sd > pd:
            findings.append({
                "check_name": "Invalid Dates",
                "entity_type": "DELIVERABLE",
                "entity_id": d["deliverable_id"],
                "project_id": d["project_id"],
                "check_result": "WARNING",
                "error_message": f"Deliverable {d['deliverable_code']} was submitted on {d['submission_date']}, after planned date ({d['planned_date']}).",
            })

    if not findings:
        findings.append({
            "check_name": "Invalid Dates",
            "entity_type": "SYSTEM",
            "entity_id": None,
            "project_id": project_id,
            "check_result": "PASS",
            "error_message": "All entity date sequences are logically consistent.",
        })
    return findings


# Rule 5: Missing Reviewer for Submitted Deliverables
def _check_missing_reviewer_submitted_deliverables(project_id: Optional[int], db_path: Optional[Union[str, Path]]) -> List[Dict[str, Any]]:
    findings = []
    sql = "SELECT deliverable_id, project_id, deliverable_code, review_status, reviewer FROM deliverables WHERE review_status IN ('Submitted', 'Under Review', 'Approved')"
    if project_id:
        sql += f" AND project_id = {project_id}"
    deliverables = fetch_all(sql, db_path=db_path)
    for d in deliverables:
        if not d.get("reviewer") or not str(d["reviewer"]).strip():
            findings.append({
                "check_name": "Missing Reviewer for Submitted Deliverables",
                "entity_type": "DELIVERABLE",
                "entity_id": d["deliverable_id"],
                "project_id": d["project_id"],
                "check_result": "FAIL",
                "error_message": f"Deliverable {d['deliverable_code']} is '{d['review_status']}' but has no designated reviewer.",
            })

    if not findings:
        findings.append({
            "check_name": "Missing Reviewer for Submitted Deliverables",
            "entity_type": "SYSTEM",
            "entity_id": None,
            "project_id": project_id,
            "check_result": "PASS",
            "error_message": "All submitted, review, and approved deliverables have designated reviewers.",
        })
    return findings


# Rule 6: Incomplete Deliverable Information
def _check_incomplete_deliverable_info(project_id: Optional[int], db_path: Optional[Union[str, Path]]) -> List[Dict[str, Any]]:
    findings = []
    sql = "SELECT deliverable_id, project_id, deliverable_code, version, file_name, deliverable_type, review_status FROM deliverables"
    if project_id:
        sql += f" WHERE project_id = {project_id}"
    deliverables = fetch_all(sql, db_path=db_path)
    for d in deliverables:
        issues = []
        if not d.get("version") or not str(d["version"]).strip():
            issues.append("missing version")
        if not d.get("file_name") or not str(d["file_name"]).strip():
            if d.get("review_status") != "Draft":
                issues.append("missing file attachment name")
        if not d.get("deliverable_type") or not str(d["deliverable_type"]).strip():
            issues.append("missing deliverable type")
        if issues:
            findings.append({
                "check_name": "Incomplete Deliverable Information",
                "entity_type": "DELIVERABLE",
                "entity_id": d["deliverable_id"],
                "project_id": d["project_id"],
                "check_result": "WARNING",
                "error_message": f"Deliverable {d['deliverable_code']} has incomplete metadata: {', '.join(issues)}.",
            })

    if not findings:
        findings.append({
            "check_name": "Incomplete Deliverable Information",
            "entity_type": "SYSTEM",
            "entity_id": None,
            "project_id": project_id,
            "check_result": "PASS",
            "error_message": "All deliverables have complete specifications and type metadata.",
        })
    return findings


# Rule 7: Invalid Task Progress
def _check_invalid_task_progress(project_id: Optional[int], db_path: Optional[Union[str, Path]]) -> List[Dict[str, Any]]:
    findings = []
    sql = "SELECT task_id, project_id, task_code, status, progress_percentage FROM tasks"
    if project_id:
        sql += f" WHERE project_id = {project_id}"
    tasks = fetch_all(sql, db_path=db_path)
    for t in tasks:
        p = t.get("progress_percentage", 0)
        s = t.get("status", "")
        if p < 0 or p > 100:
            findings.append({
                "check_name": "Invalid Task Progress",
                "entity_type": "TASK",
                "entity_id": t["task_id"],
                "project_id": t["project_id"],
                "check_result": "FAIL",
                "error_message": f"Task {t['task_code']} has out-of-range progress {p}%.",
            })
        elif s == "Completed" and p < 100:
            findings.append({
                "check_name": "Invalid Task Progress",
                "entity_type": "TASK",
                "entity_id": t["task_id"],
                "project_id": t["project_id"],
                "check_result": "FAIL",
                "error_message": f"Task {t['task_code']} is marked 'Completed' but progress is only {p}%.",
            })
        elif s != "Completed" and p == 100:
            findings.append({
                "check_name": "Invalid Task Progress",
                "entity_type": "TASK",
                "entity_id": t["task_id"],
                "project_id": t["project_id"],
                "check_result": "WARNING",
                "error_message": f"Task {t['task_code']} has progress 100% but status is '{s}'.",
            })
        elif s == "Not Started" and p > 0:
            findings.append({
                "check_name": "Invalid Task Progress",
                "entity_type": "TASK",
                "entity_id": t["task_id"],
                "project_id": t["project_id"],
                "check_result": "WARNING",
                "error_message": f"Task {t['task_code']} is 'Not Started' but has progress {p}%.",
            })

    if not findings:
        findings.append({
            "check_name": "Invalid Task Progress",
            "entity_type": "SYSTEM",
            "entity_id": None,
            "project_id": project_id,
            "check_result": "PASS",
            "error_message": "All task completion percentages are valid and aligned with status.",
        })
    return findings

# Rule 8: Overdue Tasks
def _check_overdue_tasks(project_id: Optional[int], db_path: Optional[Union[str, Path]]) -> List[Dict[str, Any]]:
    findings = []
    sql = "SELECT task_id, project_id, task_code, status, due_date, assigned_to FROM tasks WHERE status != 'Completed' AND due_date IS NOT NULL"
    if project_id:
        sql += f" AND project_id = {project_id}"
    tasks = fetch_all(sql, db_path=db_path)
    today = date.today()
    for t in tasks:
        dd = parse_date(t.get("due_date"))
        if dd and dd < today:
            days_late = (today - dd).days
            findings.append({
                "check_name": "Overdue Tasks",
                "entity_type": "TASK",
                "entity_id": t["task_id"],
                "project_id": t["project_id"],
                "check_result": "WARNING",
                "error_message": f"Task {t['task_code']} ({t.get('assigned_to') or 'Unassigned'}) is {days_late} day(s) overdue (Due: {t['due_date']}).",
            })

    if not findings:
        findings.append({
            "check_name": "Overdue Tasks",
            "entity_type": "SYSTEM",
            "entity_id": None,
            "project_id": project_id,
            "check_result": "PASS",
            "error_message": "No open tasks are overdue.",
        })
    return findings


# Rule 9: Open Requirements Requiring Clarification
def _check_open_requirements_clarification(project_id: Optional[int], db_path: Optional[Union[str, Path]]) -> List[Dict[str, Any]]:
    findings = []
    sql = """
        SELECT requirement_id, project_id, requirement_code, status, clarification_question, owner
        FROM requirements
        WHERE status = 'Clarification Required'
           OR (clarification_question IS NOT NULL AND TRIM(clarification_question) != '' AND status != 'Closed')
    """
    if project_id:
        sql += f" AND project_id = {project_id}"
    reqs = fetch_all(sql, db_path=db_path)
    for r in reqs:
        findings.append({
            "check_name": "Open Requirements Requiring Clarification",
            "entity_type": "REQUIREMENT",
            "entity_id": r["requirement_id"],
            "project_id": r["project_id"],
            "check_result": "WARNING",
            "error_message": f"Requirement {r['requirement_code']} requires clarification (Owner: {r.get('owner') or 'Unassigned'}). Question: {r.get('clarification_question') or 'Review needed'}",
        })

    if not findings:
        findings.append({
            "check_name": "Open Requirements Requiring Clarification",
            "entity_type": "SYSTEM",
            "entity_id": None,
            "project_id": project_id,
            "check_result": "PASS",
            "error_message": "All engineering requirements are clear and finalized.",
        })
    return findings


# Rule 10: Invalid Status Values
def _check_invalid_status_values(project_id: Optional[int], db_path: Optional[Union[str, Path]]) -> List[Dict[str, Any]]:
    findings = []
    sql = "SELECT project_id, project_code, status, priority FROM projects"
    if project_id:
        sql += f" WHERE project_id = {project_id}"
    for p in fetch_all(sql, db_path=db_path):
        if p.get("status") not in PROJECT_STATUSES:
            findings.append({
                "check_name": "Invalid Status Values",
                "entity_type": "PROJECT",
                "entity_id": p["project_id"],
                "project_id": p["project_id"],
                "check_result": "FAIL",
                "error_message": f"Project {p['project_code']} has invalid status '{p.get('status')}'.",
            })
        if p.get("priority") not in PROJECT_PRIORITIES:
            findings.append({
                "check_name": "Invalid Status Values",
                "entity_type": "PROJECT",
                "entity_id": p["project_id"],
                "project_id": p["project_id"],
                "check_result": "FAIL",
                "error_message": f"Project {p['project_code']} has invalid priority '{p.get('priority')}'.",
            })

    r_sql = "SELECT requirement_id, project_id, requirement_code, status, priority FROM requirements"
    if project_id:
        r_sql += f" WHERE project_id = {project_id}"
    for r in fetch_all(r_sql, db_path=db_path):
        if r.get("status") not in REQUIREMENT_STATUSES:
            findings.append({
                "check_name": "Invalid Status Values",
                "entity_type": "REQUIREMENT",
                "entity_id": r["requirement_id"],
                "project_id": r["project_id"],
                "check_result": "FAIL",
                "error_message": f"Requirement {r['requirement_code']} has invalid status '{r.get('status')}'.",
            })
        if r.get("priority") not in REQUIREMENT_PRIORITIES:
            findings.append({
                "check_name": "Invalid Status Values",
                "entity_type": "REQUIREMENT",
                "entity_id": r["requirement_id"],
                "project_id": r["project_id"],
                "check_result": "FAIL",
                "error_message": f"Requirement {r['requirement_code']} has invalid priority '{r.get('priority')}'.",
            })

    t_sql = "SELECT task_id, project_id, task_code, status, priority FROM tasks"
    if project_id:
        t_sql += f" WHERE project_id = {project_id}"
    for t in fetch_all(t_sql, db_path=db_path):
        if t.get("status") not in TASK_STATUSES:
            findings.append({
                "check_name": "Invalid Status Values",
                "entity_type": "TASK",
                "entity_id": t["task_id"],
                "project_id": t["project_id"],
                "check_result": "FAIL",
                "error_message": f"Task {t['task_code']} has invalid status '{t.get('status')}'.",
            })
        if t.get("priority") not in TASK_PRIORITIES:
            findings.append({
                "check_name": "Invalid Status Values",
                "entity_type": "TASK",
                "entity_id": t["task_id"],
                "project_id": t["project_id"],
                "check_result": "FAIL",
                "error_message": f"Task {t['task_code']} has invalid priority '{t.get('priority')}'.",
            })

    d_sql = "SELECT deliverable_id, project_id, deliverable_code, review_status FROM deliverables"
    if project_id:
        d_sql += f" WHERE project_id = {project_id}"
    for d in fetch_all(d_sql, db_path=db_path):
        if d.get("review_status") not in DELIVERABLE_REVIEW_STATUSES:
            findings.append({
                "check_name": "Invalid Status Values",
                "entity_type": "DELIVERABLE",
                "entity_id": d["deliverable_id"],
                "project_id": d["project_id"],
                "check_result": "FAIL",
                "error_message": f"Deliverable {d['deliverable_code']} has invalid review status '{d.get('review_status')}'.",
            })

    i_sql = "SELECT issue_id, project_id, issue_code, status, severity FROM issues"
    if project_id:
        i_sql += f" WHERE project_id = {project_id}"
    for i in fetch_all(i_sql, db_path=db_path):
        if i.get("status") not in ISSUE_STATUSES:
            findings.append({
                "check_name": "Invalid Status Values",
                "entity_type": "ISSUE",
                "entity_id": i["issue_id"],
                "project_id": i["project_id"],
                "check_result": "FAIL",
                "error_message": f"Issue {i['issue_code']} has invalid status '{i.get('status')}'.",
            })
        if i.get("severity") not in ISSUE_SEVERITIES:
            findings.append({
                "check_name": "Invalid Status Values",
                "entity_type": "ISSUE",
                "entity_id": i["issue_id"],
                "project_id": i["project_id"],
                "check_result": "FAIL",
                "error_message": f"Issue {i['issue_code']} has invalid severity '{i.get('severity')}'.",
            })

    if not findings:
        findings.append({
            "check_name": "Invalid Status Values",
            "entity_type": "SYSTEM",
            "entity_id": None,
            "project_id": project_id,
            "check_result": "PASS",
            "error_message": "All statuses and priority classifications conform to standard taxonomy.",
        })
    return findings


# Rule 11: Missing Task Owners
def _check_missing_task_owners(project_id: Optional[int], db_path: Optional[Union[str, Path]]) -> List[Dict[str, Any]]:
    findings = []
    sql = "SELECT task_id, project_id, task_code, status, assigned_to FROM tasks WHERE status IN ('In Progress', 'Under Review')"
    if project_id:
        sql += f" AND project_id = {project_id}"
    tasks = fetch_all(sql, db_path=db_path)
    for t in tasks:
        if not t.get("assigned_to") or not str(t["assigned_to"]).strip():
            findings.append({
                "check_name": "Missing Task Owners",
                "entity_type": "TASK",
                "entity_id": t["task_id"],
                "project_id": t["project_id"],
                "check_result": "WARNING",
                "error_message": f"Active task {t['task_code']} (Status: {t['status']}) has no assigned owner.",
            })

    if not findings:
        findings.append({
            "check_name": "Missing Task Owners",
            "entity_type": "SYSTEM",
            "entity_id": None,
            "project_id": project_id,
            "check_result": "PASS",
            "error_message": "All active and in-review tasks have assigned engineers.",
        })
    return findings


# Rule 12: Missing Acceptance Criteria
def _check_missing_acceptance_criteria(project_id: Optional[int], db_path: Optional[Union[str, Path]]) -> List[Dict[str, Any]]:
    findings = []
    sql = "SELECT requirement_id, project_id, requirement_code, status, acceptance_criteria FROM requirements WHERE status IN ('Approved', 'Implemented')"
    if project_id:
        sql += f" AND project_id = {project_id}"
    reqs = fetch_all(sql, db_path=db_path)
    for r in reqs:
        if not r.get("acceptance_criteria") or not str(r["acceptance_criteria"]).strip():
            findings.append({
                "check_name": "Missing Acceptance Criteria",
                "entity_type": "REQUIREMENT",
                "entity_id": r["requirement_id"],
                "project_id": r["project_id"],
                "check_result": "WARNING",
                "error_message": f"Requirement {r['requirement_code']} is '{r['status']}' but lacks documented acceptance criteria.",
            })

    if not findings:
        findings.append({
            "check_name": "Missing Acceptance Criteria",
            "entity_type": "SYSTEM",
            "entity_id": None,
            "project_id": project_id,
            "check_result": "PASS",
            "error_message": "All approved/implemented requirements have acceptance criteria.",
        })
    return findings


def get_latest_quality_checks(
    project_id: Optional[int] = None,
    result_filter: Optional[str] = None,
    entity_type_filter: Optional[str] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> List[Dict[str, Any]]:
    """Retrieves saved quality check results with flexible filters."""
    sql = "SELECT * FROM quality_checks WHERE 1=1"
    params: List[Any] = []

    if project_id:
        sql += " AND (project_id = ? OR project_id IS NULL)"
        params.append(project_id)

    if result_filter and result_filter != "All":
        sql += " AND check_result = ?"
        params.append(result_filter)

    if entity_type_filter and entity_type_filter != "All":
        sql += " AND entity_type = ?"
        params.append(entity_type_filter)

    sql += " ORDER BY check_id ASC"
    return fetch_all(sql, params, db_path=db_path)
