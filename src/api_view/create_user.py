"""Interactive CLI for creating an ERP login user."""

from __future__ import annotations

import argparse
from getpass import getpass

import bcrypt

from erp_backend import database


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create an ERP Agent login user")
    parser.add_argument("--username", required=True)
    parser.add_argument("--name", required=True, dest="display_name")
    parser.add_argument("--role", default="purchase")
    parser.add_argument("--department", default="信用卡运营部")
    parser.add_argument(
        "--reset-password",
        action="store_true",
        help="Update the existing user's password and profile",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    username = args.username.strip()
    if not username or len(username) > 50:
        raise SystemExit("username must contain 1-50 characters")

    existing = database.fetch_one(
        "SELECT id FROM `user` WHERE username = %s LIMIT 1", (username,)
    )
    if existing and not args.reset_password:
        raise SystemExit(
            "user already exists; pass --reset-password to update it explicitly"
        )

    password = getpass("New password: ")
    confirmation = getpass("Confirm password: ")
    if password != confirmation:
        raise SystemExit("passwords do not match")
    if len(password) < 10:
        raise SystemExit("password must contain at least 10 characters")
    if len(password.encode("utf-8")) > 72:
        raise SystemExit("password must not exceed 72 UTF-8 bytes")

    password_hash = bcrypt.hashpw(
        password.encode("utf-8"), bcrypt.gensalt(rounds=12)
    ).decode("utf-8")

    if existing:
        with database.transaction() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE `user`
                    SET password = %s, real_name = %s, role = %s,
                        department = %s, status = 1, deleted = 0
                    WHERE username = %s
                    """,
                    (
                        password_hash,
                        args.display_name,
                        args.role,
                        args.department,
                        username,
                    ),
                )
    else:
        with database.transaction() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO `user` (
                        username, password, real_name, role, department,
                        status, deleted
                    ) VALUES (%s, %s, %s, %s, %s, 1, 0)
                    """,
                    (
                        username,
                        password_hash,
                        args.display_name,
                        args.role,
                        args.department,
                    ),
                )

    print(f"User '{username}' is ready.")


if __name__ == "__main__":
    main()
