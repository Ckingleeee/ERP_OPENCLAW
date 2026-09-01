"""Regression tests for OpenSandbox restart resilience."""
import unittest
from types import SimpleNamespace

from agent.backends.sandbox_resilience import (
    SandboxExecutionUncertainError,
    SandboxUnavailableError,
    classify_sandbox_exception,
    is_successful_probe,
    wait_for_sandbox,
)


class _SequenceBackend:
    def __init__(self, responses):
        self.responses = list(responses)

    def execute(self, command, *, timeout=None):
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class SandboxResilienceTests(unittest.IsolatedAsyncioTestCase):
    def test_probe_requires_zero_exit_code_and_marker(self):
        self.assertTrue(is_successful_probe(
            SimpleNamespace(exit_code=0, output="sandbox-ready")
        ))
        self.assertFalse(is_successful_probe(
            SimpleNamespace(exit_code=1, output="sandbox-ready")
        ))
        self.assertFalse(is_successful_probe(
            SimpleNamespace(exit_code=0, output="unexpected")
        ))

    def test_connection_refused_is_safe_retry(self):
        error = classify_sandbox_exception(
            ConnectionRefusedError("[Errno 111] Connection refused")
        )
        self.assertIsInstance(error, SandboxUnavailableError)
        self.assertTrue(error.retryable)
        self.assertFalse(error.execution_uncertain)

    def test_wrapped_connection_refused_remains_safe_retry(self):
        cause = ConnectionRefusedError("[Errno 111] Connection refused")
        wrapper = RuntimeError("Network connectivity error")
        wrapper.__cause__ = cause
        error = classify_sandbox_exception(wrapper)
        self.assertIsInstance(error, SandboxUnavailableError)

    def test_incomplete_response_is_not_safe_to_replay(self):
        error = classify_sandbox_exception(
            RuntimeError("peer closed connection: incomplete chunked read")
        )
        self.assertIsInstance(error, SandboxExecutionUncertainError)
        self.assertFalse(error.retryable)
        self.assertTrue(error.execution_uncertain)

    async def test_wait_recovers_after_transient_failure(self):
        backend = _SequenceBackend([
            ConnectionRefusedError("connection refused"),
            SimpleNamespace(exit_code=0, output="sandbox-ready"),
        ])
        recovered = await wait_for_sandbox(
            backend,
            timeout_seconds=0.2,
            poll_seconds=0.01,
        )
        self.assertTrue(recovered)

    async def test_nonzero_probe_is_unhealthy(self):
        backend = _SequenceBackend([
            SimpleNamespace(exit_code=1, output="sandbox-ready")
        ])
        recovered = await wait_for_sandbox(backend, timeout_seconds=0)
        self.assertFalse(recovered)


if __name__ == "__main__":
    unittest.main()
