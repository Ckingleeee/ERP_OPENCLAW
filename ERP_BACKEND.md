# Python ERP 后端

该服务替代原来的 Java ERP API，默认监听 `127.0.0.1:8080`，并保持现有 MCP 工具使用的接口契约。

## 接口

| 方法 | 路径 | 用途 |
|---|---|---|
| GET | `/health` | 数据库健康检查 |
| GET | `/api/suppliers/search?name=博世` | 按名称查询供应商 |
| GET | `/api/parts/page` | 分页和条件查询零部件 |
| GET | `/api/parts/search?name=火花塞` | 按名称查询零部件 |
| GET | `/api/parts/supplier/{supplier_id}` | 查询供应商的零部件 |
| GET | `/api/inventory/warning` | 查询低于安全库存的零部件 |
| POST | `/api/orders/create` | 创建采购订单及明细 |
| PUT | `/api/orders/update/{order_id}` | 更新订单，可替换明细 |
| GET | `/api/orders/search-details` | 查询采购历史明细 |

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
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-erp.txt
```

根据 `.env.example` 创建你自己的 `.env`，至少填写 `ERP_DB_USER` 和 `ERP_DB_PASSWORD`。

首次运行需要创建并导入数据库。以下命令会写入本地 MySQL，请先确认账号和目标库：

```powershell
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS motorparts_db CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;"
mysql -u root -p motorparts_db < motorparts_db.sql
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

## 创建订单示例

```json
{
  "status": 1,
  "remark": "本地接口测试",
  "orderDetail": [
    {
      "partId": 1,
      "quantity": 2,
      "unitPrice": 3905.00
    }
  ]
}
```

创建、更新订单使用数据库事务。创建失败或明细中存在无效零部件 ID 时，订单头和明细都会回滚。

