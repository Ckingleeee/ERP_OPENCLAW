# Docker Compose 部署指南

## 1. 服务架构

Compose 统一管理以下服务：

| 服务 | 用途 | 对外暴露 |
|---|---|---|
| `frontend` | Nginx + Vue，反向代理 Agent API | `${HTTP_PORT:-80}` |
| `agent-web` | 登录、对话、会话历史 | 否 |
| `erp-mcp` | 将 ERP REST API 封装为 Agent 工具 | 否 |
| `erp-api` | Python ERP 业务 API | 否 |
| `mysql` | ERP 业务数据 | 否 |
| `mongodb` | Agent checkpoint、会话和沙箱绑定 | 否 |

OpenSandbox 第一阶段仍在宿主机运行。它需要访问 Docker daemon 并创建用户沙箱，与普通 Web 服务的权限边界不同。

## 2. 前置条件

- Linux 服务器已安装 Docker Engine 和 Docker Compose v2。
- OpenSandbox 已能在宿主机启动。
- 至少 4 GB 内存；运行多个用户沙箱时建议 8 GB 以上。
- 防火墙只对外开放 HTTP/HTTPS 和运维 SSH，不要公开 MySQL、MongoDB、8080、8090 和 MCP 端口。

验证：

```bash
docker --version
docker compose version
docker info
```

## 3. 准备环境变量

```bash
cp .env.docker.example .env
chmod 600 .env
```

生成随机密钥：

```bash
openssl rand -hex 32
```

至少替换这些值：

- `MYSQL_ROOT_PASSWORD`
- `ERP_DB_PASSWORD`
- `MONGO_ROOT_PASSWORD`
- `MONGODB_APP_PASSWORD`
- `ERP_ADMIN_PASSWORD`
- `AUTH_JWT_SECRET`
- `DEEPSEEK_API_KEY` / `DEEPSEEK_BASE_URL`
- `ALIBABA_API_KEY`
- `OPEN_SANDBOX_API_KEY`

建议数据库密码只使用字母和数字的长随机串，避免 MongoDB URI 出现未编码的 `@`、`:`、`/` 等字符。

`.env` 已被 Git 忽略，不得提交。

## 4. 让容器访问宿主机 OpenSandbox

Agent 容器通过以下地址访问 OpenSandbox：

```dotenv
OPEN_SANDBOX_DOMAIN=http://host.docker.internal:18080
```

OpenSandbox 如果只监听 `127.0.0.1`，Docker 容器无法访问。建议让它监听 Docker 宿主网关，而不是公网网卡。先确认网关：

```bash
docker network inspect bridge --format '{{(index .IPAM.Config 0).Gateway}}'
```

若输出是 `172.17.0.1`，在 OpenSandbox 配置中使用：

```toml
[server]
host = "172.17.0.1"
port = 18080
api_key = "<same-value-as-OPEN_SANDBOX_API_KEY>"
```

重启 OpenSandbox 后从宿主机检查：

```bash
curl http://172.17.0.1:18080/health
```

不建议在无 API Key 和防火墙限制时监听 `0.0.0.0`。

## 5. 全新环境启动

```bash
docker compose config --quiet
docker compose up -d --build
docker compose ps
```

首次启动时会：

1. 创建 MySQL 和 MongoDB 持久卷。
2. 执行 `docker/mysql/init/01-schema.sql`。
3. 创建 MongoDB 应用用户。
4. `erp-init` 对 `ERP_ADMIN_PASSWORD` 进行 bcrypt 加密并创建首个 ERP 登录用户。
5. 按 MySQL → ERP API → MCP → Agent Web → Nginx 的顺序启动。

浏览器访问：

```text
http://<server-ip>/
```

## 6. 日志和健康检查

```bash
docker compose ps
docker compose logs --tail=200 agent-web
docker compose logs --tail=200 erp-mcp
docker compose logs --tail=200 erp-api
docker compose logs --tail=200 mysql mongodb
curl http://127.0.0.1:${HTTP_PORT:-80}/health
```

某个服务需要重启时：

```bash
docker compose restart agent-web
```

## 7. 从现有宿主机数据库迁移

不要直接删除现有 MySQL、MongoDB 或 systemd 服务。先备份：

```bash
sudo mysqldump --single-transaction --routines --triggers motorparts_db \
  > "$PWD/motorparts_db_backup.sql"

mongodump --uri="$OLD_MONGODB_URI" --archive="$PWD/langchain_db.archive" \
  --gzip --db=langchain_db
```

先只启动数据库：

```bash
docker compose up -d mysql mongodb
docker compose ps
```

导入 MySQL：

```bash
docker compose exec -T mysql \
  sh -c 'mysql -uroot -p"$MYSQL_ROOT_PASSWORD" "$MYSQL_DATABASE"' \
  < motorparts_db_backup.sql
```

导入 MongoDB：

```bash
docker compose cp langchain_db.archive mongodb:/tmp/langchain_db.archive
docker compose exec mongodb sh -c \
  'mongorestore --username "$MONGO_INITDB_ROOT_USERNAME" \
  --password "$MONGO_INITDB_ROOT_PASSWORD" \
  --authenticationDatabase admin \
  --archive=/tmp/langchain_db.archive --gzip --drop'
```

数据验证通过后再启动全部服务：

```bash
docker compose up -d --build
```

> `mongorestore --drop` 会覆盖目标集合，只能在已确认备份和目标数据库的情况下执行。

## 8. 日常更新

```bash
git pull --ff-only
docker compose up -d --build
docker compose ps
```

Compose 会只重建发生变化的应用容器，MySQL 和 MongoDB 数据保留在命名卷中。

## 9. 停止和回滚

停止应用，保留数据：

```bash
docker compose down
```

不要在生产环境执行：

```bash
docker compose down -v
```

代码回滚使用 Git 的可追踪回滚，然后重建：

```bash
git revert <commit-id>
docker compose up -d --build
```

## 10. HTTPS

当 Nginx 配置 HTTPS 后，将：

```dotenv
AUTH_COOKIE_SECURE=true
CORS_ALLOWED_ORIGINS=https://your-domain.example
```

证书不应提交到 Git，建议使用宿主机证书目录只读挂载或使用云负载均衡器终止 TLS。
