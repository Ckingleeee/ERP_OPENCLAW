"""Tests for public streaming error classification."""
import unittest

from agent.backends.sandbox_resilience import (
    SandboxExecutionUncertainError,
    SandboxUnavailableError,
)
from api_view.runtime_errors import classify_runtime_error


class RuntimeErrorTests(unittest.TestCase):
    def test_sandbox_unavailable_is_retryable(self):
        result = classify_runtime_error(SandboxUnavailableError("connection refused"))
        self.assertEqual(result.code, "SANDBOX_UNAVAILABLE")
        self.assertTrue(result.retryable)
        self.assertNotIn("connection refused", result.message)

    def test_uncertain_execution_is_not_retryable(self):
        result = classify_runtime_error(
            SandboxExecutionUncertainError("incomplete chunked read")
        )
        self.assertEqual(result.code, "SANDBOX_EXECUTION_UNCERTAIN")
        self.assertFalse(result.retryable)
        self.assertIn("避免重复操作", result.message)

    def test_generic_transport_error_has_stable_contract(self):
        result = classify_runtime_error(RuntimeError("network error"))
        self.assertEqual(result.code, "UPSTREAM_UNAVAILABLE")
        self.assertTrue(result.retryable)
        self.assertNotEqual(result.message, "network error")

    def test_unknown_exception_does_not_leak_raw_detail(self):
        result = classify_runtime_error(RuntimeError("secret internal detail"))
        self.assertEqual(result.code, "INTERNAL_ERROR")
        self.assertFalse(result.retryable)
        self.assertNotIn("secret internal detail", result.message)


if __name__ == "__main__":
    unittest.main()
