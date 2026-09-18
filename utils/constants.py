"""
Application Constants and Enumerations
Defines standardized statuses, priorities, types, and labels across all modules.
"""

# Projects
PROJECT_STATUSES = ["Planned", "Active", "On Hold", "Completed", "Cancelled"]
PROJECT_PRIORITIES = ["Low", "Medium", "High", "Critical"]
PROJECT_TYPES = [
    "Equipment Inspection",
    "Documentation Standardization",
    "Component Quality Review",
    "Process Optimization",
    "Safety Compliance",
    "Infrastructure Support",
    "Tooling & Calibration",
]

# Requirements
REQUIREMENT_STATUSES = ["Open", "Clarification Required", "Approved", "Implemented", "Closed"]
REQUIREMENT_PRIORITIES = ["Low", "Medium", "High", "Critical"]

# Tasks
TASK_STATUSES = ["Not Started", "In Progress", "Under Review", "Completed", "Blocked"]
TASK_PRIORITIES = ["Low", "Medium", "High", "Critical"]

# Deliverables
DELIVERABLE_REVIEW_STATUSES = ["Draft", "Submitted", "Under Review", "Approved", "Rework Required"]
DELIVERABLE_TYPES = [
    "Inspection Checklist",
    "SOP Manual",
    "Audit Report",
    "CAD Drawing",
    "Specification Sheet",
    "Test Protocol",
    "Training Guide",
    "Compliance Certificate",
]

# Issues
ISSUE_SEVERITIES = ["Low", "Medium", "High", "Critical"]
ISSUE_STATUSES = ["Open", "In Progress", "Resolved", "Closed"]

# Quality Checks
QA_RESULTS = ["PASS", "FAIL", "WARNING"]

# Entity and Action Types for Activity Logging
ENTITY_TYPES = ["PROJECT", "REQUIREMENT", "TASK", "DELIVERABLE", "ISSUE", "QUALITY_CHECK", "SYSTEM"]
ACTION_TYPES = ["CREATE", "UPDATE", "DELETE", "STATUS_CHANGE", "QA_RUN", "SEED_DATA", "RESET_DB"]

# Status Colors for Streamlit and Charts
STATUS_COLORS = {
    # Project & Task Statuses
    "Planned": "#6c757d",
    "Active": "#0d6efd",
    "In Progress": "#0d6efd",
    "On Hold": "#fd7e14",
    "Blocked": "#dc3545",
    "Under Review": "#6f42c1",
    "Completed": "#198754",
    "Cancelled": "#6c757d",
    # Requirement Statuses
    "Open": "#0dcaf0",
    "Clarification Required": "#ffc107",
    "Approved": "#198754",
    "Implemented": "#20c997",
    "Closed": "#6c757d",
    # Deliverable Statuses
    "Draft": "#6c757d",
    "Submitted": "#0d6efd",
    "Rework Required": "#dc3545",
    # Issue Statuses
    "Resolved": "#198754",
    # QA
    "PASS": "#198754",
    "FAIL": "#dc3545",
    "WARNING": "#ffc107",
    # Priorities
    "Low": "#198754",
    "Medium": "#0dcaf0",
    "High": "#fd7e14",
    "Critical": "#dc3545",
}
