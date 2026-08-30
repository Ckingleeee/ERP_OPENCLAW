#!/usr/bin/env bash

set -Eeuo pipefail

PROJECT_DIR="${ERP_PROJECT_DIR:-/opt/erp_openclaw}"
ENV_FILE="${ERP_ENV_FILE:-$PROJECT_DIR/.env}"
SANDBOX_HEALTH_URL="${SANDBOX_HEALTH_URL:-http://172.17.0.1:18080/health}"
HTTP_PORT_VALUE="$(sed -n 's/^HTTP_PORT=//p' "$ENV_FILE" 2>/dev/null | tail -n 1)"
HTTP_PORT_VALUE="${HTTP_PORT_VALUE:-80}"
APP_HEALTH_URL="${APP_HEALTH_URL:-http://127.0.0.1:$HTTP_PORT_VALUE/health}"
WAIT_SECONDS="${WAIT_SECONDS:-180}"
DOCKER_COMMAND=(docker)

usage() {
  cat <<'EOF'
用法：
  erpctl start
  erpctl stop
  erpctl restart
  erpctl status
  erpctl health
  erpctl logs [service]

说明：
  start    启动 Docker、OpenSandbox 和全部 ERP 容器
  stop     停止 ERP 容器和 OpenSandbox，保留数据库卷
  restart  重启 OpenSandbox 和应用容器，不重启数据库
  status   查看系统服务和容器状态
  health   检查公网入口（本机）及 OpenSandbox
  logs     持续查看日志，可指定 agent-web、frontend、erp-api 等服务
EOF
}

require_runtime() {
  for command_name in curl docker sudo systemctl; do
    if ! command -v "$command_name" >/dev/null 2>&1; then
      echo "缺少命令：$command_name" >&2
      exit 1
    fi
  done

  if ! docker info >/dev/null 2>&1; then
    if sudo docker info >/dev/null 2>&1; then
      DOCKER_COMMAND=(sudo docker)
    else
      echo "当前用户无法访问 Docker daemon。" >&2
      exit 1
    fi
  fi

  if [[ ! -f "$PROJECT_DIR/compose.yaml" ]]; then
    echo "找不到 Compose 项目：$PROJECT_DIR/compose.yaml" >&2
    exit 1
  fi
  if [[ ! -f "$ENV_FILE" ]]; then
    echo "找不到环境文件：$ENV_FILE" >&2
    exit 1
  fi
}

wait_for_url() {
  local name="$1"
  local url="$2"
  local deadline=$((SECONDS + WAIT_SECONDS))

  echo "等待${name}：$url"
  while (( SECONDS < deadline )); do
    if curl --fail --silent --show-error --max-time 5 "$url" >/dev/null 2>&1; then
      echo "${name}健康检查通过。"
      return 0
    fi
    sleep 2
  done

  echo "${name}在 ${WAIT_SECONDS} 秒内未通过健康检查。" >&2
  return 1
}

compose() {
  "${DOCKER_COMMAND[@]}" compose \
    --project-directory "$PROJECT_DIR" --env-file "$ENV_FILE" "$@"
}

show_status() {
  echo "=== systemd ==="
  printf 'docker:      %s / %s\n' \
    "$(systemctl is-enabled docker 2>/dev/null || true)" \
    "$(systemctl is-active docker 2>/dev/null || true)"
  printf 'opensandbox: %s / %s\n' \
    "$(systemctl is-enabled opensandbox 2>/dev/null || true)" \
    "$(systemctl is-active opensandbox 2>/dev/null || true)"
  if systemctl cat erp-openclaw.service >/dev/null 2>&1; then
    printf 'erp-openclaw: %s / %s\n' \
      "$(systemctl is-enabled erp-openclaw 2>/dev/null || true)" \
      "$(systemctl is-active erp-openclaw 2>/dev/null || true)"
  fi

  echo
  echo "=== Docker Compose ==="
  compose ps
}

start_all() {
  sudo systemctl start docker
  sudo systemctl start opensandbox
  wait_for_url "OpenSandbox" "$SANDBOX_HEALTH_URL"

  compose config --quiet
  if systemctl cat erp-openclaw.service >/dev/null 2>&1 \
    && ! systemctl is-active --quiet erp-openclaw.service; then
    sudo systemctl start erp-openclaw.service
  else
    compose up -d --no-build
  fi
  wait_for_url "ERP" "$APP_HEALTH_URL"
  show_status
}

stop_all() {
  if systemctl cat erp-openclaw.service >/dev/null 2>&1; then
    sudo systemctl stop erp-openclaw.service
  else
    compose stop
  fi
  sudo systemctl stop opensandbox
  show_status
}

restart_apps() {
  sudo systemctl restart opensandbox
  wait_for_url "OpenSandbox" "$SANDBOX_HEALTH_URL"

  compose stop frontend agent-web erp-mcp erp-api
  compose up -d --no-build
  wait_for_url "ERP" "$APP_HEALTH_URL"
  show_status
}

health_check() {
  wait_for_url "OpenSandbox" "$SANDBOX_HEALTH_URL"
  wait_for_url "ERP" "$APP_HEALTH_URL"
  echo
  compose ps
}

main() {
  require_runtime

  case "${1:-}" in
    start)
      start_all
      ;;
    stop)
      stop_all
      ;;
    restart)
      restart_apps
      ;;
    status)
      show_status
      ;;
    health)
      health_check
      ;;
    logs)
      shift
      if [[ $# -gt 0 ]]; then
        compose logs --tail=200 --follow "$@"
      else
        compose logs --tail=200 --follow
      fi
      ;;
    -h|--help|help)
      usage
      ;;
    *)
      usage >&2
      exit 2
      ;;
  esac
}

main "$@"
