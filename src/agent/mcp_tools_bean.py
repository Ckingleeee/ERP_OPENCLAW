from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List

from pydantic import BaseModel, Field

# 分组名称常量
GROUP_RESOURCE = "resource"
GROUP_PROVIDER = "provider"

class ProviderQueryInput(BaseModel):
    """权益服务商查询参数模型。"""
    name: str = Field(..., description="服务商名称（模糊查询），必填")


class ResourceSearchInput(BaseModel):
    """权益与营销资源搜索参数模型。"""
    name: str = Field(..., description="资源名称（模糊查询），必填")


class ResourceQueryInput(BaseModel):
    """权益与营销资源分页查询参数模型。"""
    current: Optional[int] = Field(1, description="当前页码，从1开始")
    size: Optional[int] = Field(10, description="每页大小")
    name: Optional[str] = Field(None, description="权益或营销资源名称")
    category: Optional[str] = Field(None, description="资源分类")
    provider_id: Optional[int] = Field(None, description="权益服务商 ID")


class ReplenishmentDetailItem(BaseModel):
    """权益资源补充明细项。"""
    resourceId: int = Field(..., description="资源 ID，必填")
    quantity: int = Field(..., description="补充数量，必填，最小值为1")
    unitCost: Decimal = Field(..., description="单位成本，必填")
    subtotal: Optional[Decimal] = Field(None, description="小计金额")
    remark: Optional[str] = Field(None, description="明细备注")


class ReplenishmentInput(BaseModel):
    """权益资源补充单请求模型。"""
    replenishment_number: Optional[str] = Field(
        None,
        description="补充单编号。规则：BR+年月日+3位随机数字"
    )
    total_amount: Optional[Decimal] = Field(None, description="补充单总金额")
    status: Optional[int] = Field(
        None,
        description="状态(1-待审核, 2-已审核, 3-配置中, 4-已生效, 5-已取消)"
    )
    replenishment_time: Optional[str] = Field(
        None,
        description="创建时间，格式：yyyy-MM-ddTHH:mm:ss.SSS"
    )
    expected_activation_date: Optional[date] = Field(
        None,
        description="预计生效日期，格式：yyyy-MM-dd"
    )
    actual_activation_date: Optional[date] = Field(None, description="实际生效日期")
    created_by: Optional[int] = Field(None, description="创建人 ID")
    remark: Optional[str] = Field(None, description="备注")
    detail: Optional[List[ReplenishmentDetailItem]] = Field(
        None,
        description="补充明细。每项需提供 resourceId、quantity、unitCost"
    )


class ReplenishmentSearchInput(BaseModel):
    """权益资源补充历史搜索参数模型。"""
    resource_name: Optional[str] = Field(None, description="资源名称（模糊查询）")
    start_date: Optional[str] = Field(None, description="开始日期（yyyy-MM-dd 格式）")
    end_date: Optional[str] = Field(None, description="结束日期（yyyy-MM-dd 格式）")


# create_deep_agent()
# create_summarization_tool_middleware
