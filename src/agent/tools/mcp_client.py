"""
MCP 工具客户端。

在 Agent 启动时连接所有 MCP Server，获取全部 MCP 工具，
并按分组筛选后分配给不同的子 Agent。

使用方式:
    from agent.tools.mcp_client import load_mcp_tools

    all_tools, analyst_tools, replenishment_tools, chart_tools = await load_mcp_tools()
"""

import os
from typing import List, Tuple

from langchain_mcp_adapters.client import MultiServerMCPClient

# MCP Server 连接配置。容器环境中使用服务名，本地开发仍保留回环地址。
ERP_MCP_URL = os.getenv("ERP_MCP_URL", "http://127.0.0.1:8000/mcp").strip()
MCP_SERVER_CONFIG = {
    "erp-api": {
        "url": ERP_MCP_URL,
        "transport": "streamable_http",
    },
}

ANALYSIS_MCP_URL = os.getenv("ANALYSIS_MCP_URL", "").strip()
if ANALYSIS_MCP_URL:
    MCP_SERVER_CONFIG["analysis"] = {
        "url": ANALYSIS_MCP_URL,
        "transport": "streamable_http",
    }

# 工具分组规则（前缀匹配）
ANALYST_TOOL_PREFIXES = ("provider_", "resource_", "quota_")
REPLENISHMENT_TOOL_PREFIXES = ("replenishment_",)
CHART_TOOL_PREFIXES = ("generate_",)  # 魔塔社区 MCP 可视化+工具（26 图表/地图/图表 + 1 spreadsheet）


async def load_mcp_tools(
    server_config: dict | None = None,
) -> Tuple[List, List, List, List]:
    """
    连接到所有 MCP Server，加载全部工具并分组。

    Args:
        server_config: MCP Server 连接配置，默认使用 MCP_SERVER_CONFIG。

    Returns:
        (all_tools, analyst_tools, replenishment_tools, chart_tools) 四元组
        - all_tools: 全部 MCP 工具列表（ERP + 图表）
        - analyst_tools: 权益服务商 + 营销资源 + 配额预警工具
        - replenishment_tools: 补充单创建 + 更新 + 历史搜索工具
        - chart_tools: 图表/地图/可视化生成工具（来自魔塔社区 MCP Server，27 种）
    """
    if server_config is None:
        server_config = MCP_SERVER_CONFIG

    print("[INFO] 正在连接 MCP Server...")
    mcp_client = MultiServerMCPClient(server_config)

    # 从 ERP MCP Server 获取业务工具
    erp_tools = await mcp_client.get_tools(server_name="erp-api")
    print(f"[INFO] 已从 ERP MCP Server 加载 {len(erp_tools)} 个工具")

    # 外部分析 MCP 是可选能力，连接失败不应阻止 ERP Web 服务启动。
    analysis_tools = []
    if "analysis" in server_config:
        try:
            analysis_tools = await mcp_client.get_tools(server_name="analysis")
            print(
                f"[INFO] 已从外部分析 MCP Server 加载 "
                f"{len(analysis_tools)} 个工具"
            )
        except Exception as exc:
            print(f"[WARNING] 外部分析 MCP Server 不可用，已跳过: {exc}")
    else:
        print("[INFO] 未配置 ANALYSIS_MCP_URL，已跳过外部分析工具")

    # 合并全部工具
    all_tools = list(erp_tools) + list(analysis_tools)

    # 按前缀分组：业务工具
    analyst_tools = [
        t for t in erp_tools
        if t.name.startswith(ANALYST_TOOL_PREFIXES)
    ]
    replenishment_tools = [
        t for t in erp_tools
        if t.name.startswith(REPLENISHMENT_TOOL_PREFIXES)
    ]

    # 图表工具（来自魔塔社区）
    chart_tools = [
        t for t in analysis_tools
        if t.name.startswith(CHART_TOOL_PREFIXES)
    ]

    print(
        f"[INFO] 工具分组完成: "
        f"分析类 {len(analyst_tools)} 个, "
        f"补充单类 {len(replenishment_tools)} 个, "
        f"图表类 {len(chart_tools)} 个"
    )

    return all_tools, analyst_tools, replenishment_tools, chart_tools
