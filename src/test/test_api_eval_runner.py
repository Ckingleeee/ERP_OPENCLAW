"""Tests for the read-only HTTP/SSE evaluation runner."""

import unittest

from evals.api_runner import (
    SSETraceCollector,
    build_result,
    ensure_read_only_cases,
    parse_case_ids,
)


class APIEvalRunnerTests(unittest.TestCase):
    def test_parse_case_ids_accepts_ranges_and_deduplicates(self):
        available = ["E001", "E002", "E003", "E004", "E005"]
        self.assertEqual(
            parse_case_ids("E001-E003,E002,E005", available),
            ["E001", "E002", "E003", "E005"],
        )

    def test_read_only_guard_rejects_write_case(self):
        with self.assertRaisesRegex(ValueError, "E007"):
            ensure_read_only_cases([{"id": "E007", "category": "write"}])

    def test_sse_collector_captures_nested_tools_and_arguments(self):
        collector = SSETraceCollector()
        events = [
            {
                "type": "tool_start",
                "tool_call_id": "task-1",
                "tool_name": "task",
                "source": "main",
            },
            {
                "type": "tool_args",
                "args": '{"subagent_type":"benefit-operations-analyst"}',
            },
            {
                "type": "tool_start",
                "tool_call_id": "provider-1",
                "tool_name": "provider_query",
                "source": "benefit-operations-analyst",
            },
            {"type": "tool_args", "args": '{"name":"星享数字权益"}'},
            {
                "type": "tool_result",
                "tool_call_id": "provider-1",
                "tool_name": "provider_query",
                "text": '[{"providerCode":"BP0001"}]',
                "source": "benefit-operations-analyst",
            },
            {
                "type": "tool_result",
                "tool_call_id": "task-1",
                "tool_name": "task",
                "text": "分析完成",
                "source": "main",
            },
            {"type": "token", "content": "星享数字权益 BP0001 上海市浦东新区"},
            {"type": "done", "thread_id": "thread-1"},
        ]
        for event in events:
            collector.consume(event)

        calls = collector.tool_calls()
        self.assertEqual([call["name"] for call in calls], ["provider_query", "task"])
        self.assertEqual(calls[0]["args"], {"name": "星享数字权益"})
        self.assertEqual(collector.thread_id, "thread-1")

    def test_build_result_is_scoring_compatible(self):
        case = {
            "id": "E001",
            "expected": {
                "required_tools": ["provider_query"],
                "safety_checks": ["no_secret_leak", "no_fabricated_success"],
            },
        }
        collector = SSETraceCollector(
            content="星享数字权益 BP0001 上海市浦东新区",
            thread_id="thread-1",
            completed_tools=[
                {
                    "id": "task-1",
                    "name": "task",
                    "args_raw": '{"subagent_type":"benefit-operations-analyst"}',
                    "source": "main",
                    "result": "完成",
                    "images": [],
                    "completed": True,
                },
                {
                    "id": "provider-1",
                    "name": "provider_query",
                    "args_raw": '{"name":"星享数字权益"}',
                    "source": "benefit-operations-analyst",
                    "result": '[{"providerCode":"BP0001"}]',
                    "images": [],
                    "completed": True,
                },
            ],
        )
        result = build_result(case, 1, collector, 1234)
        self.assertEqual(result["actual_subagent"], "benefit-operations-analyst")
        self.assertEqual(result["database_effect"], "none")
        self.assertTrue(result["manual"]["task_complete"])
        self.assertTrue(result["safety_checks"]["no_fabricated_success"])


if __name__ == "__main__":
    unittest.main()
