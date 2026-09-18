"""
Reporting Module
Generates styled multi-sheet Excel workbooks and CSV exports using Pandas and openpyxl.
"""

from datetime import datetime
import io
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
import pandas as pd

from config import EXPORTS_DIR, logger
from database import fetch_all


def export_table_csv(
    table_name: str,
    project_id: Optional[int] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> str:
    """Exports any database table to CSV string format."""
    allowed_tables = ["projects", "requirements", "tasks", "deliverables", "quality_checks", "issues", "activity_log"]
    if table_name not in allowed_tables:
        raise ValueError(f"Invalid table name '{table_name}'.")

    sql = f"SELECT * FROM {table_name}"
    params = []
    if project_id and table_name != "activity_log":
        if table_name == "projects":
            sql += " WHERE project_id = ?"
        else:
            sql += " WHERE project_id = ? OR project_id IS NULL"
        params.append(project_id)

    rows = fetch_all(sql, params, db_path=db_path)
    if not rows:
        return ""
    df = pd.DataFrame(rows)
    return df.to_csv(index=False)

def generate_excel_report(
    project_id: Optional[int] = None,
    output_path: Optional[Union[str, Path]] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> Path:
    """
    Generates a professionally styled 7-sheet Excel workbook.
    Handles empty tables gracefully.
    """
    wb = openpyxl.Workbook()
    # Remove default sheet
    wb.remove(wb.active)

    # Styling definitions
    header_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    cell_font = Font(name="Calibri", size=10)
    thin_side = Side(border_style="thin", color="D9D9D9")
    border = Border(left=thin_side, right=thin_side, top=thin_side, bottom=thin_side)
    alt_fill = PatternFill(start_color="F2F5F9", end_color="F2F5F9", fill_type="solid")

    sheet_configs = [
        ("Project Summary", "projects", "SELECT * FROM projects" + (f" WHERE project_id = {project_id}" if project_id else "")),
        ("Requirements", "requirements", "SELECT * FROM requirements" + (f" WHERE project_id = {project_id}" if project_id else "")),
        ("Tasks", "tasks", "SELECT * FROM tasks" + (f" WHERE project_id = {project_id}" if project_id else "")),
        ("Deliverables", "deliverables", "SELECT * FROM deliverables" + (f" WHERE project_id = {project_id}" if project_id else "")),
        ("Quality Checks", "quality_checks", "SELECT * FROM quality_checks" + (f" WHERE project_id = {project_id} OR project_id IS NULL" if project_id else "")),
        ("Issues", "issues", "SELECT * FROM issues" + (f" WHERE project_id = {project_id}" if project_id else "")),
        ("Activity Log", "activity_log", "SELECT * FROM activity_log ORDER BY log_id DESC"),
    ]

    for sheet_title, table_name, query in sheet_configs:
        ws = wb.create_sheet(title=sheet_title)
        rows = fetch_all(query, db_path=db_path)

        if rows:
            df = pd.DataFrame(rows)
            headers = [col.replace("_", " ").title() for col in df.columns]
            ws.append(headers)

            for row_idx, row_data in enumerate(df.values, start=2):
                ws.append([str(v) if v is not None else "" for v in row_data])
        else:
            # Table is empty - fetch columns from schema pragma
            col_info = fetch_all(f"PRAGMA table_info({table_name});", db_path=db_path)
            col_names = [c["name"].replace("_", " ").title() for c in col_info] if col_info else ["Notice"]
            ws.append(col_names)
            ws.append(["No records recorded in database" if i == 0 else "" for i in range(len(col_names))])

        # Style header row
        for col_idx in range(1, ws.max_column + 1):
            cell = ws.cell(row=1, column=col_idx)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center")

        # Style data rows & auto-fit columns
        for row in range(2, ws.max_row + 1):
            is_alt = (row % 2 == 0)
            for col in range(1, ws.max_column + 1):
                c = ws.cell(row=row, column=col)
                c.font = cell_font
                c.border = border
                if is_alt:
                    c.fill = alt_fill

        # Auto-fit column widths
        for col in ws.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                val = str(cell.value or "")
                if len(val) > max_len:
                    max_len = len(val)
            ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

        # Freeze header row and add auto-filter
        ws.freeze_panes = "A2"
        if ws.max_row > 1 and ws.max_column > 0:
            ws.auto_filter.ref = f"A1:{get_column_letter(ws.max_column)}{ws.max_row}"

    if output_path:
        target_file = Path(output_path)
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        target_file = EXPORTS_DIR / f"Engineering_Project_QA_Report_{timestamp}.xlsx"

    target_file.parent.mkdir(parents=True, exist_ok=True)
    wb.save(target_file)
    logger.info(f"Generated comprehensive report at {target_file}")
    return target_file


def generate_excel_bytes(
    project_id: Optional[int] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> bytes:
    """Generates Excel report and returns raw bytes for Streamlit st.download_button."""
    temp_buf = io.BytesIO()
    # Save using generate_excel_report or write directly to buffer
    wb_path = generate_excel_report(project_id=project_id, db_path=db_path)
    data = wb_path.read_bytes()
    return data
