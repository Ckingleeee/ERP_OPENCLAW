#!/usr/bin/env bash

set -Eeuo pipefail

FOLLOW_LOGS=false

usage() {
  cat <<'EOF'
用法：
  ./scripts/restart-agent-web.sh [--follow]

该命令是兼容入口。Docker 部署统一使用 erpctl 管理，本脚本会重启
OpenSandbox 及 ERP 应用容器，但不会重启 MySQL/MongoDB。
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -f|--follow)
      FOLLOW_LOGS=true
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
  shift
done

if ! command -v erpctl >/dev/null 2>&1; then
  echo "找不到 erpctl，请先执行一键部署脚本。" >&2
  exit 1
fi

erpctl restart

if [[ "$FOLLOW_LOGS" == true ]]; then
  exec erpctl logs agent-web
fi
