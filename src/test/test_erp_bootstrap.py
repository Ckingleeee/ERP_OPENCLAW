"""Tests for the one-time ERP administrator bootstrap."""

import os
import unittest
from contextlib import contextmanager
from unittest.mock import patch

from erp_backend.bootstrap import bootstrap_admin


class _Cursor:
    def __init__(self, existing_user: bool):
        self.existing_user = existing_user
        self.executed = []

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, sql, params):
        self.executed.append((sql, params))

    def fetchone(self):
        return {"id": 1} if self.existing_user else None


class _Connection:
    def __init__(self, cursor):
        self._cursor = cursor

    def cursor(self):
        return self._cursor


class BootstrapTests(unittest.TestCase):
    def _environment(self, password="strong-password"):
        return patch.dict(
            os.environ,
            {
                "ERP_ADMIN_USERNAME": "yyf",
                "ERP_ADMIN_PASSWORD": password,
                "ERP_ADMIN_DISPLAY_NAME": "YYF",
                "ERP_ADMIN_ROLE": "admin",
                "ERP_ADMIN_DEPARTMENT": "采购部",
            },
            clear=False,
        )

    def test_creates_missing_admin_with_bcrypt_hash(self):
        cursor = _Cursor(existing_user=False)

        @contextmanager
        def transaction():
            yield _Connection(cursor)

        with self._environment(), patch(
            "erp_backend.bootstrap.database.transaction", transaction
        ):
            self.assertTrue(bootstrap_admin())

        insert_params = cursor.executed[-1][1]
        self.assertEqual(insert_params[0], "yyf")
        self.assertTrue(insert_params[1].startswith("$2"))
        self.assertNotEqual(insert_params[1], "strong-password")

    def test_existing_admin_is_not_overwritten(self):
        cursor = _Cursor(existing_user=True)

        @contextmanager
        def transaction():
            yield _Connection(cursor)

        with self._environment(), patch(
            "erp_backend.bootstrap.database.transaction", transaction
        ):
            self.assertFalse(bootstrap_admin())

        self.assertEqual(len(cursor.executed), 1)

    def test_rejects_short_password(self):
        with self._environment(password="short"):
            with self.assertRaisesRegex(RuntimeError, "at least 8"):
                bootstrap_admin()


if __name__ == "__main__":
    unittest.main()
