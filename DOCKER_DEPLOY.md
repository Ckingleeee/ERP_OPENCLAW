# Ubuntu 一键部署指南

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

OpenSandbox 在宿主机以 systemd 服务运行。它需要访问 Docker daemon 并创建用户沙箱，与普通 Web 服务的权限边界不同。`deploy.sh` 和 `erpctl` 会统一管理它，因此对运维人员仍是一套入口。

## 2. 支持范围

- Ubuntu 22.04/24.04（脚本会安装缺失的 Docker Engine 和 Compose v2）。
- 至少 4 GB 内存；运行多个用户沙箱时建议 8 GB 以上。
- 防火墙只对外开放 HTTP/HTTPS 和运维 SSH，不要公开 MySQL、MongoDB、8080、8090 和 MCP 端口。
- 云厂商安全组仍需手动放行 SSH、HTTP/HTTPS；脚本无法修改云控制台安全组。

其他 Linux 发行版可以手动安装 Docker 后使用 Compose，但不属于一键安装脚本的支持范围。

## 3. 一键部署

克隆代码并准备配置：

```bash
git clone <repository-url> /opt/erp_openclaw
cd /opt/erp_openclaw
cp .env.docker.example .env
chmod 600 .env
# 编辑 .env，替换全部密码、API Key、域名和占位值
sudoedit .env
```

执行部署：

```bash
sudo bash ./scripts/deploy.sh
```

脚本会依次完成：

1. 校验 `.env`，但不输出密钥。
2. 安装或启动 Docker Engine、Buildx 和 Compose v2。
3. 安装固定版本的 OpenSandbox Server，生成配置并限制监听 Docker 网关。
4. 拉取 MySQL、MongoDB 和沙箱镜像。
5. 构建前后端镜像，启动 Compose 服务。
6. 安装 `erpctl` 和 `erp-openclaw.service`，配置开机启动。
7. 检查 OpenSandbox、前端、Agent、ERP API、MCP 和数据库健康状态。

脚本不会创建、修改或覆盖 `.env`。环境校验失败时，应修复提示项后重新执行。

已有可用 OpenSandbox，不希望重新安装或改写其配置时：

```bash
sudo bash ./scripts/deploy.sh --reuse-opensandbox
```

服务器已有构建完成的应用镜像时：

```bash
sudo bash ./scripts/deploy.sh --no-build --reuse-opensandbox
```

## 4. 必填环境变量

至少替换：

- `MYSQL_ROOT_PASSWORD`
- `ERP_DB_PASSWORD`
- `MONGO_ROOT_PASSWORD`
- `MONGODB_APP_PASSWORD`
- `ERP_ADMIN_PASSWORD`
- `AUTH_JWT_SECRET`
- `DEEPSEEK_API_KEY` / `DEEPSEEK_BASE_URL`
- `ALIBABA_API_KEY`
- `OPEN_SANDBOX_API_KEY`

如启用小笨羊图表 MCP，还必须同时配置 `ANALYSIS_MCP_URL` 和
`XBY_API_KEY`。后者会作为 `XBY-APIKEY` HTTP 请求头发送，禁止提交到 Git。

建议数据库密码只使用字母和数字的长随机串，避免 MongoDB URI 出现未编码的 `@`、`:`、`/` 等字符。

`.env` 已被 Git 忽略，不得提交。

生成随机密钥：

```bash
openssl rand -hex 32
```

### 匿名演示模式

公开演示环境可以关闭登录页面，并为每个浏览器自动签发独立的匿名身份：

```dotenv
AUTH_DEMO_MODE=true
AUTH_DEMO_DISPLAY_NAME=演示用户
AUTH_DEMO_ROLE=demo
AUTH_DEMO_DEPARTMENT=公开演示
```

同一浏览器会通过签名 HttpOnly Cookie 复用身份，不同浏览器的对话、记忆和沙箱互相隔离。清除站点 Cookie 后会获得新的演示身份。正式环境应保持 `AUTH_DEMO_MODE=false`，继续使用用户名和密码登录。

## 5. 国内网络和镜像源

构建源全部可以在 `.env` 中替换，不需要改 Dockerfile：

| 变量 | 默认值 | 用途 |
|---|---|---|
| `MYSQL_IMAGE` | `mysql:8.4` | MySQL 镜像 |
| `MONGODB_IMAGE` | `mongo:8.0` | MongoDB 镜像 |
| `PYTHON_BASE_IMAGE` | `python:3.12-slim` | 后端基础镜像 |
| `NODE_BASE_IMAGE` | `node:22-alpine` | 前端构建镜像 |
| `NGINX_BASE_IMAGE` | `nginx:1.27-alpine` | 前端运行镜像 |
| `APT_MIRROR` | 空（Debian 官方源） | 容器 APT 源 |
| `APT_SECURITY_MIRROR` | 空（Debian 官方源） | Debian security 源 |
| `PIP_INDEX_URL` | `https://pypi.org/simple` | 后端和 OpenSandbox PyPI 源 |
| `NPM_REGISTRY` | `https://registry.npmjs.org` | 前端 NPM 源 |
| `DOCKER_APT_REPOSITORY_URL` | Docker 官方 Ubuntu 仓库 | Docker 安装源 |

镜像地址应使用云厂商当前提供的地址。不要把镜像仓库用户名、密码或临时 Token 写进仓库。

## 6. OpenSandbox 网络边界

Agent 容器通过以下地址访问 OpenSandbox：

```dotenv
OPEN_SANDBOX_DOMAIN=http://host.docker.internal:18080
```

OpenSandbox 如果只监听 `127.0.0.1`，Docker 容器无法访问。建议让它监听 Docker 宿主网关，而不是公网网卡。先确认网关：

```bash
docker network inspect bridge --format '{{(index .IPAM.Config 0).Gateway}}'
```

若输出是 `172.17.0.1`，OpenSandbox 会绑定这个地址。`deploy.sh` 会自动生成并维护配置，无需手工编辑：

```toml
[server]
host = "172.17.0.1"
port = 18080
api_key = "<same-value-as-OPEN_SANDBOX_API_KEY>"
```

从宿主机检查：

```bash
curl http://172.17.0.1:18080/health
```

`OPEN_SANDBOX_API_KEY` 为生产必填值，部署脚本会把它同步到权限为 `600` 的 OpenSandbox 配置中。不建议监听 `0.0.0.0`，也不要在云安全组中公开 18080。

OpenSandbox 官方配置参考：[Configuration](https://github.com/opensandbox-group/OpenSandbox/blob/main/docs/getting-started/configuration.md)。

## 7. 日常管理

```bash
erpctl status
erpctl health
erpctl start
erpctl restart
erpctl stop
erpctl logs agent-web
erpctl logs frontend
```

`erpctl stop` 使用 `docker compose stop`，不会删除容器卷。不要执行 `docker compose down -v`。

自动启动由两个 systemd 单元负责：

- `opensandbox.service`：先启动沙箱控制面。
- `erp-openclaw.service`：再确保 Compose 服务已启动。

## 8. 手动诊断

```text
docker compose ps
docker compose logs --tail=200 agent-web
docker compose logs --tail=200 erp-mcp
docker compose logs --tail=200 erp-api
docker compose logs --tail=200 mysql mongodb
curl http://127.0.0.1:${HTTP_PORT:-80}/health
curl http://172.17.0.1:18080/health
```

某个服务需要重启时：

```bash
docker compose restart agent-web
```

## 9. 初始化权益运营数据库

先只启动数据库：

```bash
docker compose up -d mysql mongodb
docker compose ps
```

首次部署时导入新的权益运营表结构和演示数据：

```bash
docker compose exec -T mysql \
  sh -c 'mysql -uroot -p"$MYSQL_ROOT_PASSWORD" "$MYSQL_DATABASE"' \
  < docker/mysql/init/01-schema.sql
```

`motorparts_db.sql` 是旧业务历史归档，表结构与当前权益运营模型不兼容，不要直接导入。若需保留已有 MongoDB 对话状态，先单独备份再恢复：

```bash
mongodump --uri="$OLD_MONGODB_URI" --archive="$PWD/langchain_db.archive" \
  --gzip --db=langchain_db
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

## 10. 日常更新

```bash
git pull --ff-only
sudo bash ./scripts/deploy.sh --reuse-opensandbox
```

部署脚本不会执行 `git pull`。先检查并同步 Git，再重新部署，MySQL 和 MongoDB 数据仍保留在命名卷中。

## 11. 停止和回滚

停止应用并保留数据：

```bash
erpctl stop
```

不要在生产环境执行：

```bash
docker compose down -v
```

代码回滚使用 Git 的可追踪回滚，然后重建：

```bash
git revert <commit-id>
sudo bash ./scripts/deploy.sh --reuse-opensandbox
```

## 12. HTTPS

当 Nginx 配置 HTTPS 后，将：

```dotenv
AUTH_COOKIE_SECURE=true
CORS_ALLOWED_ORIGINS=https://your-domain.example
```

证书不应提交到 Git，建议使用宿主机证书目录只读挂载或使用云负载均衡器终止 TLS。
