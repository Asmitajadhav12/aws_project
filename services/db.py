"""MySQL access layer.

Design notes
------------
* One connection per request, opened lazily and closed by the teardown hook.
* Every statement is parameterised with %s placeholders -- never string
  concatenation -- so user input cannot alter the SQL.
* If MySQL is unreachable the layer raises DatabaseUnavailable, which the
  application renders as a friendly "database not ready" page instead of a
  stack trace. This is deliberate: the schema is created manually from
  database/schema.sql, so "database missing" is a normal first-run state.
"""
from __future__ import annotations

import pymysql
from flask import current_app, g
from pymysql.cursors import DictCursor


class DatabaseUnavailable(RuntimeError):
    """Raised when the application cannot reach the configured MySQL server."""


def _connect():
    cfg = current_app.config
    try:
        return pymysql.connect(
            host=cfg["DB_HOST"],
            port=cfg["DB_PORT"],
            user=cfg["DB_USER"],
            password=cfg["DB_PASSWORD"],
            database=cfg["DB_NAME"],
            charset="utf8mb4",
            cursorclass=DictCursor,
            autocommit=False,
            connect_timeout=cfg.get("DB_CONNECT_TIMEOUT", 5),
        )
    except pymysql.err.MySQLError as exc:
        # Log the error class only -- never the credentials or the DSN.
        current_app.logger.error("MySQL connection failed (%s)", type(exc).__name__)
        raise DatabaseUnavailable(
            "Cannot reach the MySQL database. Check that MySQL is running, that "
            "database/schema.sql has been executed, and that the DB_* values in "
            "your .env file are correct."
        ) from exc


def get_connection():
    """Return the request-scoped connection, opening it on first use."""
    conn = g.get("db_conn")
    if conn is None:
        conn = _connect()
        g.db_conn = conn
    return conn


def close_connection(exc=None):
    """Teardown hook: commit on success, roll back on error, always close."""
    conn = g.pop("db_conn", None)
    if conn is None:
        return
    try:
        if exc is None:
            conn.commit()
        else:
            conn.rollback()
    except pymysql.err.MySQLError:
        current_app.logger.warning("Could not finalise the database transaction.")
    finally:
        conn.close()


def query_all(sql, params=None):
    with get_connection().cursor() as cur:
        cur.execute(sql, params or ())
        return cur.fetchall()


def query_one(sql, params=None):
    with get_connection().cursor() as cur:
        cur.execute(sql, params or ())
        return cur.fetchone()


def execute(sql, params=None):
    """Run a single statement and commit. Returns (lastrowid, rowcount)."""
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute(sql, params or ())
        result = (cur.lastrowid, cur.rowcount)
    conn.commit()
    return result


def execute_many(sql, seq_of_params):
    """Run the same statement for many parameter sets in one transaction."""
    conn = get_connection()
    total = 0
    with conn.cursor() as cur:
        cur.executemany(sql, seq_of_params)
        total = cur.rowcount
    conn.commit()
    return total


def scalar(sql, params=None, default=0):
    row = query_one(sql, params)
    if not row:
        return default
    value = next(iter(row.values()))
    return default if value is None else value


def is_available():
    """Cheap health check used by /healthz and the dashboard banner."""
    try:
        get_connection()
        return True
    except DatabaseUnavailable:
        return False


def init_app(app):
    app.teardown_appcontext(close_connection)
