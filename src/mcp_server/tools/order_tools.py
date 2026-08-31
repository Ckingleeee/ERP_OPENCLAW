import random
from datetime import datetime
from decimal import Decimal

from fastmcp import FastMCP, Context

from typing import Optional, List

GROUP_NAME = "replenishment"


def _generate_replenishment_number() -> str:
    """生成补充单编号：BR + 年月日(8位) + 3位随机数字。"""
    today = datetime.now().strftime("%Y%m%d")
    suffix = str(random.randint(0, 999)).zfill(3)
    return f"BR{today}{suffix}"


def _prepare_create_request(data: dict) -> dict:
    """填充默认值并序列化请求体：Decimal→float，date→ISO字符串。"""
    if not data.get("replenishmentNumber"):
        data["replenishmentNumber"] = _generate_replenishment_number()

    if not data.get("replenishmentTime"):
        now = datetime.now()
        data["replenishmentTime"] = (
            now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}"
        )

    # 递归序列化
    return _serialize_request(data)


def _serialize_request(data: dict) -> dict:
    """递归处理：Decimal → float，date/datetime → ISO 字符串"""
    for key, value in data.items():
        if isinstance(value, Decimal):
            data[key] = float(value)
        elif hasattr(value, "isoformat"):
            data[key] = value.isoformat()
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    _serialize_request(item)
        elif isinstance(value, dict):
            _serialize_request(value)
    return data


def register_replenishment_tools(mcp: FastMCP):
    """注册营销资源补充单分组的所有工具。"""

    @mcp.tool(name=f"{GROUP_NAME}_create")
    async def create_replenishment(
        detail: List[dict],
        replenishment_number: Optional[str] = None,
        total_amount: Optional[float] = None,
        status: Optional[int] = None,
        replenishment_time: Optional[str] = None,
        expected_activation_date: Optional[str] = None,
        actual_activation_date: Optional[str] = None,
        created_by: Optional[int] = None,
        remark: Optional[str] = None,
        ctx: Context = None,
    ) -> dict:
        """
        创建权益与营销资源补充单（POST /replenishments/create）。

        replenishmentNumber 不传则自动生成（规则：BR+年月日+3位随机数字）。
        replenishmentTime 不传则默认当前时间。
        detail 必填，至少包含一个明细项；每项需提供 resourceId、quantity、unitCost。

        Args:
            detail: 补充明细，每项需提供 resourceId, quantity, unitCost
            replenishment_number: 补充单编号，不传则自动生成
            total_amount: 补充单总金额，不传则自动根据明细计算
            status: 状态(1-待审核, 2-已审核, 3-配置中, 4-已生效, 5-已取消)
            replenishment_time: 创建时间，格式 yyyy-MM-ddTHH:mm:ss.SSS
            expected_activation_date: 预计生效日期，格式 yyyy-MM-dd
            actual_activation_date: 实际生效日期，格式 yyyy-MM-dd
            created_by: 创建人 ID
            remark: 备注
        """
        http_client = ctx.request_context.lifespan_context.get("http_client")

        # 构建请求体（映射到 API 字段名）
        request_data = {}
        if replenishment_number is not None:
            request_data["replenishmentNumber"] = replenishment_number
        if total_amount is not None:
            request_data["totalAmount"] = total_amount
        if status is not None:
            request_data["status"] = status
        if replenishment_time is not None:
            request_data["replenishmentTime"] = replenishment_time
        if expected_activation_date is not None:
            request_data["expectedActivationDate"] = expected_activation_date
        if actual_activation_date is not None:
            request_data["actualActivationDate"] = actual_activation_date
        if created_by is not None:
            request_data["createdBy"] = created_by
        if remark is not None:
            request_data["remark"] = remark
        if detail is not None:
            request_data["detail"] = detail

        request_data = _prepare_create_request(request_data)

        try:
            print(request_data)
            response = await http_client.post(
                "/replenishments/create",
                json=request_data
            )
            response.raise_for_status()
            result = response.json()

            if result.get("code") != 200:
                return {
                    "error": f"API error: code={result.get('code')}, message={result.get('message')}"
                }

            return result.get("data", {})
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool(name=f"{GROUP_NAME}_update")
    async def update_replenishment(
        replenishment_id: int,
        detail: Optional[List[dict]] = None,
        replenishment_number: Optional[str] = None,
        total_amount: Optional[float] = None,
        status: Optional[int] = None,
        replenishment_time: Optional[str] = None,
        expected_activation_date: Optional[str] = None,
        actual_activation_date: Optional[str] = None,
        created_by: Optional[int] = None,
        remark: Optional[str] = None,
        ctx: Context = None,
    ) -> dict:
        """
        更新权益与营销资源补充单（PUT /replenishments/update/{id}）。

        detail 为可选，传入则替换原有明细。
        其他字段与创建补充单格式一致。

        Args:
            replenishment_id: 补充单 ID（路径参数，必填）
            detail: 补充明细列表（可选），每项需提供 resourceId, quantity, unitCost
            replenishment_number: 补充单编号
            total_amount: 补充单总金额
            status: 状态(1-待审核, 2-已审核, 3-配置中, 4-已生效, 5-已取消)
            replenishment_time: 补充单创建时间
            expected_activation_date: 预计生效日期
            actual_activation_date: 实际生效日期
            created_by: 创建人 ID
            remark: 备注
        """
        http_client = ctx.request_context.lifespan_context.get("http_client")

        # 构建请求体（映射到 API 字段名，只包含非 None 字段）
        request_data = {}
        if replenishment_number is not None:
            request_data["replenishmentNumber"] = replenishment_number
        if total_amount is not None:
            request_data["totalAmount"] = total_amount
        if status is not None:
            request_data["status"] = status
        if replenishment_time is not None:
            request_data["replenishmentTime"] = replenishment_time
        if expected_activation_date is not None:
            request_data["expectedActivationDate"] = expected_activation_date
        if actual_activation_date is not None:
            request_data["actualActivationDate"] = actual_activation_date
        if created_by is not None:
            request_data["createdBy"] = created_by
        if remark is not None:
            request_data["remark"] = remark
        if detail is not None:
            request_data["detail"] = detail

        # 更新接口只传用户明确指定的字段，不能自动生成新编号或重置创建时间。
        request_data = _serialize_request(request_data)

        try:
            print(request_data)
            response = await http_client.put(
                f"/replenishments/update/{replenishment_id}",
                json=request_data
            )
            response.raise_for_status()
            result = response.json()

            if result.get("code") != 200:
                return {
                    "error": f"API error: code={result.get('code')}, message={result.get('message')}"
                }

            return result.get("data", {})
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool(name=f"{GROUP_NAME}_search_details")
    async def search_replenishment_details(
        resource_name: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ctx: Context = None,
    ) -> list:
        """
        搜索权益与营销资源补充历史明细。

        支持按资源名称、日期范围筛选，所有参数均为可选。
        返回的每条明细包含资源详情（resourceDetail）及服务商信息（provider）。

        Args:
            resource_name: 权益或营销资源名称（模糊查询），可选
            start_date: 开始日期（yyyy-MM-dd 格式），可选
            end_date: 结束日期（yyyy-MM-dd 格式），可选
        """
        http_client = ctx.request_context.lifespan_context.get("http_client")

        # 构建请求参数（过滤 None 值，映射到 API 字段名）
        request_params = {}
        if resource_name is not None:
            request_params["resourceName"] = resource_name
        if start_date is not None:
            request_params["startDate"] = start_date
        if end_date is not None:
            request_params["endDate"] = end_date

        try:
            response = await http_client.get(
                "/replenishments/search-details",
                params=request_params
            )
            response.raise_for_status()
            result = response.json()

            if result.get("code") != 200:
                return [f"API error: code={result.get('code')}"]

            return result.get("data", [])
        except Exception as e:
            return [f'没有查询到任何信息，而且报错: {e}']
