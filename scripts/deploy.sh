#!/usr/bin/env bash

set -Eeuo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$PROJECT_DIR/.env"
VALIDATOR="$PROJECT_DIR/scripts/validate-docker-env.py"
INSTALL_OPENSANDBOX="$PROJECT_DIR/scripts/install-opensandbox.sh"
BUILD_IMAGES=true
INSTALL_SANDBOX=auto
PULL_IMAGES=false

log() {
  printf '\n[deploy] %s\n' "$*"
}

die() {
  printf '\n[deploy] 错误：%s\n' "$*" >&2
  exit 1
}

usage() {
  cat <<'EOF'
用法：
  sudo bash ./scripts/deploy.sh [选项]

选项：
  --no-build            使用服务器已有镜像，不重新构建
  --reuse-opensandbox   强制复用现有 OpenSandbox，服务不健康时终止部署
  --install-opensandbox 显式安装/升级 OpenSandbox（会重启该服务）
  --pull-images         主动更新数据库镜像和构建基础镜像
  -h, --help            显示帮助

脚本不会创建或修改 .env。首次执行前请从 .env.docker.example 复制并填写。
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --no-build)
      BUILD_IMAGES=false
      ;;
    --reuse-opensandbox)
      INSTALL_SANDBOX=false
      ;;
    --install-opensandbox)
      INSTALL_SANDBOX=true
      ;;
    --pull-images)
      PULL_IMAGES=true
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      die "未知参数：$1"
      ;;
  esac
  shift
done

if [[ $EUID -ne 0 ]]; then
  die "请使用 sudo bash ./scripts/deploy.sh 执行"
fi

[[ -f "$ENV_FILE" ]] || die "找不到 $ENV_FILE；请先执行 cp .env.docker.example .env 并填写配置"
[[ -f "$VALIDATOR" ]] || die "找不到 $VALIDATOR"
[[ -f "$INSTALL_OPENSANDBOX" ]] || die "找不到 $INSTALL_OPENSANDBOX"

source /etc/os-release
if [[ "${ID:-}" != "ubuntu" ]]; then
  die "一键安装当前只支持 Ubuntu，检测到：${ID:-unknown}"
fi

missing_host_tool=false
for command_name in python3 curl; do
  if ! command -v "$command_name" >/dev/null 2>&1; then
    missing_host_tool=true
  fi
done
if [[ "$missing_host_tool" == true ]]; then
  apt-get -o Acquire::Retries=5 update
  DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    python3 ca-certificates curl
fi

env_get() {
  python3 "$VALIDATOR" "$ENV_FILE" --get "$1" 2>/dev/null || true
}

compose() {
  docker compose --project-directory "$PROJECT_DIR" --env-file "$ENV_FILE" "$@"
}

install_docker_repository() {
  local repository_url
  repository_url="$(env_get DOCKER_APT_REPOSITORY_URL)"
  repository_url="${repository_url:-https://download.docker.com/linux/ubuntu}"

  apt-get -o Acquire::Retries=5 update
  DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    ca-certificates curl
  install -m 0755 -d /etc/apt/keyrings
  curl --fail --show-error --location --retry 5 \
    https://download.docker.com/linux/ubuntu/gpg \
    -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc

  cat >/etc/apt/sources.list.d/docker.sources <<EOF
Types: deb
URIs: $repository_url
Suites: ${UBUNTU_CODENAME:-$VERSION_CODENAME}
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF
}

ensure_docker() {
  if command -v docker >/dev/null 2>&1 \
    && docker compose version >/dev/null 2>&1; then
    systemctl enable --now docker

    if [[ "$BUILD_IMAGES" == false ]] \
      || docker buildx version >/dev/null 2>&1; then
      return
    fi

    log "安装 Ubuntu docker-buildx，保留现有 Docker 与 Compose"
    apt-get -o Acquire::Retries=5 update
    DEBIAN_FRONTEND=noninteractive apt-get install -y docker-buildx
    docker buildx version >/dev/null
    return
  fi

  log "安装 Docker Engine 和 Compose v2"
  install_docker_repository
  apt-get -o Acquire::Retries=5 update
  DEBIAN_FRONTEND=noninteractive apt-get install -y \
    docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  systemctl enable --now docker
  docker version >/dev/null
  docker compose version >/dev/null
}

wait_for_url() {
  local name="$1"
  local url="$2"
  local timeout_seconds="$3"
  local deadline=$((SECONDS + timeout_seconds))

  log "等待${name}：$url"
  while (( SECONDS < deadline )); do
    if curl --fail --silent --show-error --max-time 5 "$url" >/dev/null 2>&1; then
      printf '[deploy] %s健康检查通过。\n' "$name"
      return 0
    fi
    sleep 3
  done

  compose ps || true
  compose logs --tail=120 frontend agent-web erp-mcp erp-api || true
  die "$name 在 $timeout_seconds 秒内未通过健康检查"
}

install_operations() {
  local bridge_ip
  bridge_ip="$(docker network inspect bridge --format '{{(index .IPAM.Config 0).Gateway}}')"
  [[ -n "$bridge_ip" ]] || die "无法读取 Docker bridge 网关"

  install -o root -g root -m 0755 "$PROJECT_DIR/scripts/erpctl.sh" /usr/local/sbin/erpctl

  cat >/etc/systemd/system/erp-openclaw.service <<EOF
[Unit]
Description=ERP OpenClaw Docker Compose Stack
Requires=docker.service opensandbox.service
After=network-online.target docker.service opensandbox.service
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$PROJECT_DIR
ExecStartPre=/bin/sh -c 'for attempt in \$(seq 1 60); do /usr/bin/curl -fsS http://$bridge_ip:18080/health >/dev/null && exit 0; sleep 2; done; exit 1'
ExecStart=/usr/bin/docker compose --project-directory $PROJECT_DIR --env-file $ENV_FILE up -d --no-build
ExecStop=/usr/bin/docker compose --project-directory $PROJECT_DIR --env-file $ENV_FILE stop
TimeoutStartSec=300
TimeoutStopSec=180

[Install]
WantedBy=multi-user.target
EOF

  chmod 644 /etc/systemd/system/erp-openclaw.service
  systemctl daemon-reload
  systemctl enable erp-openclaw.service
}

configure_firewall() {
  local http_port="$1"
  if ! command -v ufw >/dev/null 2>&1 || ! ufw status | grep -q '^Status: active'; then
    return
  fi

  if ! ufw status | grep -Eq "(^|[[:space:]])${http_port}/tcp([[:space:]]|$)"; then
    ufw allow "${http_port}/tcp" comment 'ERP OpenClaw web'
  fi
}

log "校验 .env"
python3 "$VALIDATOR" "$ENV_FILE"

ensure_docker

if [[ "$INSTALL_SANDBOX" == auto ]]; then
  if systemctl is-active --quiet opensandbox; then
    bridge_ip="$(docker network inspect bridge --format '{{(index .IPAM.Config 0).Gateway}}')"
    [[ -n "$bridge_ip" ]] || die "无法读取 Docker bridge 网关"
    curl --fail --silent --show-error --max-time 5 \
      "http://$bridge_ip:18080/health" >/dev/null \
      || die "现有 OpenSandbox 不健康；请先排障，或在维护窗口使用 --install-opensandbox"
    log "复用健康的 OpenSandbox；常规部署不会重装或重启它"
    INSTALL_SANDBOX=false
  else
    INSTALL_SANDBOX=true
  fi
fi

if [[ "$INSTALL_SANDBOX" == true ]]; then
  log "安装并配置 OpenSandbox"
  PROJECT_DIR="$PROJECT_DIR" ENV_FILE="$ENV_FILE" bash "$INSTALL_OPENSANDBOX"
else
  systemctl is-active --quiet opensandbox \
    || die "使用了 --reuse-opensandbox，但 opensandbox.service 未运行"
fi

log "校验 Docker Compose"
compose config --quiet

if [[ "$BUILD_IMAGES" == true ]]; then
  build_args=()
  if [[ "$PULL_IMAGES" == true ]]; then
    log "更新数据库镜像"
    compose pull mysql mongodb
    build_args+=(--pull)
  fi

  log "构建后端和前端镜像"
  compose build "${build_args[@]}" erp-api erp-mcp agent-web frontend
fi

http_port="$(env_get HTTP_PORT)"
http_port="${http_port:-80}"
if command -v ss >/dev/null 2>&1 \
  && ss -H -ltn "sport = :$http_port" | grep -q . \
  && [[ -z "$(compose ps --status running -q frontend 2>/dev/null)" ]]; then
  die "HTTP_PORT=$http_port 已被其他进程占用，请先确认端口归属"
fi

configure_firewall "$http_port"
install_operations

log "启动 ERP Docker Compose 服务"
compose up -d --remove-orphans
wait_for_url "ERP" "http://127.0.0.1:$http_port/health" 300

systemctl start erp-openclaw.service

log "部署完成"
compose ps
printf '\n访问地址：http://<server-ip>'
if [[ "$http_port" != "80" ]]; then
  printf ':%s' "$http_port"
fi
printf '/\n'
printf '日常管理：erpctl status | start | stop | restart | health | logs\n'
