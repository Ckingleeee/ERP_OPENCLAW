"""Small PyMySQL database layer for the local ERP API."""

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from erp_backend.config import settings

try:
    import pymysql
    from pymysql.cursors import DictCursor
except ModuleNotFoundError:  # Allows importing the app before optional deps are installed.
    pymysql = None
    DictCursor = None


def _require_driver() -> None:
    if pymysql is None:
        raise RuntimeError(
            "PyMySQL is not installed. Run: pip install -r requirements-erp.txt"
        )


def connect(*, autocommit: bool = True):
    """Create a UTF-8 MySQL connection using the configured database."""
    _require_driver()
    return pymysql.connect(
        host=settings.db_host,
        port=settings.db_port,
        user=settings.db_user,
        password=settings.db_password,
        database=settings.db_name,
        charset="utf8mb4",
        cursorclass=DictCursor,
        connect_timeout=settings.db_connect_timeout,
        autocommit=autocommit,
    )


@contextmanager
def transaction() -> Iterator[Any]:
    """Provide a connection that commits on success and rolls back on error."""
    connection = connect(autocommit=False)
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def fetch_all(sql: str, params: tuple | list | None = None) -> list[dict]:
    connection = connect()
    try:
        with connection.cursor() as cursor:
            cursor.execute(sql, params or ())
            return list(cursor.fetchall())
    finally:
        connection.close()


def fetch_one(sql: str, params: tuple | list | None = None) -> dict | None:
    connection = connect()
    try:
        with connection.cursor() as cursor:
            cursor.execute(sql, params or ())
            return cursor.fetchone()
    finally:
        connection.close()


def ping() -> None:
    connection = connect()
    try:
        connection.ping(reconnect=False)
    finally:
        connection.close()

