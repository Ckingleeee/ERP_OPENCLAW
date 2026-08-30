#!/usr/bin/env bash

set -Eeuo pipefail

SERVICE_NAME="${SERVICE_NAME:-agent-web}"
HEALTH_URL="${HEALTH_URL:-http://127.0.0.1:8090/health}"
WAIT_SECONDS="${WAIT_SECONDS:-120}"
FOLLOW_LOGS=false

usage() {
  cat <<'EOF'
用法：
  ./scripts/restart-agent-web.sh [--follow]

选项：
  -f, --follow  健康检查通过后持续跟踪服务日志，按 Ctrl+C 退出
  -h, --help    显示帮助

可选环境变量：
  SERVICE_NAME  systemd 服务名，默认 agent-web
  HEALTH_URL    健康检查地址，默认 http://127.0.0.1:8090/health
  WAIT_SECONDS  最长等待时间（秒），默认 120
EOF
}

show_failure_details() {
  echo
  echo "服务启动失败，当前状态："
  sudo systemctl status "$SERVICE_NAME" --no-pager -l || true
  echo
  echo "最近 80 行日志："
  sudo journalctl -u "$SERVICE_NAME" -n 80 --no-pager || true
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -f|--follow)
      FOLLOW_LOGS=true
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "未知参数：$1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if ! [[ "$WAIT_SECONDS" =~ ^[1-9][0-9]*$ ]]; then
  echo "WAIT_SECONDS 必须是正整数，当前值：$WAIT_SECONDS" >&2
  exit 2
fi

for command_name in sudo systemctl journalctl curl; do
  if ! command -v "$command_name" >/dev/null 2>&1; then
    echo "缺少命令：$command_name" >&2
    exit 1
  fi
done

if ! sudo systemctl cat "$SERVICE_NAME" >/dev/null 2>&1; then
  echo "systemd 服务不存在：$SERVICE_NAME" >&2
  exit 1
fi

echo "正在重启 $SERVICE_NAME..."
if ! sudo systemctl restart "$SERVICE_NAME"; then
  show_failure_details
  exit 1
fi

echo "正在等待健康检查：$HEALTH_URL"
deadline=$((SECONDS + WAIT_SECONDS))
while (( SECONDS < deadline )); do
  if ! sudo systemctl is-active --quiet "$SERVICE_NAME"; then
    show_failure_details
    exit 1
  fi

  if curl --fail --silent --show-error --max-time 3 "$HEALTH_URL" >/dev/null 2>&1; then
    echo "$SERVICE_NAME 已启动，健康检查通过。"
    sudo systemctl status "$SERVICE_NAME" --no-pager -l

    if [[ "$FOLLOW_LOGS" == true ]]; then
      echo
      echo "正在持续跟踪日志，按 Ctrl+C 退出："
      exec sudo journalctl -u "$SERVICE_NAME" -f
    fi

    echo
    echo "最近 20 行日志："
    sudo journalctl -u "$SERVICE_NAME" -n 20 --no-pager
    exit 0
  fi

  sleep 2
done

echo "等待 ${WAIT_SECONDS} 秒后健康检查仍未通过。" >&2
show_failure_details
exit 1
