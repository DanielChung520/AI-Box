# Docker 容器刪除事件記錄與防範措施

**創建日期**: 2026-01-28  
**創建人**: Daniel Chung  
**最後修改日期**: 2026-01-28  
**事件嚴重性**: 🔴 高（導致數據丟失）

---

## 📋 事件概述

### 事件時間
2026-01-28 02:28 UTC+8

### 事件描述
AI 助手在修復 SeaweedFS Filer 配置問題時，執行了 `docker stop seaweedfs-ai-box-filer && docker rm seaweedfs-ai-box-filer`，導致 Filer 元數據（`filerldb2`）丟失。

### 影響範圍
- **受影響服務**: SeaweedFS Filer (`seaweedfs-ai-box-filer`)
- **數據丟失**: Filer 元數據索引（`filerldb2`）
- **數據狀態**: 
  - ✅ Volume 節點數據仍在（28GB）
  - ✅ ArangoDB 文件元數據完整
  - ❌ Filer Web UI 無法顯示文件（元數據索引丟失）

### 根本原因
1. **配置問題**: Filer 容器未配置數據持久化 volume
2. **操作失誤**: AI 直接刪除容器，未檢查數據持久化狀態
3. **缺少規範**: 沒有明確的 Docker 容器操作禁止規範

---

## 🔧 已實施的修復措施

### 1. 修復配置（已完成）

**文件**: `docker-compose.seaweedfs.yml`

**修改內容**:
```yaml
seaweedfs-filer:
  volumes:
    - seaweedfs-ai-box-s3-config:/etc/seaweedfs
    - seaweedfs-ai-box-filer-data:/data  # ✅ 新增：持久化 Filer 元數據
```

**效果**: 以後刪除容器時，Filer 元數據會保留在 volume 中。

### 2. 更新開發規範（已完成）

#### 2.1 `.cursorrules` 更新
- ✅ 添加「Docker 容器操作禁止規範」章節
- ✅ 明確禁止刪除容器、volumes 的操作
- ✅ 定義必須執行的確認流程

#### 2.2 `AGENTS.md` 更新
- ✅ 在「代碼修改確認規範」中添加 Docker 容器操作要求
- ✅ 添加「Docker 容器操作禁止規範」章節
- ✅ 定義違規處理流程

#### 2.3 `數據備份規範.md` 更新
- ✅ 在「禁止操作」中添加 Docker 容器刪除禁令
- ✅ 明確列出關鍵服務容器

---

## 🚨 新增的防範措施

### 強制確認流程

在執行任何可能導致數據丟失的操作前，AI **必須**：

1. **檢查數據持久化狀態**
   ```bash
   docker inspect <container> --format '{{json .Mounts}}'
   ```

2. **檢查備份狀態**
   - 確認是否有最近的備份
   - 檢查備份是否完整

3. **向用戶明確說明風險**
   ```
   ⚠️ 警告：執行此操作將：
   - 操作：<具體操作>
   - 影響容器：<container_name>
   - 數據風險：<說明數據是否會丟失>
   - 備份狀態：<是否有備份>
   - 持久化狀態：<數據是否已持久化到 volume>
   
   請確認是否繼續？
   - 是（我確認已備份，繼續執行）
   - 否（取消操作）
   ```

4. **獲得用戶明確確認**
   - 必須收到用戶明確的「是」、「繼續」、「執行」等確認
   - 禁止在未獲得確認的情況下執行

### 禁止的操作清單

以下操作**嚴禁執行**（除非用戶明確要求且已確認備份）：

1. ❌ `docker rm <container_name>`
2. ❌ `docker stop <container> && docker rm <container>`
3. ❌ `docker-compose down`（會刪除容器）
4. ❌ `docker volume rm <volume_name>`
5. ❌ `docker stop arangodb`
6. ❌ `docker stop seaweedfs-ai-box-filer`
7. ❌ `docker stop qdrant`
8. ❌ `docker stop redis`

### 允許的操作清單

以下操作**允許執行**（只讀或安全操作）：

1. ✅ `docker ps` - 查看容器狀態
2. ✅ `docker logs <container>` - 查看日誌
3. ✅ `docker exec <container> <command>` - 執行只讀命令
4. ✅ `docker inspect <container>` - 查看容器配置
5. ✅ `docker restart <container>` - 重啟容器（不刪除）
6. ✅ `docker-compose restart <service>` - 重啟服務（不刪除）

---

## 📊 檢查清單

在執行任何 Docker 操作前，AI 必須檢查：

- [ ] 是否涉及刪除容器？
  - [ ] 如果是，是否已檢查數據持久化狀態？
  - [ ] 如果是，是否已檢查備份狀態？
  - [ ] 如果是，是否已向用戶說明風險？
  - [ ] 如果是，是否已獲得用戶明確確認？

- [ ] 是否涉及刪除 volume？
  - [ ] 如果是，是否已檢查備份狀態？
  - [ ] 如果是，是否已向用戶說明風險？
  - [ ] 如果是，是否已獲得用戶明確確認？

- [ ] 是否涉及停止關鍵服務？
  - [ ] 如果是，是否已向用戶說明影響？
  - [ ] 如果是，是否已獲得用戶明確確認？

---

## 🔄 恢復方案

### 當前狀態
- ✅ Volume 節點數據仍在（28GB）
- ✅ ArangoDB 文件元數據完整（包含 `storage_path`）
- ❌ Filer 元數據索引丟失（無法通過 Web UI 查看）

### 可能的恢復方案

1. **通過 API 訪問文件**（推薦）
   - 文件元數據在 ArangoDB 中，包含 `storage_path`
   - 應用程序可以通過 S3 API 直接訪問文件
   - 測試：`curl -X GET "http://localhost:8000/api/v1/files/{file_id}/download"`

2. **檢查備份**
   - 如果有 SeaweedFS 備份，可以恢復 Filer 元數據

3. **重新上傳**（最後手段）
   - 如果文件真的無法訪問，可能需要重新上傳

---

## 📝 經驗教訓

### 學到的教訓

1. **配置檢查的重要性**
   - 在刪除容器前，必須檢查數據持久化配置
   - 確保所有數據都存儲在 volume 中，而不是容器內

2. **操作確認的必要性**
   - 任何可能導致數據丟失的操作都必須獲得用戶明確確認
   - 不能假設操作是安全的

3. **規範的完整性**
   - 開發規範必須涵蓋所有危險操作
   - 需要定期更新規範，反映新的風險點

### 改進建議

1. **定期審查規範**
   - 每當發生類似事件時，更新規範
   - 確保規範覆蓋所有已知風險

2. **自動化檢查**
   - 考慮添加 pre-commit hook 檢查 Docker 操作
   - 或者在 AI 工具中添加操作驗證

3. **備份策略**
   - 確保關鍵服務有定期備份
   - 在重大操作前執行手動備份

---

## 📚 相關文檔

- [數據備份規範](../系统设计文档/核心组件/系統管理/數據備份規範.md)
- [Docker 管理說明](../系统设计文档/核心组件/系統管理/Docker管理說明.md)
- [SeaweedFS 使用指南](../系统设计文档/核心组件/系統管理/SeaweedFS使用指南.md)
- [.cursorrules](../../.cursorrules) - Docker 容器操作禁止規範
- [AGENTS.md](../../AGENTS.md) - Docker 容器操作禁止規範

---

## ✅ 驗證清單

確保以下措施已實施：

- [x] 修復 Filer 數據持久化配置
- [x] 更新 `.cursorrules` 添加禁止規範
- [x] 更新 `AGENTS.md` 添加禁止規範
- [x] 更新 `數據備份規範.md` 添加禁止操作
- [x] 創建事件記錄文檔（本文檔）
- [ ] 測試文件是否可以通過 API 正常訪問
- [ ] 檢查是否有備份可恢復

---

**最後更新日期**: 2026-01-28  
**維護人**: Daniel Chung
