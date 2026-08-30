"""Create the first ERP login account for a fresh deployment."""

from __future__ import annotations

import os

import bcrypt

from erp_backend import database


def _required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} must be configured")
    return value


def bootstrap_admin() -> bool:
    """Create the configured administrator when it does not already exist."""
    username = _required_env("ERP_ADMIN_USERNAME")
    password = _required_env("ERP_ADMIN_PASSWORD")
    if len(password) < 8:
        raise RuntimeError("ERP_ADMIN_PASSWORD must contain at least 8 characters")

    real_name = os.getenv("ERP_ADMIN_DISPLAY_NAME", username).strip() or username
    role = os.getenv("ERP_ADMIN_ROLE", "admin").strip() or "admin"
    department = os.getenv("ERP_ADMIN_DEPARTMENT", "采购部").strip() or "采购部"

    with database.transaction() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT id FROM `user` WHERE username = %s LIMIT 1",
                (username,),
            )
            if cursor.fetchone() is not None:
                print(f"ERP administrator already exists: {username}")
                return False

            password_hash = bcrypt.hashpw(
                password.encode("utf-8"), bcrypt.gensalt()
            ).decode("utf-8")
            cursor.execute(
                """
                INSERT INTO `user` (
                    username, password, real_name, role, department, status, deleted
                ) VALUES (%s, %s, %s, %s, %s, 1, 0)
                """,
                (username, password_hash, real_name, role, department),
            )

    print(f"Created ERP administrator: {username}")
    return True


def main() -> None:
    database.ping()
    bootstrap_admin()


if __name__ == "__main__":
    main()
