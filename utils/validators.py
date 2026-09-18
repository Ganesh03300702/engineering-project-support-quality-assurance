"""
Input and Business Rule Validation Utilities
Provides robust validation functions for all engineering entities before persistence.
"""

from datetime import datetime, date
import re
from typing import Optional, Tuple, Any
from .constants import (
    PROJECT_STATUSES,
    PROJECT_PRIORITIES,
    REQUIREMENT_STATUSES,
    REQUIREMENT_PRIORITIES,
    TASK_STATUSES,
    TASK_PRIORITIES,
    DELIVERABLE_REVIEW_STATUSES,
    ISSUE_SEVERITIES,
    ISSUE_STATUSES,
)


def validate_required_string(val: Any, field_name: str, min_len: int = 1, max_len: int = 255) -> Tuple[bool, str]:
    """Validates that a string field is present, not just whitespace, and within length limits."""
    if val is None:
        return False, f"{field_name} is required and cannot be empty."
    s = str(val).strip()
    if len(s) == 0:
        return False, f"{field_name} is required and cannot be empty."
    if len(s) < min_len:
        return False, f"{field_name} must be at least {min_len} character(s)."
    if len(s) > max_len:
        return False, f"{field_name} must not exceed {max_len} characters."
    return True, ""


def validate_code(code: str, field_name: str = "Code") -> Tuple[bool, str]:
    """Validates code formatting (e.g. PRJ-001, REQ-001, TSK-001, DEL-001, ISS-001)."""
    ok, msg = validate_required_string(code, field_name, min_len=2, max_len=30)
    if not ok:
        return False, msg
    clean_code = str(code).strip()
    if not re.match(r"^[A-Za-z0-9_\-]+$", clean_code):
        return False, f"{field_name} must only contain letters, numbers, hyphens, or underscores."
    return True, ""


def parse_date(d: Any) -> Optional[date]:
    """Parses date from string (YYYY-MM-DD) or date/datetime object."""
    if d is None:
        return None
    if isinstance(d, datetime):
        return d.date()
    if isinstance(d, date):
        return d
    try:
        s = str(d).strip()
        if not s:
            return None
        return datetime.strptime(s, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def validate_date_order(
    start: Any,
    end: Any,
    start_label: str = "Start Date",
    end_label: str = "Deadline",
) -> Tuple[bool, str]:
    """Validates that end date is on or after start date."""
    d_start = parse_date(start)
    d_end = parse_date(end)
    if not d_start:
        return False, f"{start_label} must be a valid date in YYYY-MM-DD format."
    if not d_end:
        return False, f"{end_label} must be a valid date in YYYY-MM-DD format."
    if d_end < d_start:
        return False, f"{end_label} ({d_end}) cannot be before {start_label} ({d_start})."
    return True, ""


def validate_progress(progress: Any) -> Tuple[bool, str]:
    """Validates that progress percentage is an integer between 0 and 100."""
    try:
        val = int(progress)
        if val < 0 or val > 100:
            return False, "Progress percentage must be between 0 and 100."
        return True, ""
    except (ValueError, TypeError):
        return False, "Progress percentage must be a valid integer between 0 and 100."


def validate_project_data(data: dict) -> Tuple[bool, list[str]]:
    """Comprehensive validation for project creation and updates."""
    errors = []
    
    ok, msg = validate_code(data.get("project_code", ""), "Project Code")
    if not ok:
        errors.append(msg)
        
    ok, msg = validate_required_string(data.get("project_name", ""), "Project Name", min_len=3, max_len=150)
    if not ok:
        errors.append(msg)
        
    ok, msg = validate_required_string(data.get("project_type", ""), "Project Type", min_len=2, max_len=100)
    if not ok:
        errors.append(msg)

    start_date = data.get("start_date")
    deadline = data.get("deadline")
    if not start_date or not deadline:
        errors.append("Both Start Date and Deadline are required.")
    else:
        ok, msg = validate_date_order(start_date, deadline, "Start Date", "Deadline")
        if not ok:
            errors.append(msg)

    status = data.get("status", "Planned")
    if status not in PROJECT_STATUSES:
        errors.append(f"Invalid project status '{status}'. Must be one of: {', '.join(PROJECT_STATUSES)}.")

    priority = data.get("priority", "Medium")
    if priority not in PROJECT_PRIORITIES:
        errors.append(f"Invalid project priority '{priority}'. Must be one of: {', '.join(PROJECT_PRIORITIES)}.")

    return len(errors) == 0, errors


def validate_requirement_data(data: dict) -> Tuple[bool, list[str]]:
    """Comprehensive validation for requirement creation and updates."""
    errors = []

    ok, msg = validate_code(data.get("requirement_code", ""), "Requirement Code")
    if not ok:
        errors.append(msg)

    if not data.get("project_id"):
        errors.append("Project reference is required.")

    ok, msg = validate_required_string(data.get("description", ""), "Description", min_len=5, max_len=1000)
    if not ok:
        errors.append(msg)

    status = data.get("status", "Open")
    if status not in REQUIREMENT_STATUSES:
        errors.append(f"Invalid requirement status '{status}'. Must be one of: {', '.join(REQUIREMENT_STATUSES)}.")

    priority = data.get("priority", "Medium")
    if priority not in REQUIREMENT_PRIORITIES:
        errors.append(f"Invalid requirement priority '{priority}'. Must be one of: {', '.join(REQUIREMENT_PRIORITIES)}.")

    due_date = data.get("due_date")
    if due_date and not parse_date(due_date):
        errors.append("Due date must be in valid YYYY-MM-DD format.")

    return len(errors) == 0, errors


def validate_task_data(data: dict) -> Tuple[bool, list[str]]:
    """Comprehensive validation for task creation and updates."""
    errors = []

    ok, msg = validate_code(data.get("task_code", ""), "Task Code")
    if not ok:
        errors.append(msg)

    if not data.get("project_id"):
        errors.append("Project reference is required.")

    ok, msg = validate_required_string(data.get("task_description", ""), "Task Description", min_len=5, max_len=1000)
    if not ok:
        errors.append(msg)

    status = data.get("status", "Not Started")
    if status not in TASK_STATUSES:
        errors.append(f"Invalid task status '{status}'. Must be one of: {', '.join(TASK_STATUSES)}.")

    priority = data.get("priority", "Medium")
    if priority not in TASK_PRIORITIES:
        errors.append(f"Invalid task priority '{priority}'. Must be one of: {', '.join(TASK_PRIORITIES)}.")

    progress = data.get("progress_percentage", 0)
    ok, msg = validate_progress(progress)
    if not ok:
        errors.append(msg)

    start_date = data.get("start_date")
    due_date = data.get("due_date")
    if start_date and due_date:
        ok, msg = validate_date_order(start_date, due_date, "Task Start Date", "Task Due Date")
        if not ok:
            errors.append(msg)
    elif due_date and not parse_date(due_date):
        errors.append("Task due date must be in valid YYYY-MM-DD format.")

    return len(errors) == 0, errors


def validate_deliverable_data(data: dict) -> Tuple[bool, list[str]]:
    """Comprehensive validation for deliverable creation and updates."""
    errors = []

    ok, msg = validate_code(data.get("deliverable_code", ""), "Deliverable Code")
    if not ok:
        errors.append(msg)

    if not data.get("project_id"):
        errors.append("Project reference is required.")

    ok, msg = validate_required_string(data.get("deliverable_name", ""), "Deliverable Name", min_len=3, max_len=200)
    if not ok:
        errors.append(msg)

    version = data.get("version", "")
    ok, msg = validate_required_string(version, "Version", min_len=1, max_len=20)
    if not ok:
        errors.append(msg)

    review_status = data.get("review_status", "Draft")
    if review_status not in DELIVERABLE_REVIEW_STATUSES:
        errors.append(f"Invalid review status '{review_status}'. Must be one of: {', '.join(DELIVERABLE_REVIEW_STATUSES)}.")

    planned_date = data.get("planned_date")
    submission_date = data.get("submission_date")
    if planned_date and not parse_date(planned_date):
        errors.append("Planned date must be in valid YYYY-MM-DD format.")
    if submission_date and not parse_date(submission_date):
        errors.append("Submission date must be in valid YYYY-MM-DD format.")

    return len(errors) == 0, errors


def validate_issue_data(data: dict) -> Tuple[bool, list[str]]:
    """Comprehensive validation for issue creation and updates."""
    errors = []

    ok, msg = validate_code(data.get("issue_code", ""), "Issue Code")
    if not ok:
        errors.append(msg)

    if not data.get("project_id"):
        errors.append("Project reference is required.")

    ok, msg = validate_required_string(data.get("description", ""), "Description", min_len=5, max_len=1000)
    if not ok:
        errors.append(msg)

    severity = data.get("severity", "Medium")
    if severity not in ISSUE_SEVERITIES:
        errors.append(f"Invalid severity '{severity}'. Must be one of: {', '.join(ISSUE_SEVERITIES)}.")

    status = data.get("status", "Open")
    if status not in ISSUE_STATUSES:
        errors.append(f"Invalid status '{status}'. Must be one of: {', '.join(ISSUE_STATUSES)}.")

    target_date = data.get("target_date")
    if target_date and not parse_date(target_date):
        errors.append("Target date must be in valid YYYY-MM-DD format.")

    return len(errors) == 0, errors
