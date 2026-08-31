"""
MCP 工具全量测试。

测试模式：
  - mcp_client：通过 fastmcp.Client 内存模式直接测试 MCP 服务端（需 ERP 后端运行）
  - agent_client：通过 MultiServerMCPClient 模拟 Agent，经 HTTP 获取工具并调用

运行方式：
  python -m test.test_all_tools
"""

import asyncio
import random
from datetime import date, datetime
from decimal import Decimal

from fastmcp import Client
from langchain_mcp_adapters.client import MultiServerMCPClient

from mcp_server.server_main import mcp

# ============================================================
# 随机测试数据生成
# ============================================================

PROVIDER_NAMES = ["星享数字权益", "云途生活服务", "惠味餐饮科技"]
RESOURCE_NAMES = ["视频会员月卡", "机场贵宾厅权益", "连锁咖啡兑换券"]
CATEGORIES = ["影音会员", "出行权益", "餐饮优惠", "积分礼品", "营销券包"]


def _random_provider_name() -> str:
    return random.choice(PROVIDER_NAMES)


def _random_resource_name() -> str:
    return random.choice(RESOURCE_NAMES)


def _random_category() -> str:
    return random.choice(CATEGORIES)


def _random_provider_id() -> int:
    return random.randint(1, 50)


def _random_resource_id() -> int:
    return random.randint(1, 200)


def _random_quantity() -> int:
    return random.randint(1, 500)


def _random_price() -> Decimal:
    return Decimal(str(round(random.uniform(10.0, 5000.0), 2)))


def _random_status() -> int:
    return random.randint(1, 5)


def _now_iso() -> str:
    """生成当前时间的 ISO 格式字符串：yyyy-MM-ddTHH:mm:ss.SSS"""
    now = datetime.now()
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}"


def _random_replenishment_detail(num_items: int = 2) -> list:
    """生成随机资源补充明细列表（含 subtotal）。"""
    items = []
    for i in range(num_items):
        quantity = _random_quantity()
        unit_price = float(_random_price())
        items.append({
            "resourceId": _random_resource_id(),
            "quantity": quantity,
            "unitCost": unit_price,
            "subtotal": round(quantity * unit_price, 2),
            "remark": f"测试明细-{i+1}",
        })
    return items


# ============================================================
# 1. mcp_client 测试（内存模式，直接调用 MCP 工具）
# ============================================================

async def test_mcp_provider_query():
    """测试 provider_query — 按名称模糊搜索权益服务商。"""
    name = _random_provider_name()
    print(f"\n{'='*60}")
    print(f"[mcp_client] 测试 provider_query: name={name}")
    print(f"{'='*60}")

    async with Client(mcp) as client:
        result = await client.call_tool("provider_query", {"name": name})
        print(f"结果: {result}")
        return result


async def test_mcp_resource_query():
    """测试 resource_query — 分页查询营销资源。"""
    category = _random_category()
    print(f"\n{'='*60}")
    print(f"[mcp_client] 测试 resource_query: current=1, size=5, category={category}")
    print(f"{'='*60}")

    async with Client(mcp) as client:
        result = await client.call_tool("resource_query", {
            "current": 1,
            "size": 5,
            "category": category,
        })
        print(f"结果: {result}")
        return result


async def test_mcp_resource_search():
    """测试 resource_search — 按名称搜索营销资源。"""
    name = _random_resource_name()
    print(f"\n{'='*60}")
    print(f"[mcp_client] 测试 resource_search: name={name}")
    print(f"{'='*60}")

    async with Client(mcp) as client:
        result = await client.call_tool("resource_search", {"name": name})
        print(f"结果: {result}")
        return result


async def test_mcp_resource_by_provider():
    """测试 resource_by_provider — 按服务商 ID 查询营销资源。"""
    provider_id = _random_provider_id()
    print(f"\n{'='*60}")
    print(f"[mcp_client] 测试 resource_by_provider: provider_id={provider_id}")
    print(f"{'='*60}")

    async with Client(mcp) as client:
        result = await client.call_tool("resource_by_provider", {
            "provider_id": provider_id
        })
        print(f"结果: {result}")
        return result


async def test_mcp_replenishment_create():
    """测试 replenishment_create — 创建资源补充单。"""
    replenishment_detail = _random_replenishment_detail(2)
    total_amount = sum(item["subtotal"] for item in replenishment_detail)
    test_data = {
        "replenishmentNumber": f"BR{datetime.now().strftime('%Y%m%d')}{str(random.randint(0, 999)).zfill(3)}",
        "replenishmentTime": _now_iso(),
        "detail": replenishment_detail,
        "totalAmount": round(total_amount, 2),
        "status": _random_status(),
        "remark": "mcp_client 测试资源补充单",
    }
    print(f"\n{'='*60}")
    print("[mcp_client] 测试 replenishment_create")
    print(f"  请求体: {test_data}")
    print(f"{'='*60}")

    async with Client(mcp) as client:
        result = await client.call_tool("replenishment_create", test_data)
        print(f"结果: {result}")
        return result


async def test_mcp_replenishment_update():
    """测试 replenishment_update — 更新资源补充单（含无 detail 的情况）。"""
    replenishment_id = random.randint(1, 100)

    # 场景1：带 detail 的更新
    replenishment_detail = _random_replenishment_detail(1)
    test_data_with_detail = {
        "replenishmentNumber": f"BR{datetime.now().strftime('%Y%m%d')}{str(random.randint(0, 999)).zfill(3)}",
        "replenishmentTime": _now_iso(),
        "detail": replenishment_detail,
        "status": 3,
        "remark": "mcp_client 测试-更新补充单(含明细)",
    }
    print(f"\n{'='*60}")
    print(f"[mcp_client] 测试 replenishment_update (场景1: 含 detail): replenishment_id={replenishment_id}")
    print(f"  请求体: {test_data_with_detail}")
    print(f"{'='*60}")

    async with Client(mcp) as client:
        result1 = await client.call_tool("replenishment_update", {
            "replenishment_id": replenishment_id,
            **test_data_with_detail,
        })
        print(f"结果(含明细): {result1}")

        # 场景2：不带 detail 的纯状态更新
        test_data_no_detail = {
            "replenishmentNumber": f"BR{datetime.now().strftime('%Y%m%d')}{str(random.randint(0, 999)).zfill(3)}",
            "replenishmentTime": _now_iso(),
            "status": 2,
            "remark": "mcp_client 测试-仅更新状态和备注",
        }
        print(f"\n[mcp_client] 测试 replenishment_update (场景2: 无 detail，仅更新状态): replenishment_id={replenishment_id}")
        print(f"  请求体: {test_data_no_detail}")
        result2 = await client.call_tool("replenishment_update", {
            "replenishment_id": replenishment_id,
            **test_data_no_detail,
        })
        print(f"结果(无明细): {result2}")
        return result1


async def test_mcp_replenishment_search_details():
    """测试 replenishment_search_details — 搜索资源补充明细。"""
    resource_name = _random_resource_name()
    print(f"\n{'='*60}")
    print(f"[mcp_client] 测试 replenishment_search_details: resourceName={resource_name}")
    print(f"{'='*60}")

    async with Client(mcp) as client:
        # 方式1：按营销资源名称搜索
        result = await client.call_tool("replenishment_search_details", {
            "resource_name": resource_name
        })
        print(f"结果(按名称): {result}")

        # 方式2：按日期范围搜索
        result2 = await client.call_tool("replenishment_search_details", {
            "start_date": "2026-01-01",
            "end_date": "2026-05-06",
        })
        print(f"结果(按日期): {result2}")
        return result


async def test_mcp_quota_warning():
    """测试 quota_warning — 查询资源配额预警列表（无参）。"""
    print(f"\n{'='*60}")
    print("[mcp_client] 测试 quota_warning (无参调用)")
    print(f"{'='*60}")

    async with Client(mcp) as client:
        result = await client.call_tool("quota_warning", {})
        print(f"结果: {result}")
        return result


# ============================================================
# 2. agent_client 测试（HTTP 模式，模拟 Agent 调用）
# ============================================================

MCP_SERVER_CONFIG = {
    "erp": {
        "url": "http://127.0.0.1:8000/mcp",
        "transport": "streamable_http",
    }
}


async def test_agent_replenishment_create():
    """
    模拟 Agent 通过 MultiServerMCPClient 获取 replenishment_create 工具并调用。
    前提：MCP Server 已启动（python -m mcp_server.server_main）
    """
    print(f"\n{'='*60}")
    print("[agent_client] 模拟 Agent 测试 replenishment_create")
    print(f"{'='*60}")

    client = MultiServerMCPClient(MCP_SERVER_CONFIG)

    try:
        # 获取所有工具
        all_tools = await client.get_tools(server_name="erp")
        print(f"[agent_client] 已加载 {len(all_tools)} 个 MCP 工具")

        replenishment_tools = [t for t in all_tools if t.name == "replenishment_create"]
        if not replenishment_tools:
            print("[agent_client] 错误: 未找到 replenishment_create 工具")
            return

        replenishment_create_tool = replenishment_tools[0]
        print(f"[agent_client] 获取到工具: {replenishment_create_tool.name}")
        print(f"[agent_client] 工具描述: {replenishment_create_tool.description}")

        # 构造测试数据
        replenishment_detail = _random_replenishment_detail(2)
        total_amount = sum(item["subtotal"] for item in replenishment_detail)

        # 通过工具对象调用
        result = await replenishment_create_tool.ainvoke({
            "replenishment_number": f"BR{datetime.now().strftime('%Y%m%d')}{str(random.randint(0, 999)).zfill(3)}",
            "replenishment_time": _now_iso(),
            "detail": replenishment_detail,
            "total_amount": round(total_amount, 2),
            "status": 1,
            "remark": "agent_client 模拟测试补充单",
        })
        print(f"[agent_client] 执行结果: {result}")
        return result

    finally:
        pass  # MultiServerMCPClient 没有显式 close 方法


async def test_agent_quota_warning():
    """
    模拟 Agent 通过 MultiServerMCPClient 获取 quota_warning 工具并调用（无参）。
    前提：MCP Server 已启动（python -m mcp_server.server_main）
    """
    print(f"\n{'='*60}")
    print("[agent_client] 模拟 Agent 测试 quota_warning")
    print(f"{'='*60}")

    client = MultiServerMCPClient(MCP_SERVER_CONFIG)

    try:
        all_tools = await client.get_tools(server_name="erp")
        print(f"[agent_client] 已加载 {len(all_tools)} 个 MCP 工具")

        quota_tools = [t for t in all_tools if t.name == "quota_warning"]
        if not quota_tools:
            print("[agent_client] 错误: 未找到 quota_warning 工具")
            return

        quota_tool = quota_tools[0]
        print(f"[agent_client] 获取到工具: {quota_tool.name}")
        print(f"[agent_client] 工具描述: {quota_tool.description}")

        # 无参调用
        result = await quota_tool.ainvoke({})
        print(f"[agent_client] 执行结果: {result}")
        return result

    finally:
        pass


# ============================================================
# 批量运行入口
# ============================================================

async def run_all_mcp_client_tests():
    """依次运行全部 8 个 mcp_client 测试"""
    tests = [
        ("provider_query", test_mcp_provider_query),
        ("resource_query", test_mcp_resource_query),
        ("resource_search", test_mcp_resource_search),
        ("resource_by_provider", test_mcp_resource_by_provider),
        ("replenishment_create", test_mcp_replenishment_create),
        ("replenishment_update", test_mcp_replenishment_update),
        ("replenishment_search_details", test_mcp_replenishment_search_details),
        ("quota_warning", test_mcp_quota_warning),
    ]

    results = {}
    for name, test_fn in tests:
        try:
            results[name] = await test_fn()
        except Exception as e:
            results[name] = f"失败: {e}"
            print(f"[ERROR] {name} 测试失败: {e}")

    print(f"\n{'='*60}")
    print("[汇总] mcp_client 测试完成")
    print(f"{'='*60}")
    for name, result in results.items():
        status = "失败" if isinstance(result, str) and result.startswith("失败") else "完成"
        print(f"  {name}: {status}")


async def run_all_agent_client_tests():
    """依次运行 agent_client 测试：replenishment_create + quota_warning。"""
    results = {}
    for name, test_fn in [
        ("replenishment_create", test_agent_replenishment_create),
        ("quota_warning", test_agent_quota_warning),
    ]:
        try:
            results[name] = await test_fn()
        except Exception as e:
            results[name] = f"失败: {e}"
            print(f"[ERROR] agent_client {name} 测试失败: {e}")

    print(f"\n{'='*60}")
    print("[汇总] agent_client 测试完成")
    print(f"{'='*60}")
    for name, result in results.items():
        status = "失败" if isinstance(result, str) and result.startswith("失败") else "完成"
        print(f"  {name}: {status}")


if __name__ == "__main__":
    import sys

    # if len(sys.argv) > 1:
    #     mode = sys.argv[1]
    # else:
    mode = "agent"

    if mode == "mcp":
        print("运行全部 mcp_client 测试（内存模式）...")
        asyncio.run(run_all_mcp_client_tests())
    elif mode == "agent":
        print("运行 agent_client 测试（需 MCP Server 已启动在 127.0.0.1:8000）...")
        asyncio.run(run_all_agent_client_tests())
    elif mode == "all":
        print("=== 第一阶段：mcp_client 测试 ===\n")
        asyncio.run(run_all_mcp_client_tests())
        print("\n=== 第二阶段：agent_client 测试 ===\n")
        asyncio.run(run_all_agent_client_tests())
    else:
        print(f"未知模式: {mode}")
        print("用法: python -m test.test_all_tools [mcp|agent|all]")
