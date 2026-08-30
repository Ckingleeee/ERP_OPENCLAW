#!/usr/bin/env bash

set -Eeuo pipefail

PROJECT_DIR="${PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
ENV_FILE="${ENV_FILE:-$PROJECT_DIR/.env}"
VALIDATOR="$PROJECT_DIR/scripts/validate-docker-env.py"
INSTALL_DIR="${OPENSANDBOX_INSTALL_DIR:-/opt/opensandbox-server}"
CONFIG_DIR="${OPENSANDBOX_CONFIG_DIR:-/etc/opensandbox}"
CONFIG_FILE="$CONFIG_DIR/config.toml"
STATE_DIR="${OPENSANDBOX_STATE_DIR:-/var/lib/opensandbox}"
SERVICE_FILE="/etc/systemd/system/opensandbox.service"
PORT="${OPENSANDBOX_PORT:-18080}"

log() {
  printf '[OpenSandbox] %s\n' "$*"
}

die() {
  printf '[OpenSandbox] 错误：%s\n' "$*" >&2
  exit 1
}

env_get() {
  python3 "$VALIDATOR" "$ENV_FILE" --get "$1" 2>/dev/null || true
}

wait_for_health() {
  local url="$1"
  local deadline=$((SECONDS + 120))
  while (( SECONDS < deadline )); do
    if curl --fail --silent --show-error --max-time 5 "$url" >/dev/null 2>&1; then
      log "健康检查通过：$url"
      return 0
    fi
    sleep 2
  done
  systemctl status opensandbox --no-pager -l || true
  journalctl -u opensandbox -n 100 --no-pager || true
  die "服务在 120 秒内未通过健康检查"
}

if [[ $EUID -ne 0 ]]; then
  die "请使用 sudo 执行此脚本"
fi

[[ -f "$ENV_FILE" ]] || die "找不到 $ENV_FILE"
[[ -f "$VALIDATOR" ]] || die "找不到环境校验脚本"
command -v docker >/dev/null 2>&1 || die "Docker 尚未安装"

source /etc/os-release
if [[ "${ID:-}" != "ubuntu" && "${ID:-}" != "debian" ]]; then
  die "当前只支持 Ubuntu/Debian，检测到：${ID:-unknown}"
fi

log "安装 Python 运行环境"
apt-get -o Acquire::Retries=5 update
DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
  python3 python3-venv ca-certificates curl

server_version="$(env_get OPENSANDBOX_SERVER_VERSION)"
server_version="${server_version:-0.2.2}"
pip_index_url="$(env_get PIP_INDEX_URL)"
pip_index_url="${pip_index_url:-https://pypi.org/simple}"
pip_trusted_host="$(env_get PIP_TRUSTED_HOST)"

install -d -m 0755 "$INSTALL_DIR"
if [[ ! -x "$INSTALL_DIR/.venv/bin/python" ]]; then
  python3 -m venv "$INSTALL_DIR/.venv"
fi

pip_args=(--index-url "$pip_index_url" --retries 5 --timeout 60)
if [[ -n "$pip_trusted_host" ]]; then
  pip_args+=(--trusted-host "$pip_trusted_host")
fi

log "安装 opensandbox-server==$server_version"
"$INSTALL_DIR/.venv/bin/python" -m pip install "${pip_args[@]}" --upgrade pip
"$INSTALL_DIR/.venv/bin/python" -m pip install \
  "${pip_args[@]}" "opensandbox-server==$server_version"

bridge_ip="$(docker network inspect bridge --format '{{(index .IPAM.Config 0).Gateway}}')"
[[ -n "$bridge_ip" ]] || die "无法读取 Docker bridge 网关"

install -d -m 0700 "$CONFIG_DIR" "$STATE_DIR"
if [[ ! -f "$CONFIG_FILE" ]]; then
  temporary_config="$(mktemp)"
  "$INSTALL_DIR/.venv/bin/opensandbox-server" \
    init-config "$temporary_config" --example docker --force
  install -m 0600 "$temporary_config" "$CONFIG_FILE"
  rm -f "$temporary_config"
else
  cp "$CONFIG_FILE" "$CONFIG_FILE.bak.$(date +%Y%m%d-%H%M%S)"
fi

OPEN_SANDBOX_KEY="$(env_get OPEN_SANDBOX_API_KEY)"
[[ -n "$OPEN_SANDBOX_KEY" ]] || die "OPEN_SANDBOX_API_KEY 未配置"
export OPEN_SANDBOX_KEY CONFIG_FILE bridge_ip PORT

python3 - <<'PY'
import json
import os
import re
from pathlib import Path

path = Path(os.environ["CONFIG_FILE"])
text = path.read_text(encoding="utf-8")
match = re.search(r"(?ms)^\[server\]\s*$.*?(?=^\[|\Z)", text)
if not match:
    raise SystemExit("OpenSandbox 配置缺少 [server] 段")

block = match.group(0).rstrip() + "\n"

def set_value(source: str, key: str, value: str) -> str:
    pattern = rf"(?m)^\s*{re.escape(key)}\s*=.*$"
    replacement = f"{key} = {value}"
    if re.search(pattern, source):
        return re.sub(pattern, replacement, source, count=1)
    return source.rstrip() + "\n" + replacement + "\n"

block = set_value(block, "host", json.dumps(os.environ["bridge_ip"]))
block = set_value(block, "port", str(int(os.environ["PORT"])))
block = set_value(block, "api_key", json.dumps(os.environ["OPEN_SANDBOX_KEY"]))
path.write_text(text[: match.start()] + block + text[match.end() :], encoding="utf-8")
PY

unset OPEN_SANDBOX_KEY
chmod 600 "$CONFIG_FILE"

cat >"$SERVICE_FILE" <<EOF
[Unit]
Description=OpenSandbox Lifecycle Server
Requires=docker.service
After=network-online.target docker.service
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=$STATE_DIR
Environment=HOME=$STATE_DIR
Environment=SANDBOX_CONFIG_PATH=$CONFIG_FILE
ExecStart=$INSTALL_DIR/.venv/bin/opensandbox-server --config $CONFIG_FILE
Restart=always
RestartSec=5
TimeoutStartSec=180
LimitNOFILE=1048576

[Install]
WantedBy=multi-user.target
EOF

chmod 644 "$SERVICE_FILE"
systemctl daemon-reload
systemctl enable --now opensandbox

if command -v ufw >/dev/null 2>&1 && ufw status | grep -q '^Status: active'; then
  if ! ufw status | grep -Fq "$bridge_ip $PORT/tcp"; then
    ufw allow from 172.16.0.0/12 to "$bridge_ip" port "$PORT" proto tcp \
      comment 'OpenSandbox from Docker networks'
  fi
fi

wait_for_health "http://$bridge_ip:$PORT/health"

sandbox_image="$(env_get OPEN_SANDBOX_IMAGE)"
if [[ -n "$sandbox_image" ]]; then
  log "预拉取沙箱镜像：$sandbox_image"
  docker pull "$sandbox_image"
fi

log "安装完成，监听地址仅限 Docker 网关：http://$bridge_ip:$PORT"
