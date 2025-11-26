# 代碼功能說明: Ollama 服務安裝與啟動初始化腳本
# 創建日期: 2025-11-25 23:33 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-25 23:33 (UTC+8)
#!/usr/bin/env bash

set -euo pipefail

LOG_TAG="[ollama-bootstrap]"
INSTALL_SCRIPT_URL="${OLLAMA_INSTALL_SCRIPT_URL:-https://ollama.com/install.sh}"
OLLAMA_SERVICE_NAME="${OLLAMA_SERVICE_NAME:-ollama}"
OLLAMA_HOST="${OLLAMA_HOST:-0.0.0.0}"
OLLAMA_PORT="${OLLAMA_PORT:-11434}"
OLLAMA_DATA_DIR="${OLLAMA_DATA_DIR:-/var/lib/ollama}"
OLLAMA_USER="${OLLAMA_USER:-$(whoami)}"
OLLAMA_GROUP="${OLLAMA_GROUP:-$(id -gn "${OLLAMA_USER}")}"
WAIT_TIMEOUT_SECONDS="${WAIT_TIMEOUT_SECONDS:-60}"

log() {
  echo "${LOG_TAG} $*"
}

fail() {
  echo "${LOG_TAG} ERROR: $*" >&2
  exit 1
}

require_command() {
  local cmd=$1
  command -v "${cmd}" >/dev/null 2>&1 || fail "缺少必要指令 ${cmd}"
}

detect_platform() {
  uname -s
}

install_ollama_linux() {
  log "執行官方安裝腳本：${INSTALL_SCRIPT_URL}"
  curl -fsSL "${INSTALL_SCRIPT_URL}" | sh
}

install_ollama() {
  if command -v ollama >/dev/null 2>&1; then
    log "已找到 Ollama：$(ollama --version)"
    return
  fi

  local platform
  platform=$(detect_platform)
  case "${platform}" in
    Linux*)
      install_ollama_linux
      ;;
    Darwin*)
      fail "Darwin 平台請透過官方安裝器安裝 Ollama：https://ollama.com/download"
      ;;
    *)
      fail "暫不支援的系統：${platform}"
      ;;
  esac
}

ensure_data_dir() {
  if [[ ! -d "${OLLAMA_DATA_DIR}" ]]; then
    log "建立資料目錄 ${OLLAMA_DATA_DIR}"
    sudo mkdir -p "${OLLAMA_DATA_DIR}"
  fi

  log "設定 ${OLLAMA_DATA_DIR} 擁有者為 ${OLLAMA_USER}:${OLLAMA_GROUP}"
  sudo chown -R "${OLLAMA_USER}:${OLLAMA_GROUP}" "${OLLAMA_DATA_DIR}"
}

configure_service() {
  if ! command -v systemctl >/dev/null 2>&1; then
    log "系統不支援 systemd，略過服務設定"
    return
  fi

  log "重新啟動 ${OLLAMA_SERVICE_NAME} 並設定開機啟動"
  sudo systemctl enable "${OLLAMA_SERVICE_NAME}"
  sudo systemctl restart "${OLLAMA_SERVICE_NAME}"
}

wait_for_service() {
  require_command curl
  local attempt=0
  local url="http://${OLLAMA_HOST}:${OLLAMA_PORT}/api/version"

  log "等待 Ollama 在 ${url} 回應（最多 ${WAIT_TIMEOUT_SECONDS}s）"
  until curl -sf "${url}" >/dev/null 2>&1; do
    attempt=$((attempt + 1))
    if (( attempt >= WAIT_TIMEOUT_SECONDS )); then
      fail "Ollama 在 ${WAIT_TIMEOUT_SECONDS}s 內未回應，請檢查日誌"
    fi
    sleep 1
  done

  log "Ollama 已可回應健康檢查"
}

firewall_hint() {
  if command -v ufw >/dev/null 2>&1; then
    log "可執行 sudo ufw allow ${OLLAMA_PORT}/tcp 開啟遠端存取"
  fi
}

main() {
  require_command curl
  require_command sudo
  install_ollama
  ensure_data_dir
  configure_service
  wait_for_service
  firewall_hint
  log "Ollama 初始化完成，請使用 infra/ollama/healthcheck.sh 進一步檢查"
}

main "$@"
