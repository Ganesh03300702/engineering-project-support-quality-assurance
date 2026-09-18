"""
Seed Data Generator Module
Populates realistic fictional engineering projects, requirements, tasks, deliverables,
and issues. Includes intentional QA test cases (overdue dates, clarification needs,
unassigned tasks) to demonstrate the automated Quality Assurance audit engine.
"""

from datetime import date, timedelta
from pathlib import Path
from typing import Optional, Union

from config import logger
from database import fetch_one, log_activity, init_db
from modules.projects import create_project, get_all_projects
from modules.requirements import create_requirement
from modules.tasks import create_task
from modules.deliverables import create_deliverable
from modules.issues import create_issue
from modules.quality_checks import run_all_quality_checks


def seed_database(db_path: Optional[Union[str, Path]] = None, force: bool = False) -> bool:
    """Seeds the database with realistic engineering projects and traceability records."""
    init_db(db_path)

    existing = get_all_projects(db_path=db_path)
    if existing and not force:
        logger.info(f"Database already contains {len(existing)} projects. Skipping seed data.")
        return False

    today = date.today()
    past_10 = (today - timedelta(days=10)).isoformat()
    past_3 = (today - timedelta(days=3)).isoformat()
    future_15 = (today + timedelta(days=15)).isoformat()
    future_30 = (today + timedelta(days=30)).isoformat()
    future_60 = (today + timedelta(days=60)).isoformat()
    future_90 = (today + timedelta(days=90)).isoformat()

    logger.info("Seeding engineering project data...")

    # 1. Projects
    p1_id = create_project({
        "project_code": "PRJ-INS-01",
        "project_name": "Industrial Equipment Inspection Support",
        "project_type": "Equipment Inspection",
        "description": "Comprehensive engineering support and quality verification for heavy industrial rotating machinery.",
        "stakeholder": "Plant Operations Division",
        "team_lead": "Elena Rostova",
        "start_date": past_10,
        "deadline": future_60,
        "priority": "High",
        "status": "Active",
    }, db_path=db_path)

    p2_id = create_project({
        "project_code": "PRJ-DOC-02",
        "project_name": "Engineering Documentation Standardization",
        "project_type": "Documentation Standardization",
        "description": "Consolidation, cross-referencing, and QA review of technical standard operating procedures and CAD drawings.",
        "stakeholder": "Engineering Quality Directorate",
        "team_lead": "Marcus Vance",
        "start_date": past_10,
        "deadline": future_30,
        "priority": "Medium",
        "status": "Active",
    }, db_path=db_path)

    p3_id = create_project({
        "project_code": "PRJ-QAR-03",
        "project_name": "Component Inventory Quality Review",
        "project_type": "Component Quality Review",
        "description": "Tolerance audit, non-destructive testing verification, and supplier defect tracking for alloy fasteners.",
        "stakeholder": "Supply Chain & Quality Control",
        "team_lead": "Sarah Chen",
        "start_date": past_3,
        "deadline": future_90,
        "priority": "Critical",
        "status": "Active",
    }, db_path=db_path)

    # 2. Requirements
    r1_id = create_requirement({
        "project_id": p1_id,
        "requirement_code": "REQ-INS-101",
        "description": "Vibration sensor calibration must comply with ISO 10816-3 mechanical vibration standards.",
        "acceptance_criteria": "Calibration certificates must be verified with error margin within +/- 0.5% RMS across 10Hz-1000Hz.",
        "priority": "High",
        "status": "Approved",
        "owner": "David Kim",
        "due_date": future_15,
    }, db_path=db_path)

    r2_id = create_requirement({
        "project_id": p1_id,
        "requirement_code": "REQ-INS-102",
        "description": "Acoustic emission testing procedures for bearing wear detection under dynamic load.",
        "acceptance_criteria": "",  # Triggers QA check Rule 12 (missing acceptance criteria)
        "priority": "Medium",
        "status": "Approved",
        "clarification_question": "Does the client specify resonant frequency band thresholds for high-speed roller bearings?",
        "owner": "Elena Rostova",
        "due_date": future_30,
    }, db_path=db_path)

    r3_id = create_requirement({
        "project_id": p2_id,
        "requirement_code": "REQ-DOC-201",
        "description": "Standard operating procedure templates must be unified across mechanical and electrical divisions.",
        "acceptance_criteria": "Single unified document format with revision history and sign-off blocks.",
        "priority": "High",
        "status": "Implemented",
        "owner": "Marcus Vance",
        "due_date": past_3,
    }, db_path=db_path)

    r4_id = create_requirement({
        "project_id": p2_id,
        "requirement_code": "REQ-DOC-202",
        "description": "Automated CAD metadata indexing for legacy DWG and STEP engineering files.",
        "acceptance_criteria": "Index file containing part number, author, revision date, and material density.",
        "priority": "Low",
        "status": "Clarification Required",  # Triggers QA Rule 9
        "clarification_question": "Are legacy files prior to 2018 required in the automated indexing scope?",
        "owner": "Aisha Patel",
        "due_date": future_30,
    }, db_path=db_path)

    r5_id = create_requirement({
        "project_id": p3_id,
        "requirement_code": "REQ-QAR-301",
        "description": "Destructive tensile test verification on sample fasteners from batch 2026-B9.",
        "acceptance_criteria": "Ultimate tensile strength must exceed 1200 MPa with elongation at break >= 12%.",
        "priority": "Critical",
        "status": "Open",
        "owner": "Sarah Chen",
        "due_date": future_15,
    }, db_path=db_path)

    # 3. Tasks
    t1_id = create_task({
        "project_id": p1_id,
        "requirement_id": r1_id,
        "task_code": "TSK-INS-501",
        "task_description": "Calibrate tri-axial accelerometers on test bench alpha.",
        "assigned_to": "David Kim",
        "priority": "High",
        "start_date": past_10,
        "due_date": past_3,  # Triggers QA Rule 8 (overdue task)
        "status": "In Progress",
        "progress_percentage": 60,
        "notes": "Bench alpha reference sensor was verified against NIST trace standard.",
    }, db_path=db_path)

    t2_id = create_task({
        "project_id": p1_id,
        "requirement_id": r1_id,
        "task_code": "TSK-INS-502",
        "task_description": "Synthesize calibration coefficients into telemetry processor firmware.",
        "assigned_to": "Carlos Mendez",
        "priority": "Medium",
        "start_date": past_3,
        "due_date": future_15,
        "status": "Not Started",
        "progress_percentage": 0,
        "notes": "Awaiting final sensor calibration logs.",
    }, db_path=db_path)

    t3_id = create_task({
        "project_id": p2_id,
        "requirement_id": r3_id,
        "task_code": "TSK-DOC-503",
        "task_description": "Draft unified SOP template specification and circulate for peer review.",
        "assigned_to": "Marcus Vance",
        "priority": "High",
        "start_date": past_10,
        "due_date": past_3,
        "status": "Completed",
        "progress_percentage": 100,
        "notes": "Reviewed and ratified by mechanical engineering steering committee.",
    }, db_path=db_path)

    t4_id = create_task({
        "project_id": p2_id,
        "requirement_id": r4_id,
        "task_code": "TSK-DOC-504",
        "task_description": "Benchmark CAD metadata parser against 50 legacy drawing files.",
        "assigned_to": "",  # Triggers QA Rule 11 (unassigned active task)
        "priority": "Low",
        "start_date": past_3,
        "due_date": future_30,
        "status": "In Progress",
        "progress_percentage": 35,
        "notes": "Prototype script extracted 92% of metadata tags successfully.",
    }, db_path=db_path)

    t5_id = create_task({
        "project_id": p3_id,
        "requirement_id": r5_id,
        "task_code": "TSK-QAR-505",
        "task_description": "Execute tensile stress-strain test sequence on 10 fastener specimens.",
        "assigned_to": "Sarah Chen",
        "priority": "Critical",
        "start_date": past_3,
        "due_date": future_15,
        "status": "In Progress",
        "progress_percentage": 50,
        "notes": "Tests 1 through 5 completed successfully with average UTS 1240 MPa.",
    }, db_path=db_path)

    # 4. Deliverables
    d1_id = create_deliverable({
        "project_id": p1_id,
        "deliverable_code": "DEL-INS-701",
        "deliverable_name": "Sensor Calibration Certificate Package",
        "deliverable_type": "Inspection Checklist",
        "version": "v1.0",
        "prepared_by": "David Kim",
        "reviewer": "Elena Rostova",
        "planned_date": future_15,
        "submission_date": past_3,
        "review_status": "Approved",
        "file_name": "PRJ-INS-01_CalibCert_v1.0.pdf",
        "comments": "Full compliance demonstrated across all 3 axes.",
    }, db_path=db_path)

    d2_id = create_deliverable({
        "project_id": p1_id,
        "deliverable_code": "DEL-INS-702",
        "deliverable_name": "Bearing Acoustic Emission Test Protocol",
        "deliverable_type": "Test Protocol",
        "version": "v0.9",
        "prepared_by": "David Kim",
        "reviewer": "",  # Triggers QA Rule 5 (submitted with missing reviewer)
        "planned_date": future_30,
        "submission_date": past_3,
        "review_status": "Submitted",
        "file_name": "Bearing_AE_Protocol_v0.9.docx",
        "comments": "Submitted for formal technical review.",
    }, db_path=db_path)

    d3_id = create_deliverable({
        "project_id": p2_id,
        "deliverable_code": "DEL-DOC-703",
        "deliverable_name": "Engineering SOP Master Template Manual",
        "deliverable_type": "SOP Manual",
        "version": "v1.1",
        "prepared_by": "Marcus Vance",
        "reviewer": "Sarah Chen",
        "planned_date": past_3,
        "submission_date": past_3,
        "review_status": "Approved",
        "file_name": "Engineering_SOP_Template_v1.1.pdf",
        "comments": "Ratified and deployed to company document repository.",
    }, db_path=db_path)

    d4_id = create_deliverable({
        "project_id": p3_id,
        "deliverable_code": "DEL-QAR-704",
        "deliverable_name": "Batch 2026-B9 Fastener Tensile Audit Report",
        "deliverable_type": "Audit Report",
        "version": "v1.0",
        "prepared_by": "Sarah Chen",
        "reviewer": "Marcus Vance",
        "planned_date": future_30,
        "submission_date": None,
        "review_status": "Draft",
        "file_name": "",
        "comments": "Compilation in progress pending completion of test batch.",
    }, db_path=db_path)

    # 5. Issues
    i1_id = create_issue({
        "project_id": p1_id,
        "related_requirement_id": r1_id,
        "related_task_id": t1_id,
        "issue_code": "ISS-INS-901",
        "description": "High thermal drift observed on test bench alpha accelerometer channel 3.",
        "severity": "High",
        "owner": "David Kim",
        "status": "In Progress",
        "target_date": future_15,
        "resolution_notes": "Added thermal shield enclosure; verifying drift stability under ambient variation.",
    }, db_path=db_path)

    i2_id = create_issue({
        "project_id": p2_id,
        "related_requirement_id": r4_id,
        "related_task_id": t4_id,
        "issue_code": "ISS-DOC-902",
        "description": "Legacy 2014 DWG files contain unsupported Unicode annotations in German and French.",
        "severity": "Medium",
        "owner": "Aisha Patel",
        "status": "Open",
        "target_date": future_30,
        "resolution_notes": "Evaluating utf-8 and cp1252 fallback encoding in parsing utility.",
    }, db_path=db_path)

    i3_id = create_issue({
        "project_id": p3_id,
        "related_requirement_id": r5_id,
        "related_task_id": t5_id,
        "issue_code": "ISS-QAR-903",
        "description": "Calibration due date on hydraulic tensile test rig expires next week.",
        "severity": "Critical",
        "owner": "Sarah Chen",
        "status": "Resolved",
        "target_date": past_3,
        "resolution_notes": "Third-party metrology lab completed recalibration and issued certificate #MET-8841.",
    }, db_path=db_path)

    # Run QA Engine to populate initial quality_checks table
    run_all_quality_checks(db_path=db_path, save_to_db=True)
    log_activity("SEED_DATA", "SYSTEM", 0, "Seed data generation completed successfully.", db_path=db_path)
    logger.info("Database seeding successfully completed with realistic engineering datasets.")
    return True


if __name__ == "__main__":
    seed_database(force=True)
    print("Database seeded successfully.")
