"""
Engineering Project Support & Quality Assurance Management System
Main Streamlit Application Dashboard & Workflow Interface.
"""

from datetime import date, datetime
from pathlib import Path
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import config
from config import APP_TITLE, APP_SUBTITLE, APP_VERSION, DEFAULT_DB_PATH, LOG_FILE_PATH, logger
import database
from database import fetch_all, fetch_one, init_db, reset_db
from modules import deliverables, issues, projects, quality_checks, reports, requirements, tasks
from seed_data import seed_database
from utils.constants import (
    DELIVERABLE_REVIEW_STATUSES,
    DELIVERABLE_TYPES,
    ENTITY_TYPES,
    ISSUE_SEVERITIES,
    ISSUE_STATUSES,
    PROJECT_PRIORITIES,
    PROJECT_STATUSES,
    PROJECT_TYPES,
    QA_RESULTS,
    REQUIREMENT_PRIORITIES,
    REQUIREMENT_STATUSES,
    STATUS_COLORS,
    TASK_PRIORITIES,
    TASK_STATUSES,
)
from utils.formatting import (
    format_date_display,
    format_percentage,
    get_badge_html,
    get_priority_badge_html,
    get_qa_badge_html,
)

# -----------------------------------------------------------------------------
# 1. Streamlit Page Configuration & Styling
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Engineering QA & Project Support",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for Engineering System Theme
st.markdown(
    """
    <style>
    .main-header {
        font-size: 1.85rem;
        font-weight: 700;
        color: #1F4E79;
        margin-bottom: 0.1rem;
    }
    .sub-header {
        font-size: 0.95rem;
        color: #5A6A80;
        margin-bottom: 1.2rem;
    }
    .metric-card {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 14px;
        text-align: center;
    }
    .metric-val {
        font-size: 1.8rem;
        font-weight: 700;
        color: #1F4E79;
    }
    .metric-lbl {
        font-size: 0.85rem;
        color: #64748B;
        font-weight: 500;
    }
    .status-badge {
        font-size: 0.82rem;
        padding: 2px 8px;
        border-radius: 4px;
        font-weight: 600;
        color: white;
    }
    .stButton>button {
        border-radius: 6px;
        font-weight: 500;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Auto-initialize database on application startup
try:
    init_db()
except Exception as e:
    st.error(f"Database initialization error: {e}")
    logger.error(f"App startup DB init failed: {e}")

# -----------------------------------------------------------------------------
# 2. Sidebar Navigation & Global Project Filter
# -----------------------------------------------------------------------------
st.sidebar.markdown(f"### ⚙️ {APP_TITLE}")
st.sidebar.caption(f"Version {APP_VERSION} | Internal Engineering Suite")
st.sidebar.markdown("---")

NAV_OPTIONS = [
    "Dashboard",
    "Projects",
    "Requirements",
    "Tasks",
    "Deliverables",
    "Quality Assurance",
    "Issues & Clarifications",
    "Reports",
    "Settings / Data Management",
]

selected_page = st.sidebar.radio(
    "Navigation Menu",
    options=NAV_OPTIONS,
    index=0,
    key="nav_radio",
)

# Global project list for selector
all_prjs = projects.get_all_projects()
project_options = {"All Projects": None}
for p in all_prjs:
    project_options[f"{p['project_code']} — {p['project_name']}"] = p["project_id"]

st.sidebar.markdown("---")
st.sidebar.markdown("**Global Scope Filter**")
selected_project_label = st.sidebar.selectbox(
    "Filter by Project",
    options=list(project_options.keys()),
    index=0,
    key="global_prj_filter",
)
current_project_id = project_options[selected_project_label]

st.sidebar.markdown("---")
st.sidebar.caption("System Status: **Online** | SQLite Connected")


# =============================================================================
# PAGE 1: DASHBOARD
# =============================================================================
if selected_page == "Dashboard":
    st.markdown('<div class="main-header">Engineering Operations Dashboard</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="sub-header">{APP_SUBTITLE} — Active Scope: <b>{selected_project_label}</b></div>',
        unsafe_allow_html=True,
    )

    # Fetch datasets for metrics
    prjs = projects.get_all_projects()
    reqs = requirements.get_requirements(project_id=current_project_id)
    tsks = tasks.get_tasks(project_id=current_project_id)
    delivs = deliverables.get_deliverables(project_id=current_project_id)
    isss = issues.get_issues(project_id=current_project_id)

    total_projects = len(prjs)
    active_projects = sum(1 for p in prjs if p["status"] == "Active")
    total_requirements = len(reqs)
    total_tasks = len(tsks)
    completed_tasks = sum(1 for t in tsks if t["status"] == "Completed")
    overdue_tasks = sum(1 for t in tsks if t.get("is_overdue", False))
    pending_reviews = sum(1 for d in delivs if d["review_status"] in ("Submitted", "Under Review"))
    open_issues = sum(1 for i in isss if i["status"] in ("Open", "In Progress"))
    avg_task_progress = (sum(t["progress_percentage"] for t in tsks) / total_tasks) if total_tasks > 0 else 0.0

    # KPI Top Metric Row
    m1, m2, m3, m4, m5, m6, m7 = st.columns(7)
    with m1:
        st.metric("Total Projects", total_projects, delta=f"{active_projects} Active")
    with m2:
        st.metric("Requirements", total_requirements)
    with m3:
        st.metric("Tasks", total_tasks, delta=f"{completed_tasks} Done")
    with m4:
        st.metric("Overdue Tasks", overdue_tasks, delta_color="inverse")
    with m5:
        st.metric("Pending Reviews", pending_reviews)
    with m6:
        st.metric("Open Issues", open_issues, delta_color="inverse")
    with m7:
        st.metric("Avg Progress", f"{avg_task_progress:.1f}%")

    st.markdown("---")

    # Visualizations
    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown("##### Task Status Breakdown")
        if tsks:
            df_task = pd.DataFrame(tsks)
            status_counts = df_task["status"].value_counts().reset_index()
            status_counts.columns = ["Status", "Count"]
            fig_task = px.pie(
                status_counts,
                names="Status",
                values="Count",
                color="Status",
                color_discrete_map=STATUS_COLORS,
                hole=0.45,
            )
            fig_task.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=260)
            st.plotly_chart(fig_task, use_container_width=True)
        else:
            st.info("No task records available in selected scope.")

    with c2:
        st.markdown("##### Deliverable Review Status")
        if delivs:
            df_deliv = pd.DataFrame(delivs)
            deliv_counts = df_deliv["review_status"].value_counts().reset_index()
            deliv_counts.columns = ["Review Status", "Count"]
            fig_deliv = px.bar(
                deliv_counts,
                x="Review Status",
                y="Count",
                color="Review Status",
                color_discrete_map=STATUS_COLORS,
            )
            fig_deliv.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=260, showlegend=False)
            st.plotly_chart(fig_deliv, use_container_width=True)
        else:
            st.info("No deliverable records available in selected scope.")

    with c3:
        st.markdown("##### Project Priority Distribution")
        if prjs:
            df_prj = pd.DataFrame(prjs)
            pri_counts = df_prj["priority"].value_counts().reset_index()
            pri_counts.columns = ["Priority", "Count"]
            fig_pri = px.pie(
                pri_counts,
                names="Priority",
                values="Count",
                color="Priority",
                color_discrete_map=STATUS_COLORS,
                hole=0.45,
            )
            fig_pri.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=260)
            st.plotly_chart(fig_pri, use_container_width=True)
        else:
            st.info("No project records found.")

    st.markdown("---")

    # Bottom Row: Upcoming Deadlines & Recent Activity
    b1, b2 = st.columns([1.2, 1])

    with b1:
        st.markdown("##### 📅 Upcoming & Immediate Deadlines")
        deadline_items = []
        for t in tsks:
            if t.get("due_date") and t.get("status") != "Completed":
                deadline_items.append({
                    "Type": "Task",
                    "Code": t["task_code"],
                    "Item": t["task_description"],
                    "Assigned": t.get("assigned_to") or "Unassigned",
                    "Due Date": t["due_date"],
                    "Status": t["status"],
                })
        for d in delivs:
            if d.get("planned_date") and d.get("review_status") != "Approved":
                deadline_items.append({
                    "Type": "Deliverable",
                    "Code": d["deliverable_code"],
                    "Item": d["deliverable_name"],
                    "Assigned": d.get("prepared_by") or "Unassigned",
                    "Due Date": d["planned_date"],
                    "Status": d["review_status"],
                })

        if deadline_items:
            df_deadlines = pd.DataFrame(deadline_items).sort_values("Due Date").head(8)
            st.dataframe(df_deadlines, hide_index=True, use_container_width=True)
        else:
            st.success("No impending or overdue deadlines found in current scope.")

    with b2:
        st.markdown("##### 📜 Recent System Activity Log")
        logs = fetch_all("SELECT action_type, entity_type, description, created_at FROM activity_log ORDER BY log_id DESC LIMIT 8")
        if logs:
            df_logs = pd.DataFrame(logs)
            df_logs.columns = ["Action", "Entity", "Description", "Timestamp"]
            st.dataframe(df_logs, hide_index=True, use_container_width=True)
        else:
            st.info("No activity recorded yet.")


# =============================================================================
# PAGE 2: PROJECTS MANAGEMENT
# =============================================================================
elif selected_page == "Projects":
    st.markdown('<div class="main-header">Project Portfolio Management</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Register, monitor, edit, and decommission engineering projects.</div>', unsafe_allow_html=True)

    tab_list, tab_create, tab_edit = st.tabs(["📋 Projects Overview", "➕ Register New Project", "✏️ Edit / Manage Project"])

    with tab_list:
        f1, f2, f3 = st.columns([1, 1, 2])
        with f1:
            p_status_filter = st.selectbox("Status Filter", ["All"] + PROJECT_STATUSES, key="prj_stat_fltr")
        with f2:
            p_pri_filter = st.selectbox("Priority Filter", ["All"] + PROJECT_PRIORITIES, key="prj_pri_fltr")
        with f3:
            p_search = st.text_input("Search Projects", placeholder="Search by code, title, lead, stakeholder...", key="prj_search")

        project_records = projects.get_all_projects(status_filter=p_status_filter, priority_filter=p_pri_filter, search_term=p_search)
        if project_records:
            df_p = pd.DataFrame(project_records)[
                ["project_id", "project_code", "project_name", "project_type", "team_lead", "start_date", "deadline", "priority", "status"]
            ]
            st.dataframe(df_p, hide_index=True, use_container_width=True)
        else:
            st.info("No projects match the specified search or filter criteria.")

    with tab_create:
        st.markdown("##### Register a New Engineering Project")
        with st.form(key="create_project_form", clear_on_submit=True):
            col_p1, col_p2 = st.columns(2)
            with col_p1:
                new_p_code = st.text_input("Project Code*", placeholder="e.g., PRJ-CAL-04")
                new_p_name = st.text_input("Project Name*", placeholder="e.g., High-Precision Sensor Calibration")
                new_p_type = st.selectbox("Project Type*", PROJECT_TYPES)
                new_p_stakeholder = st.text_input("Stakeholder", placeholder="e.g., Turbine Reliability Division")
            with col_p2:
                new_p_lead = st.text_input("Team Lead", placeholder="e.g., Dr. Hannah Schmidt")
                new_p_start = st.date_input("Start Date*", value=date.today())
                new_p_deadline = st.date_input("Deadline*", value=date.today())
                col_sub1, col_sub2 = st.columns(2)
                with col_sub1:
                    new_p_pri = st.selectbox("Priority*", PROJECT_PRIORITIES, index=1)
                with col_sub2:
                    new_p_stat = st.selectbox("Status*", PROJECT_STATUSES, index=0)

            new_p_desc = st.text_area("Project Description", placeholder="Technical scope, objectives, and test requirements...")
            submit_create_p = st.form_submit_button("Create Project", type="primary")

            if submit_create_p:
                try:
                    p_id = projects.create_project({
                        "project_code": new_p_code,
                        "project_name": new_p_name,
                        "project_type": new_p_type,
                        "description": new_p_desc,
                        "stakeholder": new_p_stakeholder,
                        "team_lead": new_p_lead,
                        "start_date": new_p_start.isoformat(),
                        "deadline": new_p_deadline.isoformat(),
                        "priority": new_p_pri,
                        "status": new_p_stat,
                    })
                    st.success(f"Project '{new_p_code}' successfully created with ID {p_id}!")
                    st.rerun()
                except Exception as ex:
                    st.error(f"Error creating project: {ex}")

    with tab_edit:
        st.markdown("##### Update or Remove an Existing Project")
        all_p = projects.get_all_projects()
        if not all_p:
            st.info("No projects registered yet.")
        else:
            p_select_map = {f"{p['project_code']} — {p['project_name']}": p["project_id"] for p in all_p}
            selected_edit_label = st.selectbox("Select Project to Manage", list(p_select_map.keys()), key="edit_prj_sel")
            selected_edit_id = p_select_map[selected_edit_label]
            target_proj = projects.get_project(selected_edit_id)

            if target_proj:
                with st.form(key="update_project_form"):
                    u_col1, u_col2 = st.columns(2)
                    with u_col1:
                        u_p_code = st.text_input("Project Code*", value=target_proj["project_code"])
                        u_p_name = st.text_input("Project Name*", value=target_proj["project_name"])
                        u_p_type = st.selectbox("Project Type*", PROJECT_TYPES, index=PROJECT_TYPES.index(target_proj["project_type"]) if target_proj["project_type"] in PROJECT_TYPES else 0)
                        u_p_stakeholder = st.text_input("Stakeholder", value=target_proj["stakeholder"] or "")
                    with u_col2:
                        u_p_lead = st.text_input("Team Lead", value=target_proj["team_lead"] or "")
                        # Parse start date & deadline
                        sd_val = datetime.strptime(target_proj["start_date"][:10], "%Y-%m-%d").date() if target_proj["start_date"] else date.today()
                        dd_val = datetime.strptime(target_proj["deadline"][:10], "%Y-%m-%d").date() if target_proj["deadline"] else date.today()
                        u_p_start = st.date_input("Start Date*", value=sd_val)
                        u_p_deadline = st.date_input("Deadline*", value=dd_val)
                        u_c1, u_c2 = st.columns(2)
                        with u_c1:
                            u_p_pri = st.selectbox("Priority*", PROJECT_PRIORITIES, index=PROJECT_PRIORITIES.index(target_proj["priority"]) if target_proj["priority"] in PROJECT_PRIORITIES else 1)
                        with u_c2:
                            u_p_stat = st.selectbox("Status*", PROJECT_STATUSES, index=PROJECT_STATUSES.index(target_proj["status"]) if target_proj["status"] in PROJECT_STATUSES else 0)

                    u_p_desc = st.text_area("Project Description", value=target_proj["description"] or "")
                    update_btn = st.form_submit_button("Save Changes", type="primary")

                    if update_btn:
                        try:
                            projects.update_project(selected_edit_id, {
                                "project_code": u_p_code,
                                "project_name": u_p_name,
                                "project_type": u_p_type,
                                "description": u_p_desc,
                                "stakeholder": u_p_stakeholder,
                                "team_lead": u_p_lead,
                                "start_date": u_p_start.isoformat(),
                                "deadline": u_p_deadline.isoformat(),
                                "priority": u_p_pri,
                                "status": u_p_stat,
                            })
                            st.success("Project details successfully updated!")
                            st.rerun()
                        except Exception as ex:
                            st.error(f"Error updating project: {ex}")

                # Deletion section with dependency check
                st.markdown("---")
                st.markdown("##### 🗑️ Project Decommissioning / Deletion")
                deps = projects.get_project_dependencies_count(selected_edit_id)
                if deps["total"] > 0:
                    st.warning(
                        f"⚠️ This project has {deps['requirements']} requirements, {deps['tasks']} tasks, "
                        f"{deps['deliverables']} deliverables, and {deps['issues']} issues attached."
                    )
                force_cascade = st.checkbox("Confirm cascade deletion of all child requirements, tasks, and deliverables", key="del_prj_cascade")
                if st.button("Delete Project", type="secondary", key="del_prj_btn"):
                    try:
                        projects.delete_project(selected_edit_id, cascade=force_cascade)
                        st.success(f"Project '{target_proj['project_code']}' deleted.")
                        st.rerun()
                    except Exception as ex:
                        st.error(f"Deletion blocked: {ex}")


# =============================================================================
# PAGE 3: REQUIREMENTS MANAGEMENT
# =============================================================================
elif selected_page == "Requirements":
    st.markdown('<div class="main-header">Requirements Traceability & Clarifications</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Manage engineering specifications, acceptance criteria, and clarification tracking.</div>', unsafe_allow_html=True)

    r_tab1, r_tab2, r_tab3 = st.tabs(["📋 Requirements Register", "➕ New Requirement", "✏️ Update / Delete Requirement"])

    with r_tab1:
        rc1, rc2, rc3, rc4 = st.columns([1, 1, 1, 2])
        with rc1:
            req_stat_filter = st.selectbox("Status Filter", ["All"] + REQUIREMENT_STATUSES, key="req_stat_fltr")
        with rc2:
            req_pri_filter = st.selectbox("Priority Filter", ["All"] + REQUIREMENT_PRIORITIES, key="req_pri_fltr")
        with rc3:
            clarif_only = st.checkbox("Clarification Required Only", key="req_clarif_chk")
        with rc4:
            req_search = st.text_input("Search Requirements", placeholder="Code, description, owner...", key="req_srch")

        req_list = requirements.get_requirements(
            project_id=current_project_id,
            status_filter=req_stat_filter,
            priority_filter=req_pri_filter,
            needs_clarification_only=clarif_only,
            search_term=req_search,
        )

        if req_list:
            df_r = pd.DataFrame(req_list)[
                ["requirement_id", "project_code", "requirement_code", "description", "acceptance_criteria", "priority", "status", "clarification_question", "owner", "due_date"]
            ]
            st.dataframe(df_r, hide_index=True, use_container_width=True)
        else:
            st.info("No requirements match the specified filter criteria.")

    with r_tab2:
        st.markdown("##### Add Requirement to Project")
        prjs_for_req = projects.get_all_projects()
        if not prjs_for_req:
            st.warning("Please create a project first before registering requirements.")
        else:
            with st.form(key="create_req_form", clear_on_submit=True):
                c1, c2 = st.columns(2)
                with c1:
                    r_prj_sel = st.selectbox("Project*", options=[f"{p['project_code']} — {p['project_name']}" for p in prjs_for_req], key="req_prj_select")
                    r_prj_id = [p["project_id"] for p in prjs_for_req if f"{p['project_code']} — {p['project_name']}" == r_prj_sel][0]
                    r_code = st.text_input("Requirement Code*", placeholder="e.g., REQ-VIB-101")
                    r_owner = st.text_input("Owner / Lead Engineer", placeholder="e.g., David Kim")
                    r_due = st.date_input("Due Date", value=date.today())
                with c2:
                    r_pri = st.selectbox("Priority*", REQUIREMENT_PRIORITIES, index=1)
                    r_stat = st.selectbox("Status*", REQUIREMENT_STATUSES, index=0)
                    r_clarif = st.text_area("Clarification Question (if any)", placeholder="Pending questions for stakeholders...")

                r_desc = st.text_area("Description*", placeholder="Engineering requirement description...")
                r_ac = st.text_area("Acceptance Criteria", placeholder="Measurable pass/fail criteria, tolerances, standards...")

                sub_req = st.form_submit_button("Create Requirement", type="primary")
                if sub_req:
                    try:
                        rid = requirements.create_requirement({
                            "project_id": r_prj_id,
                            "requirement_code": r_code,
                            "description": r_desc,
                            "acceptance_criteria": r_ac,
                            "priority": r_pri,
                            "status": r_stat,
                            "clarification_question": r_clarif,
                            "owner": r_owner,
                            "due_date": r_due.isoformat() if r_due else None,
                        })
                        st.success(f"Requirement '{r_code}' registered successfully!")
                        st.rerun()
                    except Exception as ex:
                        st.error(f"Failed to create requirement: {ex}")

    with r_tab3:
        st.markdown("##### Update or Remove Requirement")
        all_reqs_for_edit = requirements.get_requirements(project_id=current_project_id)
        if not all_reqs_for_edit:
            st.info("No requirements available to edit.")
        else:
            r_map = {f"{r['requirement_code']} — {r['description'][:50]}...": r["requirement_id"] for r in all_reqs_for_edit}
            selected_r_label = st.selectbox("Select Requirement", list(r_map.keys()), key="edit_req_sel")
            target_r_id = r_map[selected_r_label]
            target_r = requirements.get_requirement(target_r_id)

            if target_r:
                with st.form(key="update_req_form"):
                    rc1, rc2 = st.columns(2)
                    with rc1:
                        u_r_code = st.text_input("Requirement Code*", value=target_r["requirement_code"])
                        u_r_owner = st.text_input("Owner", value=target_r["owner"] or "")
                        cur_due = datetime.strptime(target_r["due_date"][:10], "%Y-%m-%d").date() if target_r["due_date"] else date.today()
                        u_r_due = st.date_input("Due Date", value=cur_due)
                    with rc2:
                        u_r_pri = st.selectbox("Priority*", REQUIREMENT_PRIORITIES, index=REQUIREMENT_PRIORITIES.index(target_r["priority"]))
                        u_r_stat = st.selectbox("Status*", REQUIREMENT_STATUSES, index=REQUIREMENT_STATUSES.index(target_r["status"]))
                        u_r_clarif = st.text_area("Clarification Question", value=target_r["clarification_question"] or "")

                    u_r_desc = st.text_area("Description*", value=target_r["description"])
                    u_r_ac = st.text_area("Acceptance Criteria", value=target_r["acceptance_criteria"] or "")

                    save_r = st.form_submit_button("Save Changes", type="primary")
                    if save_r:
                        try:
                            requirements.update_requirement(target_r_id, {
                                "project_id": target_r["project_id"],
                                "requirement_code": u_r_code,
                                "description": u_r_desc,
                                "acceptance_criteria": u_r_ac,
                                "priority": u_r_pri,
                                "status": u_r_stat,
                                "clarification_question": u_r_clarif,
                                "owner": u_r_owner,
                                "due_date": u_r_due.isoformat() if u_r_due else None,
                            })
                            st.success("Requirement successfully updated!")
                            st.rerun()
                        except Exception as ex:
                            st.error(f"Error updating requirement: {ex}")

                if st.button("Delete Requirement", type="secondary", key="del_req_btn"):
                    try:
                        requirements.delete_requirement(target_r_id)
                        st.success(f"Requirement '{target_r['requirement_code']}' deleted.")
                        st.rerun()
                    except Exception as ex:
                        st.error(f"Failed to delete requirement: {ex}")


# =============================================================================
# PAGE 4: TASK MANAGEMENT
# =============================================================================
elif selected_page == "Tasks":
    st.markdown('<div class="main-header">Engineering Tasks & Activities</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Plan, assign, update progress, and monitor overdue tasks.</div>', unsafe_allow_html=True)

    # Summary Metrics Row
    summary = tasks.get_task_summary(project_id=current_project_id)
    s1, s2, s3, s4, s5, s6 = st.columns(6)
    with s1:
        st.metric("Total Tasks", summary["total"])
    with s2:
        st.metric("In Progress", summary["in_progress"])
    with s3:
        st.metric("Completed", summary["completed"])
    with s4:
        st.metric("Blocked", summary["blocked"])
    with s5:
        st.metric("Overdue", summary["overdue"], delta_color="inverse")
    with s6:
        st.metric("Avg Progress", f"{summary['avg_progress']}%")

    st.markdown("---")

    t_tab1, t_tab2, t_tab3, t_tab4 = st.tabs(["📋 Tasks List", "⚡ Quick Progress Update", "➕ Create Task", "✏️ Edit / Delete Task"])

    with t_tab1:
        tc1, tc2, tc3, tc4 = st.columns([1, 1, 1, 2])
        with tc1:
            t_stat_filter = st.selectbox("Status Filter", ["All"] + TASK_STATUSES, key="task_stat_fltr")
        with tc2:
            t_pri_filter = st.selectbox("Priority Filter", ["All"] + TASK_PRIORITIES, key="task_pri_fltr")
        with tc3:
            t_overdue_only = st.checkbox("Overdue Tasks Only", key="task_overdue_chk")
        with tc4:
            t_search = st.text_input("Search Tasks", placeholder="Task code, description, assignee...", key="task_srch")

        all_tasks = tasks.get_tasks(
            project_id=current_project_id,
            status_filter=t_stat_filter,
            priority_filter=t_pri_filter,
            overdue_only=t_overdue_only,
            search_term=t_search,
        )

        if all_tasks:
            df_t = pd.DataFrame(all_tasks)[
                ["task_id", "project_code", "task_code", "task_description", "assigned_to", "priority", "status", "progress_percentage", "due_date", "is_overdue"]
            ]
            st.dataframe(df_t, hide_index=True, use_container_width=True)
        else:
            st.info("No tasks found matching criteria.")

    with t_tab2:
        st.markdown("##### Quick Progress Adjuster")
        all_tasks_quick = tasks.get_tasks(project_id=current_project_id)
        if not all_tasks_quick:
            st.info("No tasks available.")
        else:
            q_map = {f"{t['task_code']} — {t['task_description'][:40]} (Cur: {t['progress_percentage']}%)": t["task_id"] for t in all_tasks_quick}
            sel_q_task = st.selectbox("Select Task to Update", list(q_map.keys()), key="quick_task_sel")
            q_task_id = q_map[sel_q_task]
            q_target = tasks.get_task(q_task_id)

            if q_target:
                new_prog = st.slider("Completion Percentage (%)", min_value=0, max_value=100, value=int(q_target["progress_percentage"]), step=5)
                new_stat = st.selectbox("Status", TASK_STATUSES, index=TASK_STATUSES.index(q_target["status"]))
                if st.button("Apply Progress Update", type="primary", key="apply_prog_btn"):
                    try:
                        tasks.update_task_progress(q_task_id, new_prog, status=new_stat)
                        st.success(f"Task {q_target['task_code']} updated to {new_prog}% ({new_stat})!")
                        st.rerun()
                    except Exception as ex:
                        st.error(f"Failed to update progress: {ex}")

    with t_tab3:
        st.markdown("##### Create Engineering Task")
        prjs_for_task = projects.get_all_projects()
        if not prjs_for_task:
            st.warning("Please create a project first.")
        else:
            with st.form(key="create_task_form", clear_on_submit=True):
                col_t1, col_t2 = st.columns(2)
                with col_t1:
                    t_prj_sel = st.selectbox("Project*", options=[f"{p['project_code']} — {p['project_name']}" for p in prjs_for_task], key="task_prj_sel")
                    t_prj_id = [p["project_id"] for p in prjs_for_task if f"{p['project_code']} — {p['project_name']}" == t_prj_sel][0]
                    # Fetch linked requirements for this project
                    p_reqs = requirements.get_requirements(project_id=t_prj_id)
                    req_options = {"None (Unlinked)": None}
                    for r in p_reqs:
                        req_options[f"{r['requirement_code']} — {r['description'][:30]}"] = r["requirement_id"]
                    t_req_sel = st.selectbox("Linked Requirement", list(req_options.keys()))
                    t_req_id = req_options[t_req_sel]

                    t_code = st.text_input("Task Code*", placeholder="e.g., TSK-INS-501")
                    t_assigned = st.text_input("Assigned Engineer", placeholder="e.g., Carlos Mendez")

                with col_t2:
                    t_pri = st.selectbox("Priority*", TASK_PRIORITIES, index=1)
                    t_stat = st.selectbox("Status*", TASK_STATUSES, index=0)
                    t_prog = st.slider("Progress (%)", 0, 100, 0, 5)
                    t_sd = st.date_input("Start Date", value=date.today())
                    t_dd = st.date_input("Due Date", value=date.today())

                t_desc = st.text_area("Task Description*", placeholder="Detailed instructions, acceptance parameters...")
                t_notes = st.text_area("Notes / Progress Log", placeholder="Observations, impediments, test rig notes...")

                sub_t = st.form_submit_button("Create Task", type="primary")
                if sub_t:
                    try:
                        tasks.create_task({
                            "project_id": t_prj_id,
                            "requirement_id": t_req_id,
                            "task_code": t_code,
                            "task_description": t_desc,
                            "assigned_to": t_assigned,
                            "priority": t_pri,
                            "start_date": t_sd.isoformat() if t_sd else None,
                            "due_date": t_dd.isoformat() if t_dd else None,
                            "status": t_stat,
                            "progress_percentage": t_prog,
                            "notes": t_notes,
                        })
                        st.success(f"Task '{t_code}' successfully created!")
                        st.rerun()
                    except Exception as ex:
                        st.error(f"Error creating task: {ex}")

    with t_tab4:
        st.markdown("##### Edit or Delete Task")
        all_tsks = tasks.get_tasks(project_id=current_project_id)
        if not all_tsks:
            st.info("No tasks to edit.")
        else:
            t_map = {f"{t['task_code']} — {t['task_description'][:40]}": t["task_id"] for t in all_tsks}
            sel_t_label = st.selectbox("Select Task", list(t_map.keys()), key="edit_task_sel")
            t_target_id = t_map[sel_t_label]
            target_tsk = tasks.get_task(t_target_id)

            if target_tsk:
                with st.form(key="update_task_form"):
                    c1, c2 = st.columns(2)
                    with c1:
                        u_t_code = st.text_input("Task Code*", value=target_tsk["task_code"])
                        u_t_assigned = st.text_input("Assigned To", value=target_tsk["assigned_to"] or "")
                        sd_cur = datetime.strptime(target_tsk["start_date"][:10], "%Y-%m-%d").date() if target_tsk["start_date"] else date.today()
                        dd_cur = datetime.strptime(target_tsk["due_date"][:10], "%Y-%m-%d").date() if target_tsk["due_date"] else date.today()
                        u_t_sd = st.date_input("Start Date", value=sd_cur)
                        u_t_dd = st.date_input("Due Date", value=dd_cur)
                    with c2:
                        u_t_pri = st.selectbox("Priority*", TASK_PRIORITIES, index=TASK_PRIORITIES.index(target_tsk["priority"]))
                        u_t_stat = st.selectbox("Status*", TASK_STATUSES, index=TASK_STATUSES.index(target_tsk["status"]))
                        u_t_prog = st.slider("Progress (%)", 0, 100, value=int(target_tsk["progress_percentage"]), step=5)

                    u_t_desc = st.text_area("Task Description*", value=target_tsk["task_description"])
                    u_t_notes = st.text_area("Notes", value=target_tsk["notes"] or "")

                    save_t = st.form_submit_button("Save Changes", type="primary")
                    if save_t:
                        try:
                            tasks.update_task(t_target_id, {
                                "project_id": target_tsk["project_id"],
                                "requirement_id": target_tsk.get("requirement_id"),
                                "task_code": u_t_code,
                                "task_description": u_t_desc,
                                "assigned_to": u_t_assigned,
                                "priority": u_t_pri,
                                "start_date": u_t_sd.isoformat() if u_t_sd else None,
                                "due_date": u_t_dd.isoformat() if u_t_dd else None,
                                "status": u_t_stat,
                                "progress_percentage": u_t_prog,
                                "notes": u_t_notes,
                            })
                            st.success("Task updated successfully!")
                            st.rerun()
                        except Exception as ex:
                            st.error(f"Error updating task: {ex}")

                if st.button("Delete Task", type="secondary", key="del_tsk_btn"):
                    try:
                        tasks.delete_task(t_target_id)
                        st.success(f"Task '{target_tsk['task_code']}' deleted.")
                        st.rerun()
                    except Exception as ex:
                        st.error(f"Error deleting task: {ex}")


# =============================================================================
# PAGE 5: DELIVERABLES MANAGEMENT
# =============================================================================
elif selected_page == "Deliverables":
    st.markdown('<div class="main-header">Engineering Deliverables & Quality Gates</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Track engineering documents, CAD models, test protocols, versions, and peer review status.</div>', unsafe_allow_html=True)

    d_tab1, d_tab2, d_tab3 = st.tabs(["📋 Deliverables Matrix", "➕ Register Deliverable", "✏️ Review & Edit Deliverable"])

    with d_tab1:
        dc1, dc2, dc3, dc4 = st.columns([1, 1, 1, 2])
        with dc1:
            d_stat_filter = st.selectbox("Review Status", ["All"] + DELIVERABLE_REVIEW_STATUSES, key="del_stat_fltr")
        with dc2:
            d_type_filter = st.selectbox("Deliverable Type", ["All"] + DELIVERABLE_TYPES, key="del_type_fltr")
        with dc3:
            d_pending_only = st.checkbox("Pending Review Only", key="del_pend_chk")
            d_rework_only = st.checkbox("Rework Required Only", key="del_rework_chk")
        with dc4:
            d_search = st.text_input("Search Deliverables", placeholder="Code, name, author, reviewer...", key="del_srch")

        all_delivs = deliverables.get_deliverables(
            project_id=current_project_id,
            review_status_filter=d_stat_filter,
            deliverable_type_filter=d_type_filter,
            pending_review_only=d_pending_only,
            rework_required_only=d_rework_only,
            search_term=d_search,
        )

        if all_delivs:
            df_d = pd.DataFrame(all_delivs)[
                ["deliverable_id", "project_code", "deliverable_code", "deliverable_name", "deliverable_type", "version", "prepared_by", "reviewer", "review_status", "submission_date", "file_name"]
            ]
            st.dataframe(df_d, hide_index=True, use_container_width=True)
        else:
            st.info("No deliverables found matching filters.")

    with d_tab2:
        st.markdown("##### Register Engineering Deliverable")
        prjs_for_del = projects.get_all_projects()
        if not prjs_for_del:
            st.warning("Please create a project first.")
        else:
            with st.form(key="create_deliv_form", clear_on_submit=True):
                c1, c2 = st.columns(2)
                with c1:
                    d_prj_sel = st.selectbox("Project*", options=[f"{p['project_code']} — {p['project_name']}" for p in prjs_for_del], key="del_prj_sel")
                    d_prj_id = [p["project_id"] for p in prjs_for_del if f"{p['project_code']} — {p['project_name']}" == d_prj_sel][0]
                    d_code = st.text_input("Deliverable Code*", placeholder="e.g., DEL-INS-705")
                    d_name = st.text_input("Deliverable Name*", placeholder="e.g., Rotor Dynamic Analysis Final Report")
                    d_type = st.selectbox("Deliverable Type*", DELIVERABLE_TYPES)
                    d_ver = st.text_input("Version*", value="v1.0")
                with c2:
                    d_prep = st.text_input("Prepared By", placeholder="Author engineer name...")
                    d_rev = st.text_input("Designated Reviewer", placeholder="Lead reviewer name...")
                    d_stat = st.selectbox("Review Status*", DELIVERABLE_REVIEW_STATUSES, index=0)
                    d_plan_date = st.date_input("Planned Submission Date", value=date.today())
                    d_sub_date = st.date_input("Actual Submission Date (Optional)", value=None)

                d_file = st.text_input("File Name / Attachment Reference", placeholder="e.g., Rotor_Dynamic_Analysis_v1.0.pdf")
                d_comm = st.text_area("Review Comments / Revision Notes", placeholder="Summary of changes or technical sign-off notes...")

                sub_d = st.form_submit_button("Register Deliverable", type="primary")
                if sub_d:
                    try:
                        deliverables.create_deliverable({
                            "project_id": d_prj_id,
                            "deliverable_code": d_code,
                            "deliverable_name": d_name,
                            "deliverable_type": d_type,
                            "version": d_ver,
                            "prepared_by": d_prep,
                            "reviewer": d_rev,
                            "planned_date": d_plan_date.isoformat() if d_plan_date else None,
                            "submission_date": d_sub_date.isoformat() if d_sub_date else None,
                            "review_status": d_stat,
                            "file_name": d_file,
                            "comments": d_comm,
                        })
                        st.success(f"Deliverable '{d_code}' registered!")
                        st.rerun()
                    except Exception as ex:
                        st.error(f"Error registering deliverable: {ex}")

    with d_tab3:
        st.markdown("##### Update Deliverable & Review Workflow")
        all_delivs_edit = deliverables.get_deliverables(project_id=current_project_id)
        if not all_delivs_edit:
            st.info("No deliverables available.")
        else:
            d_map = {f"{d['deliverable_code']} — {d['deliverable_name']} ({d['review_status']})": d["deliverable_id"] for d in all_delivs_edit}
            sel_d_label = st.selectbox("Select Deliverable", list(d_map.keys()), key="edit_del_sel")
            d_target_id = d_map[sel_d_label]
            target_del = deliverables.get_deliverable(d_target_id)

            if target_del:
                with st.form(key="update_deliv_form"):
                    c1, c2 = st.columns(2)
                    with c1:
                        u_d_code = st.text_input("Deliverable Code*", value=target_del["deliverable_code"])
                        u_d_name = st.text_input("Deliverable Name*", value=target_del["deliverable_name"])
                        u_d_type = st.selectbox("Deliverable Type*", DELIVERABLE_TYPES, index=DELIVERABLE_TYPES.index(target_del["deliverable_type"]) if target_del["deliverable_type"] in DELIVERABLE_TYPES else 0)
                        u_d_ver = st.text_input("Version*", value=target_del["version"])
                    with c2:
                        u_d_prep = st.text_input("Prepared By", value=target_del["prepared_by"] or "")
                        u_d_rev = st.text_input("Reviewer", value=target_del["reviewer"] or "")
                        u_d_stat = st.selectbox("Review Status*", DELIVERABLE_REVIEW_STATUSES, index=DELIVERABLE_REVIEW_STATUSES.index(target_del["review_status"]))
                        cur_plan = datetime.strptime(target_del["planned_date"][:10], "%Y-%m-%d").date() if target_del["planned_date"] else date.today()
                        u_d_plan = st.date_input("Planned Date", value=cur_plan)

                    u_d_file = st.text_input("File Name", value=target_del["file_name"] or "")
                    u_d_comm = st.text_area("Review Comments", value=target_del["comments"] or "")

                    save_d = st.form_submit_button("Save Review Status & Changes", type="primary")
                    if save_d:
                        try:
                            deliverables.update_deliverable(d_target_id, {
                                "project_id": target_del["project_id"],
                                "deliverable_code": u_d_code,
                                "deliverable_name": u_d_name,
                                "deliverable_type": u_d_type,
                                "version": u_d_ver,
                                "prepared_by": u_d_prep,
                                "reviewer": u_d_rev,
                                "planned_date": u_d_plan.isoformat() if u_d_plan else None,
                                "submission_date": target_del["submission_date"],
                                "review_status": u_d_stat,
                                "file_name": u_d_file,
                                "comments": u_d_comm,
                            })
                            st.success("Deliverable updated!")
                            st.rerun()
                        except Exception as ex:
                            st.error(f"Error updating deliverable: {ex}")

                if st.button("Delete Deliverable", type="secondary", key="del_deliv_btn"):
                    try:
                        deliverables.delete_deliverable(d_target_id)
                        st.success(f"Deliverable '{target_del['deliverable_code']}' deleted.")
                        st.rerun()
                    except Exception as ex:
                        st.error(f"Error deleting deliverable: {ex}")


# =============================================================================
# PAGE 6: QUALITY ASSURANCE ENGINE
# =============================================================================
elif selected_page == "Quality Assurance":
    st.markdown('<div class="main-header">Quality Assurance Audit Engine</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Automated 12-rule engineering audit verifying data integrity, traceability, and workflow compliance.</div>', unsafe_allow_html=True)

    col_btn, col_info = st.columns([1, 3])
    with col_btn:
        run_qa_btn = st.button("🚀 Run Quality Checks", type="primary", use_container_width=True)
    with col_info:
        st.caption("Executes all 12 validation rules across active projects, requirements, tasks, deliverables, and issues.")

    if run_qa_btn:
        with st.spinner("Executing QA audit rules against SQLite database..."):
            results = quality_checks.run_all_quality_checks(project_id=current_project_id, save_to_db=True)
            st.success(f"Audit completed: {len(results)} findings processed and saved to database.")

    # Fetch latest quality checks from database
    latest_checks = quality_checks.get_latest_quality_checks(project_id=current_project_id)

    # QA KPI Metrics
    total_checks = len(latest_checks)
    passed_checks = sum(1 for c in latest_checks if c["check_result"] == "PASS")
    warning_checks = sum(1 for c in latest_checks if c["check_result"] == "WARNING")
    failed_checks = sum(1 for c in latest_checks if c["check_result"] == "FAIL")

    qk1, qk2, qk3, qk4 = st.columns(4)
    with qk1:
        st.metric("Total Checks Evaluated", total_checks)
    with qk2:
        st.metric("Passed Checks", passed_checks)
    with qk3:
        st.metric("Warnings Flagged", warning_checks)
    with qk4:
        st.metric("Failures Detected", failed_checks, delta_color="inverse")

    st.markdown("---")

    # Filter QA findings
    qf1, qf2, qf3 = st.columns([1, 1, 2])
    with qf1:
        qa_res_filter = st.selectbox("Result Filter", ["All", "FAIL", "WARNING", "PASS"], key="qa_res_fltr")
    with qf2:
        qa_ent_filter = st.selectbox("Entity Filter", ["All"] + ENTITY_TYPES, key="qa_ent_fltr")
    with qf3:
        st.markdown("<br>", unsafe_allow_html=True)
        # Export QA results to CSV
        if latest_checks:
            qa_df = pd.DataFrame(latest_checks)
            csv_qa = qa_df.to_csv(index=False).encode("utf-8")
            st.download_button("📥 Export QA Audit Results (CSV)", data=csv_qa, file_name=f"QA_Audit_Results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv", mime="text/csv")

    filtered_checks = quality_checks.get_latest_quality_checks(
        project_id=current_project_id,
        result_filter=qa_res_filter,
        entity_type_filter=qa_ent_filter,
    )

    if filtered_checks:
        display_qa = pd.DataFrame(filtered_checks)[
            ["check_id", "check_result", "check_name", "entity_type", "entity_id", "error_message", "checked_at"]
        ]
        st.dataframe(display_qa, hide_index=True, use_container_width=True)
    else:
        st.info("No quality checks match the current filter selection.")


# =============================================================================
# PAGE 7: ISSUES & CLARIFICATIONS
# =============================================================================
elif selected_page == "Issues & Clarifications":
    st.markdown('<div class="main-header">Issues, Defects & Clarifications</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Log technical questions, identify engineering blockers, assign owners, and track resolutions.</div>', unsafe_allow_html=True)

    i_tab1, i_tab2, i_tab3 = st.tabs(["📋 Issues Log", "➕ Log New Issue", "✏️ Update / Resolve Issue"])

    with i_tab1:
        ic1, ic2, ic3, ic4 = st.columns([1, 1, 1, 2])
        with ic1:
            i_sev_filter = st.selectbox("Severity Filter", ["All"] + ISSUE_SEVERITIES, key="iss_sev_fltr")
        with ic2:
            i_stat_filter = st.selectbox("Status Filter", ["All"] + ISSUE_STATUSES, key="iss_stat_fltr")
        with ic3:
            i_overdue_chk = st.checkbox("Overdue Issues Only", key="iss_od_chk")
        with ic4:
            i_search = st.text_input("Search Issues", placeholder="Code, description, owner, resolution...", key="iss_srch")

        all_issues = issues.get_issues(
            project_id=current_project_id,
            severity_filter=i_sev_filter,
            status_filter=i_stat_filter,
            overdue_only=i_overdue_chk,
            search_term=i_search,
        )

        if all_issues:
            df_i = pd.DataFrame(all_issues)[
                ["issue_id", "project_code", "issue_code", "description", "severity", "owner", "status", "target_date", "is_overdue", "resolution_notes"]
            ]
            st.dataframe(df_i, hide_index=True, use_container_width=True)
        else:
            st.info("No issues found.")

    with i_tab2:
        st.markdown("##### Log New Engineering Issue")
        prjs_for_iss = projects.get_all_projects()
        if not prjs_for_iss:
            st.warning("Please create a project first.")
        else:
            with st.form(key="create_issue_form", clear_on_submit=True):
                c1, c2 = st.columns(2)
                with c1:
                    i_prj_sel = st.selectbox("Project*", options=[f"{p['project_code']} — {p['project_name']}" for p in prjs_for_iss], key="iss_prj_sel")
                    i_prj_id = [p["project_id"] for p in prjs_for_iss if f"{p['project_code']} — {p['project_name']}" == i_prj_sel][0]
                    # Fetch linked reqs & tasks
                    p_reqs = requirements.get_requirements(project_id=i_prj_id)
                    p_tasks = tasks.get_tasks(project_id=i_prj_id)
                    req_opts = {"None": None}
                    for r in p_reqs:
                        req_opts[f"{r['requirement_code']} — {r['description'][:30]}"] = r["requirement_id"]
                    tsk_opts = {"None": None}
                    for t in p_tasks:
                        tsk_opts[f"{t['task_code']} — {t['task_description'][:30]}"] = t["task_id"]

                    i_req_sel = st.selectbox("Related Requirement", list(req_opts.keys()))
                    i_tsk_sel = st.selectbox("Related Task", list(tsk_opts.keys()))
                    i_code = st.text_input("Issue Code*", placeholder="e.g., ISS-INS-904")
                with c2:
                    i_sev = st.selectbox("Severity*", ISSUE_SEVERITIES, index=1)
                    i_stat = st.selectbox("Status*", ISSUE_STATUSES, index=0)
                    i_owner = st.text_input("Owner / Responsible Engineer", placeholder="e.g., Elena Rostova")
                    i_target = st.date_input("Target Resolution Date", value=date.today())

                i_desc = st.text_area("Issue Description*", placeholder="Failure symptom, drift observed, or specification discrepancy...")
                i_res = st.text_area("Resolution Notes (if resolving)", placeholder="Corrective actions taken, verification protocol...")

                sub_i = st.form_submit_button("Log Issue", type="primary")
                if sub_i:
                    try:
                        issues.create_issue({
                            "project_id": i_prj_id,
                            "related_requirement_id": req_opts[i_req_sel],
                            "related_task_id": tsk_opts[i_tsk_sel],
                            "issue_code": i_code,
                            "description": i_desc,
                            "severity": i_sev,
                            "owner": i_owner,
                            "status": i_stat,
                            "target_date": i_target.isoformat() if i_target else None,
                            "resolution_notes": i_res,
                        })
                        st.success(f"Issue '{i_code}' registered successfully!")
                        st.rerun()
                    except Exception as ex:
                        st.error(f"Error logging issue: {ex}")

    with i_tab3:
        st.markdown("##### Update or Resolve Issue")
        all_issues_edit = issues.get_issues(project_id=current_project_id)
        if not all_issues_edit:
            st.info("No issues to manage.")
        else:
            i_map = {f"{i['issue_code']} — {i['description'][:40]} ({i['status']})": i["issue_id"] for i in all_issues_edit}
            sel_i_label = st.selectbox("Select Issue", list(i_map.keys()), key="edit_iss_sel")
            i_target_id = i_map[sel_i_label]
            target_iss = issues.get_issue(i_target_id)

            if target_iss:
                with st.form(key="update_issue_form"):
                    c1, c2 = st.columns(2)
                    with c1:
                        u_i_code = st.text_input("Issue Code*", value=target_iss["issue_code"])
                        u_i_owner = st.text_input("Owner", value=target_iss["owner"] or "")
                        cur_tgt = datetime.strptime(target_iss["target_date"][:10], "%Y-%m-%d").date() if target_iss["target_date"] else date.today()
                        u_i_target = st.date_input("Target Date", value=cur_tgt)
                    with c2:
                        u_i_sev = st.selectbox("Severity*", ISSUE_SEVERITIES, index=ISSUE_SEVERITIES.index(target_iss["severity"]))
                        u_i_stat = st.selectbox("Status*", ISSUE_STATUSES, index=ISSUE_STATUSES.index(target_iss["status"]))

                    u_i_desc = st.text_area("Description*", value=target_iss["description"])
                    u_i_notes = st.text_area("Resolution Notes", value=target_iss["resolution_notes"] or "")

                    save_i = st.form_submit_button("Save Changes", type="primary")
                    if save_i:
                        try:
                            issues.update_issue(i_target_id, {
                                "project_id": target_iss["project_id"],
                                "related_requirement_id": target_iss.get("related_requirement_id"),
                                "related_task_id": target_iss.get("related_task_id"),
                                "issue_code": u_i_code,
                                "description": u_i_desc,
                                "severity": u_i_sev,
                                "owner": u_i_owner,
                                "status": u_i_stat,
                                "target_date": u_i_target.isoformat() if u_i_target else None,
                                "resolution_notes": u_i_notes,
                            })
                            st.success("Issue successfully updated!")
                            st.rerun()
                        except Exception as ex:
                            st.error(f"Error updating issue: {ex}")

                if st.button("Delete Issue", type="secondary", key="del_iss_btn"):
                    try:
                        issues.delete_issue(i_target_id)
                        st.success(f"Issue '{target_iss['issue_code']}' deleted.")
                        st.rerun()
                    except Exception as ex:
                        st.error(f"Error deleting issue: {ex}")


# =============================================================================
# PAGE 8: REPORTS & EXPORTS
# =============================================================================
elif selected_page == "Reports":
    st.markdown('<div class="main-header">Automated Project Reports & Data Exports</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Generate executive Excel workbooks and tabular CSV exports across all engineering domains.</div>', unsafe_allow_html=True)

    r_col1, r_col2 = st.columns([1.2, 1])

    with r_col1:
        st.markdown("##### 📊 Full Project Portfolio Excel Report")
        st.write("Generates an Excel workbook containing 7 formatted worksheets with freeze panes, auto-filters, and auto-fitted columns:")
        st.markdown(
            """
            1. **Project Summary** — Scope, leads, start & deadline schedules
            2. **Requirements** — Traceability matrix & acceptance criteria
            3. **Tasks** — Activity assignments, progress %, due dates
            4. **Deliverables** — Documentation versions & review status
            5. **Quality Checks** — Comprehensive 12-rule audit log
            6. **Issues** — Technical blockers & corrective actions
            7. **Activity Log** — Historical audit trail
            """
        )

        excel_bytes = reports.generate_excel_bytes(project_id=current_project_id)
        report_fn = f"Engineering_Project_QA_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        st.download_button(
            label="📥 Download Full Excel Workbook (.xlsx)",
            data=excel_bytes,
            file_name=report_fn,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
        )

    with r_col2:
        st.markdown("##### 📄 Individual Table CSV Exports")
        csv_table = st.selectbox(
            "Select Table to Export",
            options=["projects", "requirements", "tasks", "deliverables", "quality_checks", "issues", "activity_log"],
            key="csv_tbl_sel",
        )
        csv_data = reports.export_table_csv(csv_table, project_id=current_project_id)
        if csv_data:
            st.download_button(
                label=f"📥 Download {csv_table}.csv",
                data=csv_data.encode("utf-8"),
                file_name=f"{csv_table}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
            )
        else:
            st.info(f"No records available in '{csv_table}'.")

    st.markdown("---")
    st.markdown("##### 🔍 Live Data Table Inspector")
    inspect_tabs = st.tabs(["Projects", "Requirements", "Tasks", "Deliverables", "Quality Checks", "Issues"])
    with inspect_tabs[0]:
        st.dataframe(projects.get_all_projects(), hide_index=True, use_container_width=True)
    with inspect_tabs[1]:
        st.dataframe(requirements.get_requirements(project_id=current_project_id), hide_index=True, use_container_width=True)
    with inspect_tabs[2]:
        st.dataframe(tasks.get_tasks(project_id=current_project_id), hide_index=True, use_container_width=True)
    with inspect_tabs[3]:
        st.dataframe(deliverables.get_deliverables(project_id=current_project_id), hide_index=True, use_container_width=True)
    with inspect_tabs[4]:
        st.dataframe(quality_checks.get_latest_quality_checks(project_id=current_project_id), hide_index=True, use_container_width=True)
    with inspect_tabs[5]:
        st.dataframe(issues.get_issues(project_id=current_project_id), hide_index=True, use_container_width=True)


# =============================================================================
# PAGE 9: SETTINGS & DATA MANAGEMENT
# =============================================================================
elif selected_page == "Settings / Data Management":
    st.markdown('<div class="main-header">System Settings & Data Management</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Manage database storage, seed simulated test datasets, and inspect application logs.</div>', unsafe_allow_html=True)

    s_col1, s_col2 = st.columns(2)

    with s_col1:
        st.markdown("##### 💾 Database Information & Health")
        db_file = Path(DEFAULT_DB_PATH)
        db_exists = db_file.exists()
        db_size_kb = (db_file.stat().st_size / 1024) if db_exists else 0

        st.write(f"- **Database Path:** `{DEFAULT_DB_PATH}`")
        st.write(f"- **Status:** {'🟢 Connected' if db_exists else '🔴 Missing'}")
        st.write(f"- **Database File Size:** {db_size_kb:.2f} KB")

        # Counts
        p_count = fetch_one("SELECT COUNT(*) as cnt FROM projects")["cnt"] if db_exists else 0
        r_count = fetch_one("SELECT COUNT(*) as cnt FROM requirements")["cnt"] if db_exists else 0
        t_count = fetch_one("SELECT COUNT(*) as cnt FROM tasks")["cnt"] if db_exists else 0
        d_count = fetch_one("SELECT COUNT(*) as cnt FROM deliverables")["cnt"] if db_exists else 0
        i_count = fetch_one("SELECT COUNT(*) as cnt FROM issues")["cnt"] if db_exists else 0
        l_count = fetch_one("SELECT COUNT(*) as cnt FROM activity_log")["cnt"] if db_exists else 0

        st.write(f"- **Record Counts:** {p_count} Projects | {r_count} Reqs | {t_count} Tasks | {d_count} Deliverables | {i_count} Issues | {l_count} Logs")

        st.markdown("---")
        st.markdown("##### 🌱 Seed Fictional Engineering Data")
        st.caption("Populates 3 realistic engineering projects, requirements, tasks, deliverables, issues, and triggers QA findings.")
        force_seed = st.checkbox("Overwrite / Append data if projects already exist", key="seed_force_chk")
        if st.button("Load Seed Datasets", type="primary", key="load_seed_btn"):
            with st.spinner("Seeding database..."):
                ok = seed_database(force=force_seed)
                if ok:
                    st.success("Seed data loaded successfully!")
                    st.rerun()
                else:
                    st.warning("Database already contains projects. Check the overwrite box if you wish to add more.")

    with s_col2:
        st.markdown("##### ⚠️ Database Reset Utility")
        st.error("Danger Zone: Resetting drops all tables and clears project history.")
        confirm_reset = st.checkbox("I understand that this will permanently erase all records.", key="reset_db_confirm")
        if st.button("Reset Database to Empty", type="secondary", key="reset_db_btn"):
            if confirm_reset:
                reset_db()
                st.success("Database has been reset to an empty state.")
                st.rerun()
            else:
                st.warning("Please check the confirmation box before proceeding with reset.")

        st.markdown("---")
        st.markdown("##### 📋 Application Runtime Log")
        log_path = Path(LOG_FILE_PATH)
        if log_path.exists():
            log_lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()[-40:]
            st.text_area("Recent Log Entries (logs/app.log)", value="\n".join(log_lines), height=240)
        else:
            st.info("Log file has not been created yet.")
