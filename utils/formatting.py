"""
UI and Data Formatting Helpers
Provides clean display helpers, status badge HTML/markdown, and date formatters.
"""

from datetime import datetime, date
from typing import Optional, Any
from .constants import STATUS_COLORS


def format_date_display(d: Any, fallback: str = "—") -> str:
    """Formats date objects or YYYY-MM-DD strings to human-readable format."""
    if not d:
        return fallback
    if isinstance(d, (datetime, date)):
        return d.strftime("%b %d, %Y")
    try:
        dt = datetime.strptime(str(d).strip()[:10], "%Y-%m-%d")
        return dt.strftime("%b %d, %Y")
    except Exception:
        return str(d)


def format_percentage(val: Any) -> str:
    """Formats an integer or float as a percentage string."""
    try:
        v = float(val)
        return f"{v:.1f}%" if v % 1 != 0 else f"{int(v)}%"
    except (ValueError, TypeError):
        return "0%"


def get_badge_html(text: str, color: Optional[str] = None) -> str:
    """Generates an inline styled HTML badge for Streamlit markdown rendering."""
    bg_color = color or STATUS_COLORS.get(text, "#6c757d")
    return (
        f'<span style="background-color: {bg_color}; color: white; '
        f'padding: 2px 8px; border-radius: 4px; font-weight: 500; '
        f'font-size: 0.85em; display: inline-block;">{text}</span>'
    )


def get_priority_badge_html(priority: str) -> str:
    """Convenience helper for priority badges."""
    return get_badge_html(priority, STATUS_COLORS.get(priority, "#6c757d"))


def get_qa_badge_html(result: str) -> str:
    """Convenience helper for QA result badges."""
    return get_badge_html(result, STATUS_COLORS.get(result, "#6c757d"))
