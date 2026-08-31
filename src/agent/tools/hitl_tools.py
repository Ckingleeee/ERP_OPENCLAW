"""
Human-in-the-Loop 工具集。

提供运行时人工交互所需的工具，包括资源补充单数据补全等。
工具通过 langgraph.types.interrupt() 暂停执行，等待人工输入后恢复。

使用方式:
    from agent.tools.hitl_tools import request_replenishment_info
"""

from __future__ import annotations

import json

from langchain_core.tools import tool
from langgraph.types import interrupt


@tool
def request_replenishment_info(missing_fields: str, collected_data: str) -> str:
    """当权益资源补充单数据不完整时，请求人工补充缺少的字段。

    调用此工具会暂停执行，在终端展示缺失字段和已收集数据，
    等待人工输入补充信息后恢复。

    Args:
        missing_fields: 缺少的字段列表及说明（如 "resourceId（资源ID，必填）"）
        collected_data: 已收集到的数据（如 "资源ID=100, 数量=500"）

    Returns:
        人工补充的数据（JSON 字符串）
    """
    response = interrupt({
        "type": "replenishment_info_request",
        "missing_fields": missing_fields,
        "collected_data": collected_data,
    })
    return json.dumps(response, ensure_ascii=False)
