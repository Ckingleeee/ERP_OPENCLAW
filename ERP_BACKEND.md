# 信用卡权益与营销资源运营后端

该服务默认监听 `127.0.0.1:8080`，为权益运营 MCP 工具提供稳定的业务接口。

## 接口

| 方法 | 路径 | 用途 |
|---|---|---|
| GET | `/health` | 数据库健康检查 |
| GET | `/api/providers/search?name=星享` | 按名称查询权益服务商 |
| GET | `/api/resources/page` | 分页和条件查询权益与营销资源 |
| GET | `/api/resources/search?name=会员` | 按名称查询权益资源 |
| GET | `/api/resources/provider/{provider_id}` | 查询服务商提供的资源 |
| GET | `/api/quotas/warning` | 查询低于安全阈值的资源配额 |
| POST | `/api/replenishments/create` | 创建资源补充单及明细 |
| PUT | `/api/replenishments/update/{replenishment_id}` | 更新补充单，可替换明细 |
| GET | `/api/replenishments/search-details` | 查询资源补充历史明细 |

所有接口延续原项目响应格式：

```json
{
  "code": 200,
  "message": "success",
  "data": {}
}
```

## 初始化

在 PowerShell 中执行：

```powershell
cd D:\workspace\ERP_OPENCLAW
py -3.12 -m venv ..\erp_openclaw_venv
..\erp_openclaw_venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-erp.txt
```

根据 `.env.example` 创建你自己的 `.env`，至少填写 `ERP_DB_USER` 和 `ERP_DB_PASSWORD`。

首次运行需要创建并导入数据库。以下命令会写入本地 MySQL，请先确认账号和目标库：

```powershell
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS benefits_ops_db CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;"
mysql -u root -p benefits_ops_db < docker/mysql/init/01-schema.sql
```

## 启动和验证

```powershell
$env:PYTHONPATH = (Resolve-Path .\src).Path
python -m uvicorn erp_backend.main:app --host 127.0.0.1 --port 8080 --reload
```

打开：

- API 文档：<http://127.0.0.1:8080/docs>
- 健康检查：<http://127.0.0.1:8080/health>

ERP API 正常后，在另一个 PowerShell 窗口启动 MCP：

```powershell
$env:PYTHONPATH = (Resolve-Path .\src).Path
python -m mcp_server.server_main
```

MCP 默认监听 `http://127.0.0.1:8000/mcp`。

## 创建权益资源补充单示例

```json
{
  "status": 1,
  "remark": "九月活跃提升活动",
  "detail": [
    {
      "resourceId": 1,
      "quantity": 1000,
      "unitCost": 12.80
    }
  ]
}
```

创建、更新补充单使用数据库事务。明细存在无效资源 ID 时，补充单头与明细会整体回滚。
