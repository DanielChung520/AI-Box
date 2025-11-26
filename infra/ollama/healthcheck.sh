# 代碼功能說明: 檢查 Ollama 節點健康狀態與硬體資源的腳本
# 創建日期: 2025-11-25 23:33 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-25 23:33 (UTC+8)
#!/usr/bin/env bash

set -euo pipefail

LOG_TAG="[ollama-healthcheck]"
OLLAMA_HOST="${OLLAMA_HOST:-localhost}"
OLLAMA_PORT="${OLLAMA_PORT:-11434}"
OUTPUT_FORMAT="${OUTPUT_FORMAT:-table}"
TIMEOUT_SECONDS="${TIMEOUT_SECONDS:-5}"

log() {
  echo "${LOG_TAG} $*"
}

fail() {
  echo "${LOG_TAG} ERROR: $*" >&2
  exit 1
}

collect_cpu_info() {
  local platform
  platform=$(uname -s)
  if [[ "${platform}" == "Darwin" ]]; then
    sysctl -n machdep.cpu.brand_string
  elif command -v lscpu >/dev/null 2>&1; then
    lscpu | awk -F': +' '/Model name/ {print $2; exit}'
  else
    echo "Unknown CPU"
  fi
}

collect_mem_total() {
  local platform
  platform=$(uname -s)
  if [[ "${platform}" == "Darwin" ]]; then
    local bytes
    bytes=$(sysctl -n hw.memsize)
    awk -v b="${bytes}" 'BEGIN { printf "%.2f GiB", b/1024/1024/1024 }'
  elif [[ -r /proc/meminfo ]]; then
    awk '/MemTotal/ { printf "%.2f GiB", $2/1024/1024 }' /proc/meminfo
  else
    echo "Unknown"
  fi
}

collect_gpu_info() {
  if command -v nvidia-smi >/dev/null 2>&1; then
    nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
  elif [[ "$(uname -s)" == "Darwin" ]]; then
    system_profiler SPDisplaysDataType | awk -F': ' '/Chipset Model/ {print $2; exit}'
  else
    echo "Unknown GPU"
  fi
}

collect_disk_info() {
  local mount_point="${1:-/}"
  df -h "${mount_point}" | awk 'NR==1 || NR==2 {print}'
}

check_service() {
  if ! command -v curl >/dev/null 2>&1; then
    log "缺少 curl 無法檢查 API"
    return 1
  fi

  local url="http://${OLLAMA_HOST}:${OLLAMA_PORT}/api/version"
  if curl -sf --max-time "${TIMEOUT_SECONDS}" "${url}" >/dev/null 2>&1; then
    echo "OK"
  else
    echo "UNREACHABLE"
  fi
}

collect_ollama_version() {
  if command -v ollama >/dev/null 2>&1; then
    ollama --version
  else
    echo "ollama command not found"
  fi
}

collect_model_list() {
  if command -v ollama >/dev/null 2>&1; then
    ollama list || true
  else
    echo "N/A - ollama command not found"
  fi
}

print_table() {
  printf "\n"
  printf "Ollama 節點健康檢查\n"
  printf "====================\n"
  printf "時間：%s\n" "$(date '+%Y-%m-%d %H:%M:%S %Z')"
  printf "API 位址：%s:%s\n" "${OLLAMA_HOST}" "${OLLAMA_PORT}"
  printf "\n"
  printf "硬體資訊\n"
  printf "--------\n"
  printf "CPU：%s\n" "$(collect_cpu_info)"
  printf "記憶體：%s\n" "$(collect_mem_total)"
  printf "GPU：%s\n" "$(collect_gpu_info)"
  printf "\n"
  printf "磁碟（根目錄）\n"
  collect_disk_info "/"
  printf "\n"
  printf "Ollama 服務\n"
  printf "-----------\n"
  printf "CLI 版本：%s\n" "$(collect_ollama_version)"
  printf "健康檢查：%s\n" "$(check_service)"
  printf "\n"
  printf "模型列表\n"
  printf "--------\n"
  collect_model_list
}

case "${OUTPUT_FORMAT}" in
  table)
    print_table
    ;;
  *)
    fail "不支援的輸出格式：${OUTPUT_FORMAT}"
    ;;
esac
