from fastmcp import FastMCP, Context
from typing import Optional

# 分组名称
GROUP_NAME = "resource"


def register_resource_tools(mcp: FastMCP):
    """注册信用卡权益与营销资源分组的所有工具。"""

    @mcp.tool(name=f"{GROUP_NAME}_query")
    async def query_resources(
        current: Optional[int] = 1,
        size: Optional[int] = 10,
        name: Optional[str] = None,
        category: Optional[str] = None,
        provider_id: Optional[int] = None,
        ctx: Context = None,
    ) -> list:
        """
        分页查询权益与营销资源列表。
        支持按名称模糊查询、按分类筛选、按服务商 ID 筛选。

        Args:
            current: 当前页码，从1开始，默认1
            size: 每页大小，默认10
            name: 权益或营销资源名称（模糊查询），可选
            category: 分类（影音会员/出行权益/餐饮优惠/积分礼品/营销券包），可选
            provider_id: 权益服务商 ID，可选
        """
        http_client = ctx.request_context.lifespan_context.get("http_client")

        # 构建请求参数（过滤 None 值，映射到 API 字段名）
        request_params = {}
        if current is not None:
            request_params["current"] = current
        if size is not None:
            request_params["size"] = size
        if name is not None:
            request_params["name"] = name
        if category is not None:
            request_params["category"] = category
        if provider_id is not None:
            request_params["providerId"] = provider_id

        try:
            response = await http_client.get("/resources/page", params=request_params)
            response.raise_for_status()
            result = response.json()

            # 检查业务状态码
            if result.get("code") != 200:
                return [f"API error: code={result.get('code')}"]

            # 返回 data 字段，通常包含 records, total, current, size 等
            return result.get("data", {}).get("records", [])

        except Exception as e:
            return [f'没有查询到任何信息，而且报错: {e}']

    @mcp.tool(name=f"{GROUP_NAME}_search")
    async def search_resources(name: str, ctx: Context) -> list:
        """
        按名称搜索权益或营销资源。
        与 resource_query 不同，此接口直接搜索，name 为必填参数。

        Args:
            name: 权益或营销资源名称（模糊查询），必填
        """
        http_client = ctx.request_context.lifespan_context.get("http_client")

        try:
            response = await http_client.get("/resources/search", params={"name": name})
            response.raise_for_status()
            result = response.json()

            if result.get("code") != 200:
                return [f"API error: code={result.get('code')}"]

            # data 为数组
            return result.get("data", [])
        except Exception as e:
            return [f'没有查询到任何信息，而且报错: {e}']

    @mcp.tool(name=f"{GROUP_NAME}_by_provider")
    async def list_resources_by_provider(provider_id: int, ctx: Context) -> list:
        """
        根据服务商 ID 查询其提供的权益与营销资源列表。

        Args:
            provider_id: 权益服务商 ID（路径参数，必填）
        """
        http_client = ctx.request_context.lifespan_context.get("http_client")

        try:
            response = await http_client.get(f"/resources/provider/{provider_id}")
            response.raise_for_status()
            result = response.json()

            if result.get("code") != 200:
                return [f"API error: code={result.get('code')}"]

            return result.get("data", [])
        except Exception as e:
            return [f'没有查询到任何信息，而且报错: {e}']
