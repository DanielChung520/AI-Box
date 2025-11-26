# Ollama 節點部署與驗證指南

本資料夾提供 WBS 1.5 所需的本地 LLM（Ollama）部署、啟動與健康檢查腳本，協助快速在 `olm.k84.org` 或其他節點上建置推理環境。

## 檔案說明

| 檔案 | 說明 |
|------|------|
| `bootstrap.sh` | 以官方安裝腳本建置 Ollama，設定資料目錄與 systemd 服務，確保 11434 連線正常。 |
| `healthcheck.sh` | 讀取 CPU/GPU/記憶體、磁碟、`ollama --version` 與 `ollama list`，並以 REST API 檢查健康狀態。 |

## 先決條件

1. 目標節點需支援 Bash、curl 與 sudo。
2. Linux 節點可直接透過官方 `install.sh` 自動安裝；macOS 節點需先手動安裝後再執行健康檢查。
3. 預設資料目錄為 `/var/lib/ollama`，可透過環境變數 `OLLAMA_DATA_DIR` 覆寫。

## 部署流程

```bash
ssh <user>@olm.k84.org
git clone git@github.com:DanielChung520/AI-Box.git
cd AI-Box/infra/ollama
./bootstrap.sh
```

成功後可透過 `curl http://olm.k84.org:11434/api/version` 驗證 API 是否就緒。

## 健康檢查與報告

`healthcheck.sh` 會輸出硬體與服務狀態，可搭配 `scripts/verify_env.sh` 自動產出 `docs/deployment/ollama-health-report.md`：

```bash
cd /path/to/AI-Box
./scripts/verify_env.sh
```

如需單獨檢查遠端節點，可指定主機與端口：

```bash
OLLAMA_HOST=olm.k84.org OLLAMA_PORT=11434 infra/ollama/healthcheck.sh
```

## 常見問題

- **服務無法啟動**：確認 `sudo systemctl status ollama` 日誌，並檢查 `OLLAMA_DATA_DIR` 是否具備讀寫權限。
- **遠端無法連線**：確保防火牆開啟 `11434/tcp`；腳本會於安裝後提示 `ufw` 設定建議。
- **模型下載緩慢**：建議先在低峰期透過 `scripts/ollama_sync_models.py`（步驟 2）下載所需 baseline 與 fallback 模型，再同步至其他節點。
