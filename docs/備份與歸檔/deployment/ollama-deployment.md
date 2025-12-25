<!--
代碼功能說明: Ollama 部署與模型管理指南
創建日期: 2025-11-25 23:40 (UTC+8)
創建人: Daniel Chung
最後修改日期: 2025-11-25 23:40 (UTC+8)
-->

# Ollama 節點部署與模型管理

本文件說明如何在 `olm.k84.org` 或任一推理節點部署 Ollama、同步 baseline/fallback 模型，以及如何記錄健康狀態。

## 1. 節點準備

1. 依 `infra/ollama/README.md` 透過 `bootstrap.sh` 建置服務、`healthcheck.sh` 驗證。
2. 執行 `scripts/verify_env.sh` 產出 `docs/deployment/ollama-health-report.md`，確認 CPU 64 GB RAM、>700 GB 可用儲存等閾值。
3. 若部署於新節點，請在 `.env`（未版控）新增：

```env
# 將此片段加入本機 .env
OLLAMA_REMOTE_HOST=olm.k84.org
OLLAMA_REMOTE_PORT=11434
OLLAMA_SSH_USER=deploy
OLLAMA_SSH_KEY_PATH=~/.ssh/olm_k84
```

> `.env` 僅存放憑證與帳號；非敏感參數放 `config/config.json`。

## 2. `config.json` 整合

`config/config.example.json` 已新增 `services.ollama` 與 `jobs.ollama_sync`：

```json
"services": {
  "ollama": {
    "scheme": "http",
    "host": "olm.k84.org",
    "port": 11434,
    "health_timeout": 10,
    "baseline_models": ["gpt-oss:20b", "qwen3-coder:30b"],
    "fallback_models": ["llama3.1:8b", "mistral-nemo:12b"],
    "download": {
      "data_root": "~/.ollama",
      "retry": { "max_attempts": 3, "backoff_seconds": 20 },
      "allowed_window": "02:00-06:00 UTC+8",
      "max_parallel_jobs": 1
    }
  }
},
"jobs": {
  "ollama_sync": {
    "enabled": true,
    "schedule_cron": "0 3 * * *",
    "manifest_path": "docs/deployment/ollama-models-manifest.json"
  }
}
```

> 將 example 複製為 `config/config.json` 後，可依環境調整 host/port 或控制 baseline 清單。

## 3. 模型同步流程

1. **設定環境**：於節點載入 `.env`（提供 SSH/Token），並確保 `ollama` CLI 可存取。
2. **執行腳本**：

```bash
python scripts/ollama_sync_models.py --skip-existing
# 僅於本機產生 manifest（不下載）：
python scripts/ollama_sync_models.py --skip-existing --no-download --host localhost
```

- 預設會讀取 `config/config.json` 的 baseline + fallback 清單。
- 可用 `--models llama3.1:8b` 覆蓋，或 `--dry-run` 單純檢閱。
- 若環境禁止下載（例如 CI 或備援節點），可使用 `--no-download` 只收集 digest 與 manifest。
- 報告輸出到 `docs/deployment/ollama-models-manifest.json`，含 digest 與節點資訊。

3. **排程建議**：透過 `crontab -e` 建立條目，每日 03:00 自動同步：

```
0 3 * * * cd /opt/AI-Box && /usr/bin/python3 scripts/ollama_sync_models.py --skip-existing >> /var/log/ollama_sync.log 2>&1
```

## 4. 驗證、API 與稽核

- `scripts/verify_env.sh`：生成硬體報告與 `ollama list` 快照。
- `infra/ollama/healthcheck.sh`：遠端檢查 `OLLAMA_HOST:PORT/api/version`、列出模型。
- `services/api/routers/llm.py`：提供 `/api/v1/llm/generate|chat|embeddings`，統一封裝 Ollama REST API。
- `services/api/core/llm_router.py`（與 `llm/router.py`）：依 `config.services.ollama.nodes` 執行輪詢/加權與節點冷卻。
- `scripts/smoke_test.py`：可透過環境變數 `SMOKE_TEST_LLM_PROMPT` 自動打 `LLM` 端點；若要直接檢查節點則設置 `SMOKE_TEST_OLLAMA_HOST/PORT`。
- `docs/deployment/ollama-health-report.md`：最新一次健康檢查紀錄。
- `docs/deployment/ollama-models-manifest.json`：同步腳本輸出的模型摘要，可附在 WBS 1.5 驗收報告。

## 5. 故障排除

| 問題 | 排除步驟 |
|------|----------|
| 模型下載中斷 | `ollama pull` 具備斷點續傳，腳本會自動重試 3 次，並於 log 中顯示 backoff。 |
| API 無回應 | 先執行 `systemctl status ollama`，再用 `healthcheck.sh` 確認 host/port 是否一致。 |
| 容量警示 | 檢查 `docs/deployment/ollama-health-report.md` 的「容量閾值對照」，必要時清理舊模型或擴充磁碟。 |
| 單一節點過載 | 在 `config.services.ollama.nodes` 中加入/調整節點與 `weight`，重新啟動 API 即可生效，負載均衡器會自動跳過失敗節點並在冷卻後重試。 |

完成以上步驟後，即可進入 WBS 1.5.3 的 API 封裝工作。
