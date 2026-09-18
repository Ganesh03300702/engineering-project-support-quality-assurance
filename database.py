"""
Database Management and Helper Layer
Encapsulates SQLite connection management, transactions, query execution,
and schema initialization with strict foreign key enforcement.
"""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generator, List, Optional, Tuple, Union

from config import DEFAULT_DB_PATH, SCHEMA_PATH, logger


def get_connection(db_path: Optional[Union[str, Path]] = None) -> sqlite3.Connection:
    """
    Creates and returns a SQLite connection with foreign key support enabled
    and row factory configured to return sqlite3.Row objects.
    """
    path = Path(db_path) if db_path else DEFAULT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(str(path), timeout=15.0)
    conn.row_factory = sqlite3.Row
    # Enforce foreign key constraints
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


@contextmanager
def db_transaction(db_path: Optional[Union[str, Path]] = None) -> Generator[sqlite3.Connection, None, None]:
    """
    Context manager providing a transactional database connection.
    Automatically commits if block succeeds, rolls back if an exception occurs.
    """
    conn = get_connection(db_path)
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Transaction failed, rolled back: {e}")
        raise
    finally:
        conn.close()


def execute_query(
    sql: str,
    params: Union[Tuple, List, dict] = (),
    db_path: Optional[Union[str, Path]] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> int:
    """
    Executes a parameterized INSERT, UPDATE, or DELETE query.
    Returns the lastrowid for INSERTs or rowcount for updates/deletes.
    """
    if conn:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        return cursor.lastrowid if cursor.lastrowid else cursor.rowcount

    with db_transaction(db_path) as transaction_conn:
        cursor = transaction_conn.cursor()
        cursor.execute(sql, params)
        return cursor.lastrowid if cursor.lastrowid else cursor.rowcount


def fetch_all(
    sql: str,
    params: Union[Tuple, List, dict] = (),
    db_path: Optional[Union[str, Path]] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> List[dict]:
    """Executes a parameterized SELECT query and returns all matching rows as dictionaries."""
    should_close = False
    active_conn = conn
    if active_conn is None:
        active_conn = get_connection(db_path)
        should_close = True
        
    try:
        cursor = active_conn.cursor()
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Error executing fetch_all query: {sql} | Error: {e}")
        raise
    finally:
        if should_close and active_conn:
            active_conn.close()


def fetch_one(
    sql: str,
    params: Union[Tuple, List, dict] = (),
    db_path: Optional[Union[str, Path]] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> Optional[dict]:
    """Executes a parameterized SELECT query and returns the first row as a dictionary or None."""
    should_close = False
    active_conn = conn
    if active_conn is None:
        active_conn = get_connection(db_path)
        should_close = True
        
    try:
        cursor = active_conn.cursor()
        cursor.execute(sql, params)
        row = cursor.fetchone()
        return dict(row) if row else None
    except Exception as e:
        logger.error(f"Error executing fetch_one query: {sql} | Error: {e}")
        raise
    finally:
        if should_close and active_conn:
            active_conn.close()


def init_db(db_path: Optional[Union[str, Path]] = None) -> None:
    """Initializes the database schema if not already present."""
    path = Path(db_path) if db_path else DEFAULT_DB_PATH
    logger.info(f"Initializing database at: {path}")
    
    if not SCHEMA_PATH.exists():
        err_msg = f"Schema file not found at {SCHEMA_PATH}"
        logger.critical(err_msg)
        raise FileNotFoundError(err_msg)
        
    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
    
    conn = get_connection(path)
    try:
        conn.executescript(schema_sql)
        conn.commit()
        logger.info("Database schema initialized successfully.")
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to initialize schema: {e}")
        raise
    finally:
        conn.close()


def log_activity(
    action_type: str,
    entity_type: str,
    entity_id: Optional[int],
    description: str,
    db_path: Optional[Union[str, Path]] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> None:
    """Records an entry into the activity_log table for auditability and project history."""
    sql = """
        INSERT INTO activity_log (action_type, entity_type, entity_id, description, created_at)
        VALUES (?, ?, ?, ?, datetime('now', 'localtime'))
    """
    try:
        execute_query(sql, (action_type, entity_type, entity_id, description), db_path=db_path, conn=conn)
        logger.debug(f"Activity logged: [{action_type}] {entity_type} {entity_id} - {description}")
    except Exception as e:
        logger.error(f"Failed to record activity log: {e}")


def reset_db(db_path: Optional[Union[str, Path]] = None) -> None:
    """
    Safely resets all application tables and reapplies the schema.
    Used for maintenance, testing, and system resets.
    """
    tables = [
        "activity_log",
        "quality_checks",
        "issues",
        "deliverables",
        "tasks",
        "requirements",
        "projects",
    ]
    
    with db_transaction(db_path) as conn:
        # Disable FKs temporarily during drop
        conn.execute("PRAGMA foreign_keys = OFF;")
        for table in tables:
            conn.execute(f"DROP TABLE IF EXISTS {table};")
        conn.execute("PRAGMA foreign_keys = ON;")
        
    init_db(db_path)
    log_activity("RESET_DB", "SYSTEM", 0, "System database reset performed.", db_path=db_path)
    logger.warning("Database has been reset to empty schema.")
