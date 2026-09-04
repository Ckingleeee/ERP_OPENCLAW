"""Regression tests for LangGraph control-flow exceptions in tool middleware."""

from __future__ import annotations

import json
import unittest
from types import SimpleNamespace

from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage
from langchain_core.tools import tool
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.errors import GraphInterrupt
from langgraph.types import Command, Interrupt

from agent.middlewares.tool_error import ToolErrorMiddleware


class _ScriptedModel(GenericFakeChatModel):
    def bind_tools(self, tools, **kwargs):
        return self


def _request():
    return SimpleNamespace(tool_call={"id": "task-1", "name": "task"})


class ToolErrorMiddlewareTests(unittest.IsolatedAsyncioTestCase):
    def test_sync_graph_interrupt_is_propagated(self):
        middleware = ToolErrorMiddleware()
        graph_interrupt = GraphInterrupt(
            [Interrupt(value={"action_requests": []}, id="interrupt-1")]
        )

        def handler(_request):
            raise graph_interrupt

        with self.assertRaises(GraphInterrupt) as raised:
            middleware.wrap_tool_call(_request(), handler)

        self.assertIs(raised.exception, graph_interrupt)

    async def test_async_graph_interrupt_is_propagated(self):
        middleware = ToolErrorMiddleware()
        graph_interrupt = GraphInterrupt(
            [Interrupt(value={"action_requests": []}, id="interrupt-2")]
        )

        async def handler(_request):
            raise graph_interrupt

        with self.assertRaises(GraphInterrupt) as raised:
            await middleware.awrap_tool_call(_request(), handler)

        self.assertIs(raised.exception, graph_interrupt)

    def test_regular_tool_exception_is_still_converted_to_error_message(self):
        middleware = ToolErrorMiddleware()

        def handler(_request):
            raise RuntimeError("upstream failed")

        result = middleware.wrap_tool_call(_request(), handler)
        payload = json.loads(result.content)

        self.assertEqual(result.status, "error")
        self.assertEqual(result.tool_call_id, "task-1")
        self.assertEqual(payload["error_type"], "RuntimeError")
        self.assertEqual(payload["name"], "task")


class ApprovalResumeRegressionTests(unittest.TestCase):
    def _build_agent(self):
        created = []

        @tool
        def replenishment_create() -> str:
            """Create one replenishment order."""
            created.append("created")
            return "created"

        inner_model = _ScriptedModel(
            messages=iter(
                [
                    AIMessage(
                        content="",
                        tool_calls=[
                            {
                                "name": "replenishment_create",
                                "args": {},
                                "id": "create-1",
                            }
                        ],
                    ),
                    AIMessage(content="subagent done"),
                ]
            )
        )
        subagent = create_agent(
            model=inner_model,
            tools=[replenishment_create],
            middleware=[
                HumanInTheLoopMiddleware(
                    interrupt_on={
                        "replenishment_create": {
                            "allowed_decisions": ["approve", "reject"]
                        }
                    }
                )
            ],
        )

        @tool
        def task() -> str:
            """Delegate replenishment creation to a subagent."""
            result = subagent.invoke(
                {"messages": [{"role": "user", "content": "create it"}]}
            )
            return result["messages"][-1].text

        outer_model = _ScriptedModel(
            messages=iter(
                [
                    AIMessage(
                        content="",
                        tool_calls=[{"name": "task", "args": {}, "id": "task-1"}],
                    ),
                    AIMessage(content="main agent done"),
                ]
            )
        )
        agent = create_agent(
            model=outer_model,
            tools=[task],
            middleware=[ToolErrorMiddleware()],
            checkpointer=InMemorySaver(),
        )
        return agent, created

    def test_approve_resumes_nested_subagent_and_creates_once(self):
        agent, created = self._build_agent()
        config = {"configurable": {"thread_id": "approve-thread"}}

        interrupted = agent.invoke(
            {"messages": [{"role": "user", "content": "create order"}]}, config
        )
        self.assertIn("__interrupt__", interrupted)
        self.assertEqual(created, [])

        result = agent.invoke(
            Command(resume={"decisions": [{"type": "approve"}]}), config
        )

        self.assertNotIn("__interrupt__", result)
        self.assertEqual(created, ["created"])
        self.assertEqual(result["messages"][-1].text, "main agent done")

    def test_reject_resumes_nested_subagent_without_creating(self):
        agent, created = self._build_agent()
        config = {"configurable": {"thread_id": "reject-thread"}}

        interrupted = agent.invoke(
            {"messages": [{"role": "user", "content": "create order"}]}, config
        )
        self.assertIn("__interrupt__", interrupted)

        result = agent.invoke(
            Command(resume={"decisions": [{"type": "reject"}]}), config
        )

        self.assertNotIn("__interrupt__", result)
        self.assertEqual(created, [])
        self.assertEqual(result["messages"][-1].text, "main agent done")


if __name__ == "__main__":
    unittest.main()
