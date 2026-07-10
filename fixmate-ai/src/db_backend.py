"""Unified database connection wrapper for SQLite and PostgreSQL."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any


class DatabaseCursor:
    """Thin wrapper exposing ``lastrowid``, ``rowcount``, and fetch helpers."""

    def __init__(
        self,
        cursor: Any,
        is_postgres: bool = False,
        is_insert_with_returning: bool = False,
    ) -> None:
        self._cursor = cursor
        self._is_postgres = is_postgres
        self._lastrowid: int | None = None
        self._stored_rows: list[Any] | None = None
        if is_postgres and is_insert_with_returning:
            try:
                row = self._cursor.fetchone()
                if row is not None:
                    self._lastrowid = row["id"] if isinstance(row, dict) else row[0]
            except Exception:
                self._lastrowid = None
        elif not is_postgres:
            # Eagerly consume and close SQLite cursor to avoid
            # "cannot commit transaction - SQL statements in progress"
            # when RETURNING or other active cursors are open.
            self._lastrowid = cursor.lastrowid
            try:
                self._stored_rows = cursor.fetchall()
            except Exception:
                self._stored_rows = []
            cursor.close()

    @property
    def lastrowid(self) -> int | None:
        if self._is_postgres:
            return self._lastrowid
        return self._lastrowid

    @property
    def rowcount(self) -> int:
        if self._is_postgres:
            return self._cursor.rowcount
        return self._cursor.rowcount

    def fetchone(self) -> Any:
        if not self._is_postgres and self._stored_rows is not None:
            return self._stored_rows[0] if self._stored_rows else None
        return self._cursor.fetchone()

    def fetchall(self) -> list[Any]:
        if not self._is_postgres and self._stored_rows is not None:
            return list(self._stored_rows)
        return self._cursor.fetchall()


class DatabaseConnection:
    """Database connection that works with both SQLite and PostgreSQL.

    Mimics the ``sqlite3.Connection`` interface used throughout the codebase
    so that callers can continue to use ``execute()``, ``executemany()``,
    ``executescript()``, and the context-manager protocol without changes.
    """

    def __init__(self, connection: Any, is_postgres: bool = False) -> None:
        self._connection = connection
        self._is_postgres = is_postgres
        self._pg_cursor_obj: Any = None

    @property
    def dialect(self) -> str:
        return "postgresql" if self._is_postgres else "sqlite"

    @property
    def is_postgres(self) -> bool:
        return self._is_postgres

    def execute(self, sql: str, parameters: Any = ()) -> DatabaseCursor:
        if self._is_postgres:
            translated = sql.replace("?", "%s")
            stripped_upper = translated.strip().upper()
            is_insert = stripped_upper.startswith("INSERT")
            has_returning = "RETURNING" in stripped_upper
            cursor = self._ensure_pg_cursor()
            cursor.execute(translated, parameters)
            return DatabaseCursor(
                cursor,
                is_postgres=True,
                is_insert_with_returning=is_insert and has_returning,
            )
        sqlite_cursor = self._connection.execute(sql, parameters)
        return DatabaseCursor(sqlite_cursor, is_postgres=False)

    def executemany(self, sql: str, parameters_list: Any) -> DatabaseCursor:
        if self._is_postgres:
            translated = sql.replace("?", "%s")
            cursor = self._ensure_pg_cursor()
            cursor.executemany(translated, parameters_list)
            return DatabaseCursor(cursor, is_postgres=True)
        sqlite_cursor = self._connection.executemany(sql, parameters_list)
        return DatabaseCursor(sqlite_cursor, is_postgres=False)

    def executescript(self, sql_script: str) -> None:
        if self._is_postgres:
            statements = [s.strip() for s in sql_script.split(";") if s.strip()]
            for stmt in statements:
                self.execute(stmt)
        else:
            self._connection.executescript(sql_script)

    def commit(self) -> None:
        self._connection.commit()

    def close(self) -> None:
        if self._is_postgres and self._pg_cursor_obj is not None:
            try:
                self._pg_cursor_obj.close()
            except Exception:
                pass
            self._pg_cursor_obj = None
        self._connection.close()

    def __enter__(self) -> DatabaseConnection:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool:
        if exc_type is None:
            if self._is_postgres:
                self._connection.commit()
            else:
                self._connection.__exit__(None, None, None)
        else:
            if self._is_postgres:
                self._connection.rollback()
            else:
                self._connection.__exit__(exc_type, exc_val, exc_tb)
        return False

    def _ensure_pg_cursor(self) -> Any:
        if self._pg_cursor_obj is None or self._pg_cursor_obj.closed:
            try:
                import psycopg2.extras

                self._pg_cursor_obj = self._connection.cursor(
                    cursor_factory=psycopg2.extras.RealDictCursor,
                )
            except ImportError:
                self._pg_cursor_obj = self._connection.cursor()
        return self._pg_cursor_obj


def connect_sqlite(database_path: Path) -> DatabaseConnection:
    """Open a SQLite database, creating parent directories as needed."""
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return DatabaseConnection(connection, is_postgres=False)


def connect_sqlite_readonly(database_path: Path) -> DatabaseConnection | None:
    """Open an existing SQLite database in read-only mode."""
    if not database_path.exists():
        return None
    uri = f"{database_path.resolve().as_uri()}?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA query_only = ON")
    return DatabaseConnection(connection, is_postgres=False)


def _redact_exc(exc: Exception, database_url: str) -> Exception:
    """Return a new exception with the raw URL or password replaced by redacted forms."""
    from src.db_url import parse_database_url, redact_database_url

    redacted = redact_database_url(database_url)
    msg = str(exc)
    if database_url in msg:
        msg = msg.replace(database_url, redacted)
    # Also replace a bare password in case the driver includes it in parsed form.
    parsed = parse_database_url(database_url)
    password = parsed.get("password")
    if password and password in msg:
        msg = msg.replace(password, "***")
    return type(exc)(msg)


def connect_postgresql(database_url: str) -> DatabaseConnection:
    """Open a PostgreSQL database from a URL string."""
    try:
        import psycopg2
    except ImportError as exc:
        raise ImportError(
            "psycopg2 is required for PostgreSQL support. "
            "Install it with: pip install psycopg2-binary"
        ) from exc

    try:
        connection = psycopg2.connect(database_url)
    except Exception as exc:
        raise _redact_exc(exc, database_url) from None

    connection.autocommit = False
    return DatabaseConnection(connection, is_postgres=True)


def connect_postgresql_readonly(database_url: str) -> DatabaseConnection:
    """Open a PostgreSQL connection in read-only mode."""
    try:
        import psycopg2
    except ImportError as exc:
        raise ImportError(
            "psycopg2 is required for PostgreSQL support. "
            "Install it with: pip install psycopg2-binary"
        ) from exc

    try:
        connection = psycopg2.connect(database_url)
    except Exception as exc:
        raise _redact_exc(exc, database_url) from None

    connection.autocommit = False
    dc = DatabaseConnection(connection, is_postgres=True)
    cursor = dc._ensure_pg_cursor()
    cursor.execute("SET TRANSACTION READ ONLY")
    return dc
