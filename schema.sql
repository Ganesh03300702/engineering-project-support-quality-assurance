-- Engineering Project Support & Quality Assurance Management System
-- SQLite Database Schema

PRAGMA foreign_keys = ON;

-- 1. Projects Table
CREATE TABLE IF NOT EXISTS projects (
    project_id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_code TEXT UNIQUE NOT NULL,
    project_name TEXT NOT NULL,
    project_type TEXT NOT NULL,
    description TEXT,
    stakeholder TEXT,
    team_lead TEXT,
    start_date TEXT NOT NULL,
    deadline TEXT NOT NULL,
    priority TEXT NOT NULL DEFAULT 'Medium',
    status TEXT NOT NULL DEFAULT 'Planned',
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE INDEX IF NOT EXISTS idx_projects_code ON projects(project_code);
CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status);
CREATE INDEX IF NOT EXISTS idx_projects_deadline ON projects(deadline);

-- 2. Requirements Table
CREATE TABLE IF NOT EXISTS requirements (
    requirement_id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    requirement_code TEXT UNIQUE NOT NULL,
    description TEXT NOT NULL,
    acceptance_criteria TEXT,
    priority TEXT NOT NULL DEFAULT 'Medium',
    status TEXT NOT NULL DEFAULT 'Open',
    clarification_question TEXT,
    owner TEXT,
    due_date TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE INDEX IF NOT EXISTS idx_requirements_project_id ON requirements(project_id);
CREATE INDEX IF NOT EXISTS idx_requirements_code ON requirements(requirement_code);
CREATE INDEX IF NOT EXISTS idx_requirements_status ON requirements(status);
CREATE INDEX IF NOT EXISTS idx_requirements_due_date ON requirements(due_date);

-- 3. Tasks Table
CREATE TABLE IF NOT EXISTS tasks (
    task_id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    requirement_id INTEGER REFERENCES requirements(requirement_id) ON DELETE SET NULL,
    task_code TEXT UNIQUE NOT NULL,
    task_description TEXT NOT NULL,
    assigned_to TEXT,
    priority TEXT NOT NULL DEFAULT 'Medium',
    start_date TEXT,
    due_date TEXT,
    status TEXT NOT NULL DEFAULT 'Not Started',
    progress_percentage INTEGER NOT NULL DEFAULT 0 CHECK(progress_percentage >= 0 AND progress_percentage <= 100),
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE INDEX IF NOT EXISTS idx_tasks_project_id ON tasks(project_id);
CREATE INDEX IF NOT EXISTS idx_tasks_requirement_id ON tasks(requirement_id);
CREATE INDEX IF NOT EXISTS idx_tasks_code ON tasks(task_code);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_due_date ON tasks(due_date);

-- 4. Deliverables Table
CREATE TABLE IF NOT EXISTS deliverables (
    deliverable_id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    deliverable_code TEXT UNIQUE NOT NULL,
    deliverable_name TEXT NOT NULL,
    deliverable_type TEXT,
    version TEXT NOT NULL DEFAULT 'v1.0',
    prepared_by TEXT,
    reviewer TEXT,
    planned_date TEXT,
    submission_date TEXT,
    review_status TEXT NOT NULL DEFAULT 'Draft',
    file_name TEXT,
    comments TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE INDEX IF NOT EXISTS idx_deliverables_project_id ON deliverables(project_id);
CREATE INDEX IF NOT EXISTS idx_deliverables_code ON deliverables(deliverable_code);
CREATE INDEX IF NOT EXISTS idx_deliverables_review_status ON deliverables(review_status);
CREATE INDEX IF NOT EXISTS idx_deliverables_planned_date ON deliverables(planned_date);

-- 5. Quality Checks Table
CREATE TABLE IF NOT EXISTS quality_checks (
    check_id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER REFERENCES projects(project_id) ON DELETE CASCADE,
    entity_type TEXT NOT NULL,
    entity_id INTEGER,
    check_name TEXT NOT NULL,
    check_result TEXT NOT NULL,
    error_message TEXT,
    checked_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE INDEX IF NOT EXISTS idx_quality_checks_project_id ON quality_checks(project_id);
CREATE INDEX IF NOT EXISTS idx_quality_checks_result ON quality_checks(check_result);
CREATE INDEX IF NOT EXISTS idx_quality_checks_entity ON quality_checks(entity_type, entity_id);

-- 6. Issues Table
CREATE TABLE IF NOT EXISTS issues (
    issue_id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    issue_code TEXT UNIQUE NOT NULL,
    related_requirement_id INTEGER REFERENCES requirements(requirement_id) ON DELETE SET NULL,
    related_task_id INTEGER REFERENCES tasks(task_id) ON DELETE SET NULL,
    description TEXT NOT NULL,
    severity TEXT NOT NULL DEFAULT 'Medium',
    owner TEXT,
    status TEXT NOT NULL DEFAULT 'Open',
    target_date TEXT,
    resolution_notes TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE INDEX IF NOT EXISTS idx_issues_project_id ON issues(project_id);
CREATE INDEX IF NOT EXISTS idx_issues_code ON issues(issue_code);
CREATE INDEX IF NOT EXISTS idx_issues_status ON issues(status);
CREATE INDEX IF NOT EXISTS idx_issues_target_date ON issues(target_date);

-- 7. Activity Log Table
CREATE TABLE IF NOT EXISTS activity_log (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    action_type TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id INTEGER,
    description TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE INDEX IF NOT EXISTS idx_activity_log_entity ON activity_log(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_activity_log_created_at ON activity_log(created_at);
