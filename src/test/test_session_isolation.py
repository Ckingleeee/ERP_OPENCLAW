"""Unit tests for authenticated conversation ownership."""

import unittest
from unittest.mock import MagicMock, patch

try:
    from api_view.agent_loader import agent_loader
except ModuleNotFoundError as exc:
    if exc.name != "pymongo":
        raise
    agent_loader = None


@unittest.skipIf(agent_loader is None, "pymongo is not installed in this environment")
class SessionIsolationTests(unittest.TestCase):
    def test_existing_session_cannot_be_claimed_by_another_user(self):
        collection = MagicMock()
        collection.find_one.return_value = {
            "thread_id": "thread-1",
            "user_id": "another-user",
        }

        with patch.object(
            agent_loader, "_session_collection", return_value=collection
        ):
            with self.assertRaises(PermissionError):
                agent_loader.claim_session("thread-1", "yyf", "yyf")

        collection.insert_one.assert_not_called()

    def test_ownership_query_always_includes_user_id(self):
        collection = MagicMock()
        collection.count_documents.return_value = 1

        with patch.object(
            agent_loader, "_session_collection", return_value=collection
        ):
            owned = agent_loader.user_owns_session("thread-1", "yyf")

        self.assertTrue(owned)
        collection.count_documents.assert_called_once_with(
            {"thread_id": "thread-1", "user_id": "yyf"}, limit=1
        )

    def test_history_query_is_scoped_to_user(self):
        collection = MagicMock()
        collection.find.return_value.sort.return_value = []

        with patch.object(
            agent_loader, "_session_collection", return_value=collection
        ):
            result = agent_loader.get_user_sessions("yyf")

        self.assertEqual(result, [])
        collection.find.assert_called_once_with({"user_id": "yyf"})


if __name__ == "__main__":
    unittest.main()
