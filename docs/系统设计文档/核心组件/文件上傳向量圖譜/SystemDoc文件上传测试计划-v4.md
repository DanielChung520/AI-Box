# SystemDocs 文件上傳測試計劃 v4.0

**創建日期**: 2026-01-20
**創建人**: Daniel Chung
**最後修改日期**: 2026-01-21 10:35 UTC+8

---

---

## ⚠️ 測試前環境檢查（重要提醒！）

每次重新測試前，請務必執行以下環境檢查：

### 1. 檢查服務狀態

```bash
# 檢查所有系統服務狀態
./scripts/start_services.sh status
```

**必要服務**：

- ✅ ArangoDB (端口 8529)
- ✅ Qdrant (端口 6333)
- ✅ SeaweedFS (端口 8333, 8888)
- ✅ Redis (端口 6379)
- ✅ Ollama (端口 11434)

### 2. 清理測試數據

執行清理腳本確保從乾淨狀態開始：

```bash
# 預覽清理內容（不實際刪除）
python3 scripts/cleanup_test_data.py --dry-run

# 執行清理
python3 scripts/cleanup_test_data.py
```

**清理腳本位置**：`scripts/cleanup_test_data.py`

**清理內容**：

主要是前次測試輪的記錄、collection、文檔，請注意不要誤刪其他文件

- ArangoDB: `user_tasks`, `file_metadata`, `entities`, `relations`
- Qdrant: `file_*` collections
- SeaweedFS: `tasks/SystemDocs/` 文件

### 3. 測試腳本位置

**通用測試腳本**：`scripts/test_file_upload.py`

```bash
# 使用預設配置
python3 scripts/test_file_upload.py

# 自定義配置
python3 scripts/test_file_upload.py --task-id SystemDocs --files "file1.md,file2.md" --workers 3
```

## 📝 每輪測試後必須更新測試記錄（重要提醒！）

**重要**：每完成一輪測試後，請在下方「測試輪記錄表」中更新測試記錄與狀態說明：

| 欄位             | 說明                                 |
| ---------------- | ------------------------------------ |
| **總耗時** | 從清理數據到處理完成的總時間（分鐘） |
| **成功率** | 成功處理檔數 / 總檔數（百分比）      |
| **備註**   | 錯誤信息、調整記錄、特殊情況         |

### 測試輪記錄表

| 輪次    | 日期       | 文件數 | 成功 | 失敗 | 總耗時   | 成功率 | 備註（錯誤/調整） |
| ------- | ---------- | ------ | ---- | ---- | -------- | ------ | ----------------- |
| Round 0 | 2026-01-20 | 1 | 1 | 0 | ~1 分鐘 | 100% | 初始環境驗證成功 |
| Round 1 | 2026-01-21 | 6 | 1 | 0 | ~15 分鐘 | 17% | 實體:22 關係:23, 4個KG仍在處理中, 1個重新上傳後完成 |
| Round 2 | ___        | ___    | ___  | ___  | ___ 分鐘 | ___%   | ___               |
| Round 3 | ___        | ___    | ___  | ___  | ___ 分鐘 | ___%   | ___               |
| Round 4 | ___        | ___    | ___  | ___  | ___ 分鐘 | ___%   | ___               |

### 更新方式

1. 執行測試腳本：`python3 scripts/test_file_upload.py --timing`
2. 記錄輸出結果
3. 更新本表的「輪次」下一行

---

## 📋 計劃概述

### v4.0 更新說明

**2026-01-20**：向量數據庫從 ChromaDB 遷移到 Qdrant

| 項目          | v3.x (ChromaDB)         | v4.0 (Qdrant)                      |
| ------------- | ----------------------- | ---------------------------------- |
| 向量數據庫    | ChromaDB                | ✅ Qdrant                          |
| REST API 端口 | 8001                    | 6333                               |
| gRPC API 端口 | -                       | 6334                               |
| Dashboard     | 無                      | ✅ <http://localhost:6333/dashboard> |
| 配置來源      | `datastores.chromadb` | `datastores.qdrant`              |

### 測試目的

1. **驗證資料上傳的正確性**

   - 確保文件能夠正確上傳到 SeaWeedFS
   - 確保文件元數據正確存儲到 ArangoDB
   - 確保處理流程（分塊、向量化、圖譜提取）正確執行
2. **讓 AI 能檢索及推斷系統**

   - 驗證向量化數據正確存儲到 Qdrant
   - 驗證知識圖譜數據正確存儲到 ArangoDB
   - 驗證 HybridRAG 檢索功能正常運作

### 測試範圍

- **目標任務**: `systemAdmin_SystemDocs`
- **目標文件**: `docs/系統設計文檔/` 目錄下的 Markdown 文件
- **處理階段**:
  - 1. 文件上傳與存儲
  - 2. 文件分塊（Chunking）
  - 3. 向量化（Vectorization）
  - 4. 知識圖譜提取（Knowledge Graph Extraction）

---

## 🎯 測試階段

### 第一階段：準備工作

#### 1.1 環境確認

**檢查項目**：

- [ ] ArangoDB 運行正常（端口 8529）
- [ ] **Qdrant 運行正常（端口 6333）**
- [ ] SeaWeedFS 運行正常（端口 8333、8888）
- [ ] Redis 運行正常（端口 6379）
- [ ] RQ Worker 運行正常
- [ ] Ollama 運行正常（端口 11434）

**檢查命令**：

```bash
# 檢查服務狀態
ps aux | grep -E "arangodb|qdrant|seaweed|redis|rq|ollama" | grep -v grep

# 檢查 Qdrant 健康
curl -s http://localhost:6333/health

# 檢查 Qdrant Collections
curl -s http://localhost:6333/collections | python3 -c "import sys,json; print(json.load(sys.stdin))"

# 檢查 API 響應
curl -s http://localhost:8000/api/v1/health | python3 -c "import sys,json; print(json.load(sys.stdin))"
```

#### 1.2 數據清理（確保從乾淨狀態開始）

**清理內容**：

- [ ] SeaWeedFS `bucket-ai-box-assets/tasks/SystemDocs/` 中的舊文件
- [ ] ArangoDB `user_tasks`、`file_metadata`、`entities`、`relations`
- [ ] **Qdrant 中的測試 collections**
- [ ] Redis 中的處理狀態

**清理工具**（推薦使用）：

使用 `scripts/cleanup_test_data.py` 腳本進行一鍵清理：

```bash
# 預覽清理內容（不實際刪除）
python3 scripts/cleanup_test_data.py --dry-run

# 執行清理（需要確認）
python3 scripts/cleanup_test_data.py

# 直接執行（不詢問，危險！）
python3 scripts/cleanup_test_data.py --yes
```

**清理腳本功能**：

- ✅ 清理 ArangoDB `user_tasks`、`file_metadata`、`entities`、`relations`
- ✅ 清理 Qdrant `file_*` collections
- ✅ 清理 SeaweedFS `tasks/SystemDocs/` 文件
- ✅ 預覽模式（dry-run）
- ✅ 確認機制防止誤刪

**清理腳本位置**：`scripts/cleanup_test_data.py`

**手動清理命令**（備選方案）：

```bash
# 清理 SeaweedFS（舊方式）
docker exec seaweedfs-ai-box-volume sh -c 'rm -f /var/lib/seaweedfs/bucket-ai-box-assets_*.* 2>/dev/null; echo "SeaWeedFS 清理完成"'
```

#### 1.3 測試記錄

| 項目             | 數值       | 備註                |
| ---------------- | ---------- | ------------------- |
| 測試日期         | 2026-01-20 |                     |
| ArangoDB         | ✅ 正常    | port 8529           |
| **Qdrant** | ✅ 正常    | **port 6333** |
| SeaWeedFS        | ✅ 正常    | port 8333, 8888     |
| Redis            | ✅ 正常    | port 6379           |
| Ollama           | ✅ 正常    | port 11434          |

---

### 第二階段：單一文件測試

#### 2.1 測試目標

驗證完整處理流程能夠正常運作。

#### 2.2 測試步驟

1. **選擇測試文件**

   ```
   推薦：`docs/系統設計文檔/README.md`
   原因：文件較小，內容簡單，適合快速驗證
   ```

2. **執行上傳**

   ```bash
   # 使用前端界面上傳，或使用 API
   curl -X POST "http://localhost:8000/api/v1/files/v2/upload" \
     -F "files=@docs/系統設計文檔/README.md" \
     -F "task_id=systemAdmin_SystemDocs"
   ```

3. **監控處理狀態**

   ```bash
   # 檢查處理狀態
   curl "http://localhost:8000/api/v1/files/{file_id}/processing-status"
   ```

4. **驗證結果**

   **SeaWeedFS 存儲**：

   ```python
   # 驗證文件已存儲
   import boto3
   s3 = boto3.client('s3', endpoint_url='http://localhost:8333', ...)
   response = s3.list_objects_v2(Bucket='bucket-ai-box-assets')
   # 確認文件存在
   ```

   **ArangoDB 元數據**：

   ```python
   # 驗證元數據
   from arango import ArangoClient
   client = ArangoClient(hosts='http://localhost:8529')
   db = client.db('ai_box_kg', ...)
   doc = db.collection('file_metadata').get(file_id)
   assert doc['status'] == 'processed'
   assert doc['chunk_count'] > 0
   assert doc['vector_count'] > 0
   assert doc['kg_status'] == 'completed'
   ```

   **Qdrant 向量**：

   ```python
   # 驗證向量
   from qdrant_client import QdrantClient

   client = QdrantClient(host='localhost', port=6333)

   # 檢查 Collection 是否存在
   collection_name = f'file_{file_id}'
   collection_info = client.get_collection(collection_name)

   # 查詢向量
   results = client.query_points(
       collection_name=collection_name,
       query=[0.1] * 768,  # 示例查詢向量
       limit=5,
       with_payload=True,
   )

   assert len(results.points) > 0
   ```

   **Qdrant Dashboard 驗證**：

   ```
   訪問 http://localhost:6333/dashboard
   查看 Collection: file_{file_id}
   確認向量數量和狀態
   ```

   **ArangoDB 知識圖譜**：

   ```python
   # 驗證實體
   entities = list(db.collection('entities').find({'file_id': file_id}))
   assert len(entities) > 0

   # 驗證關係
   relations = list(db.collection('relations').find({'file_id': file_id}))
   assert len(relations) > 0
   ```

#### 2.3 記錄模板

| 項目                        | 數值   | 備註               |
| --------------------------- | ------ | ------------------ |
| 測試文件                    |        |                    |
| 文件大小                    | ___ KB |                    |
| 上傳狀態                    | ✅/❌  |                    |
| 分塊數量                    | ___ 個 |                    |
| 向量數量                    | ___ 個 |                    |
| 實體數量                    | ___ 個 |                    |
| 關係數量                    | ___ 個 |                    |
| 處理時間                    | ___ 秒 |                    |
| 使用的 Ontology             |        | Base/Domain/Major  |
| **Qdrant Collection** |        | `file_{file_id}` |

#### 2.4 測試記錄

| 項目                             | 數值                                                                    | 備註                                    |
| -------------------------------- | ----------------------------------------------------------------------- | --------------------------------------- |
| 測試日期                         | 2026-01-20                                                              |                                         |
| 測試文件                         | `docs_system_design_README.md`                                        | 從 `docs/系統設計文檔/README.md` 複製 |
| 文件大小                         | 18.41 KB                                                                |                                         |
| File ID                          | `cc3d7aee-b5b3-4e11-9458-784575c1dba6`                                | 上傳成功                                |
| S3 Path                          | `s3://bucket-ai-box-assets/tasks/systemAdmin_SystemDocs/cc3d7aee-...` |                                         |
| 上傳狀態                         | ✅ 成功                                                                 | API:`/api/v1/files/v2/upload`         |
| 上傳時間                         | 0.14 秒                                                                 |                                         |
| 任務 ID                          | `systemAdmin_SystemDocs`                                              |                                         |
| 文件夾                           | `systemAdmin_SystemDocs_workspace`                                    |                                         |
| **Qdrant Collection**      | `file_cc3d7aee-b5b3-4e11-9458-784575c1dba6`                           | ✅ 正常                                 |
| **Qdrant 向量數量**        | 11 個                                                                   | ✅                                      |
| **Qdrant Collection 狀態** | green                                                                   | ✅                                      |

**測試腳本**： `scripts/test_file_upload_phase2.py`

---

### 第三階段：批量文件測試（5 個文件）

#### 3.1 測試目標

驗證 RQ 任務排程和並發處理能力。

#### 3.2 測試文件選擇

```
選擇標準：
- 涵蓋不同類型的文檔（架構、API、流程）
- 文件大小適中（5-30KB）
- 能夠匹配到現有的 Ontology

推薦文件列表：
1. docs/系統設計文檔/README.md
2. docs/系統設計文檔/核心組件/IEE對話式開發文件編輯/README.md
3. docs/系統設計文檔/核心組件/MCP工具/README.md
4. docs/系統設計文檔/核心組件/系統管理/README.md
5. docs/系統設計文檔/核心組件/README.md
```

#### 3.3 執行步驟

**方法一：使用自動化測試腳本（推薦）**

使用 `scripts/test_file_upload.py` 腳本進行自動化測試：

```bash
# 設置 API Token（如果需要認證）
export API_TOKEN="your_api_token_here"

# 執行測試腳本（使用預設配置）
python3 scripts/test_file_upload.py

# 或自定義配置
python3 scripts/test_file_upload.py --task-id SystemDocs --workers 3
```

**測試腳本功能**：

- ✅ 自動檢查服務狀態（ArangoDB、Qdrant、API）
- ✅ 自動啟動 3 個 RQ Worker
- ✅ 批量上傳 5 個測試文件
- ✅ 自動監控處理進度
- ✅ 生成測試摘要報告
- ✅ 測試完成後自動停止 Worker

**測試腳本完整代碼**：

```python
#!/usr/bin/env python3
# 代碼功能說明: 第三階段批量文件上傳測試腳本（5個文件）
# 創建日期: 2026-01-21 04:21 UTC+8
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-21 04:21 UTC+8

"""
第三階段批量文件上傳測試腳本

用於測試 SystemDoc 文件上傳功能的第三階段（5個文件批量測試）
驗證 RQ 任務排程和並發處理能力

要求：
- 測試用戶：systemAdmin
- 任務名稱：SystemDocs
- 開啟3個批量RQ Worker
"""

import json
import os
import sys
import time
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

import httpx
from arango import ArangoClient
from qdrant_client import QdrantClient

# 配置
BASE_DIR = Path(__file__).resolve().parent.parent
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
API_PREFIX = "/api/v1"
TASK_ID = "SystemDocs"  # 任務名稱
USER_ID = "systemAdmin"  # 測試用戶

# 測試文件列表（選擇不同類型的文檔，不全是README）
TEST_FILES = [
    "docs/系统设计文档/安全架构说明.md",
    "docs/系统设计文档/IEE前端系統/IEE前端系统.md",
    "docs/系统设计文档/核心组件/MCP工具/MCP工具.md",
    "docs/系统设计文档/核心组件/Agent平台/Data-Agent-規格書.md",
    "docs/系统设计文档/核心组件/語義與任務分析/AI-Box語義與任務v4重構計劃.md",
]

# 數據庫配置
ARANGO_HOST = os.getenv("ARANGO_HOST", "http://localhost:8529")
ARANGO_DB = os.getenv("ARANGO_DB", "ai_box_kg")
ARANGO_USERNAME = os.getenv("ARANGO_USERNAME", "root")
ARANGO_PASSWORD = os.getenv("ARANGO_PASSWORD", "changeme")

QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))

# RQ Worker 配置
RQ_QUEUE = "file_processing"
NUM_WORKERS = 3  # 開啟3個批量RQ Worker


def print_header(title: str) -> None:
    """打印標題"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_status(message: str, status: str = "INFO") -> None:
    """打印狀態信息"""
    status_symbols = {
        "INFO": "ℹ️",
        "SUCCESS": "✅",
        "ERROR": "❌",
        "WARNING": "⚠️",
    }
    symbol = status_symbols.get(status, "ℹ️")
    print(f"{symbol} {message}")


def check_services() -> bool:
    """檢查服務狀態"""
    print_header("1. 環境確認")

    # 檢查文件是否存在
    print_status("檢查測試文件...", "INFO")
    missing_files = []
    for file_path in TEST_FILES:
        full_path = BASE_DIR / file_path
        if not full_path.exists():
            missing_files.append(str(full_path))
            print_status(f"文件不存在: {file_path}", "ERROR")
        else:
            size = full_path.stat().st_size
            print_status(f"✓ {file_path} ({size / 1024:.2f} KB)", "SUCCESS")

    if missing_files:
        print_status(f"缺少 {len(missing_files)} 個文件，請檢查", "ERROR")
        return False

    # 檢查 ArangoDB
    try:
        print_status("檢查 ArangoDB 連接...", "INFO")
        client = ArangoClient(hosts=ARANGO_HOST)
        db = client.db(ARANGO_DB, username=ARANGO_USERNAME, password=ARANGO_PASSWORD)
        db.collection("file_metadata").count()
        print_status("ArangoDB 連接正常", "SUCCESS")
    except Exception as e:
        print_status(f"ArangoDB 連接失敗: {e}", "ERROR")
        return False

    # 檢查 Qdrant
    try:
        print_status("檢查 Qdrant 連接...", "INFO")
        qdrant = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
        collections = qdrant.get_collections()
        print_status(f"Qdrant 連接正常 (現有 Collections: {len(collections.collections)})", "SUCCESS")
    except Exception as e:
        print_status(f"Qdrant 連接失敗: {e}", "ERROR")
        return False

    # 檢查 API
    try:
        print_status("檢查 API 服務...", "INFO")
        response = httpx.get(f"{API_BASE_URL}{API_PREFIX}/health", timeout=5.0)
        if response.status_code == 200:
            print_status("API 服務正常", "SUCCESS")
        else:
            print_status(f"API 服務響應異常: {response.status_code}", "WARNING")
    except Exception as e:
        print_status(f"API 服務不可用: {e}", "WARNING")
        print_status("將繼續執行，但需要手動確認 API 可用", "WARNING")

    return True


def start_rq_workers() -> List[subprocess.Popen]:
    """啟動3個RQ Worker"""
    print_header("2. 啟動RQ Worker")

    workers = []
    python_cmd = sys.executable

    # 檢查是否有虛擬環境
    venv_python = BASE_DIR / "venv" / "bin" / "python"
    if venv_python.exists():
        python_cmd = str(venv_python)

    log_dir = BASE_DIR / "logs"
    log_dir.mkdir(exist_ok=True)

    for i in range(1, NUM_WORKERS + 1):
        worker_name = f"rq_worker_phase3_{i}"
        log_file = log_dir / f"rq_worker_{worker_name}.log"

        print_status(f"啟動 Worker {i}/{NUM_WORKERS}: {worker_name}", "INFO")

        try:
            # 使用 workers.service 模組啟動 Worker
            cmd = [
                python_cmd,
                "-m",
                "workers.service",
                "--queues",
                RQ_QUEUE,
                "--name",
                worker_name,
                "--log-file",
                str(log_file),
            ]

            process = subprocess.Popen(
                cmd,
                cwd=str(BASE_DIR),
                stdout=open(log_file, "a"),
                stderr=subprocess.STDOUT,
                env={**os.environ, "PYTHONPATH": str(BASE_DIR)},
            )

            workers.append(process)
            print_status(f"✓ Worker {i} 已啟動 (PID: {process.pid}, 日誌: {log_file})", "SUCCESS")
            time.sleep(1)  # 等待一下再啟動下一個

        except Exception as e:
            print_status(f"✗ Worker {i} 啟動失敗: {e}", "ERROR")

    if len(workers) == NUM_WORKERS:
        print_status(f"所有 {NUM_WORKERS} 個 Worker 已啟動", "SUCCESS")
        print_status("等待 3 秒讓 Worker 完全啟動...", "INFO")
        time.sleep(3)
    else:
        print_status(f"只啟動了 {len(workers)}/{NUM_WORKERS} 個 Worker", "WARNING")

    return workers


def stop_rq_workers(workers: List[subprocess.Popen]) -> None:
    """停止RQ Worker"""
    print_header("停止RQ Worker")

    for i, worker in enumerate(workers, 1):
        try:
            if worker.poll() is None:  # 進程還在運行
                print_status(f"停止 Worker {i} (PID: {worker.pid})", "INFO")
                worker.terminate()
                try:
                    worker.wait(timeout=5)
                    print_status(f"✓ Worker {i} 已停止", "SUCCESS")
                except subprocess.TimeoutExpired:
                    print_status(f"⚠ Worker {i} 未在5秒內停止，強制終止", "WARNING")
                    worker.kill()
                    worker.wait()
        except Exception as e:
            print_status(f"✗ 停止 Worker {i} 時發生錯誤: {e}", "ERROR")


def upload_file(file_path: str, api_token: Optional[str] = None) -> Optional[Dict]:
    """上傳單個文件"""
    full_path = BASE_DIR / file_path
    if not full_path.exists():
        print_status(f"文件不存在: {file_path}", "ERROR")
        return None

    print_status(f"上傳: {file_path}", "INFO")

    try:
        headers = {}
        if api_token:
            headers["Authorization"] = f"Bearer {api_token}"

        with open(full_path, "rb") as f:
            files = {"files": (full_path.name, f, "text/markdown")}
            data = {"task_id": TASK_ID}

            response = httpx.post(
                f"{API_BASE_URL}{API_PREFIX}/files/v2/upload",
                files=files,
                data=data,
                headers=headers,
                timeout=30.0,
            )

            if response.status_code == 200:
                result = response.json()
                file_id = result.get("data", {}).get("file_id") or result.get("file_id")
                print_status(f"✓ 上傳成功: {file_path} (File ID: {file_id})", "SUCCESS")
                return {
                    "file_path": file_path,
                    "file_id": file_id,
                    "status": "uploaded",
                    "response": result,
                }
            else:
                print_status(
                    f"✗ 上傳失敗: {file_path} (狀態碼: {response.status_code})", "ERROR"
                )
                print_status(f"響應: {response.text}", "ERROR")
                return None

    except Exception as e:
        print_status(f"✗ 上傳異常: {file_path} - {e}", "ERROR")
        return None


def batch_upload_files(api_token: Optional[str] = None) -> List[Dict]:
    """批量上傳文件"""
    print_header("3. 批量上傳文件")

    results = []
    for i, file_path in enumerate(TEST_FILES, 1):
        print_status(f"({i}/{len(TEST_FILES)}) 處理文件...", "INFO")
        result = upload_file(file_path, api_token)
        if result:
            results.append(result)
        else:
            results.append({"file_path": file_path, "status": "failed"})

        # 等待一下再上傳下一個
        if i < len(TEST_FILES):
            time.sleep(2)

    print_status(f"批量上傳完成: {len(results)}/{len(TEST_FILES)} 成功", "INFO")
    return results


def get_processing_status() -> Dict:
    """獲取處理狀態"""
    try:
        # ArangoDB 狀態
        client = ArangoClient(hosts=ARANGO_HOST)
        db = client.db(ARANGO_DB, username=ARANGO_USERNAME, password=ARANGO_PASSWORD)

        cursor = db.aql.execute(
            'FOR f IN file_metadata FILTER f.task_id == @task_id RETURN f',
            bind_vars={"task_id": TASK_ID},
        )
        files = list(cursor)

        completed = sum(1 for f in files if f.get("status") == "processed")
        processing = sum(1 for f in files if f.get("status") == "processing")
        uploaded = sum(1 for f in files if f.get("status") == "uploaded")
        failed = sum(1 for f in files if f.get("status") == "failed")

        # Qdrant Collections 數量
        qdrant = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
        collections = qdrant.get_collections()
        qdrant_count = len([c for c in collections.collections if "file_" in c.name])

        return {
            "total": len(files),
            "uploaded": uploaded,
            "processing": processing,
            "completed": completed,
            "failed": failed,
            "qdrant_collections": qdrant_count,
            "files": files,
        }
    except Exception as e:
        print_status(f"獲取狀態失敗: {e}", "ERROR")
        return {}


def monitor_processing(max_wait_minutes: int = 10) -> Optional[Dict]:
    """監控處理進度"""
    print_header("4. 監控處理進度")

    start_time = time.time()
    max_wait_seconds = max_wait_minutes * 60

    print_status(f"開始監控（最多等待 {max_wait_minutes} 分鐘）...", "INFO")

    while True:
        elapsed = time.time() - start_time
        if elapsed > max_wait_seconds:
            print_status("監控超時", "WARNING")
            break

        status = get_processing_status()
        if not status:
            time.sleep(10)
            continue

        total = status.get("total", 0)
        completed = status.get("completed", 0)
        processing = status.get("processing", 0)
        uploaded = status.get("uploaded", 0)
        failed = status.get("failed", 0)
        qdrant_count = status.get("qdrant_collections", 0)

        print_status(
            f"進度: 總計={total}, 已完成={completed}, 處理中={processing}, "
            f"待處理={uploaded}, 失敗={failed}, Qdrant Collections={qdrant_count}",
            "INFO",
        )

        if completed >= total and total > 0:
            print_status("所有文件處理完成！", "SUCCESS")
            break

        time.sleep(10)

    # 最終狀態
    final_status = get_processing_status()
    return final_status


def print_summary(results: List[Dict], final_status: Optional[Dict] = None) -> None:
    """打印測試摘要"""
    print_header("5. 測試摘要")

    print("\n📋 上傳結果:")
    for i, result in enumerate(results, 1):
        file_path = result.get("file_path", "Unknown")
        status = result.get("status", "unknown")
        file_id = result.get("file_id", "N/A")
        symbol = "✅" if status == "uploaded" else "❌"
        print(f"  {i}. {symbol} {file_path}")
        if file_id and file_id != "N/A":
            print(f"     File ID: {file_id}")

    if final_status:
        print("\n📊 最終處理狀態:")
        print(f"  總文件數: {final_status.get('total', 0)}")
        print(f"  已完成: {final_status.get('completed', 0)}")
        print(f"  處理中: {final_status.get('processing', 0)}")
        print(f"  待處理: {final_status.get('uploaded', 0)}")
        print(f"  失敗: {final_status.get('failed', 0)}")
        print(f"  Qdrant Collections: {final_status.get('qdrant_collections', 0)}")

        # 詳細文件信息
        files = final_status.get("files", [])
        if files:
            print("\n📄 文件詳情:")
            for f in files:
                filename = f.get("filename", "Unknown")
                status = f.get("status", "unknown")
                chunk_count = f.get("chunk_count", 0)
                vector_count = f.get("vector_count", 0)
                kg_status = f.get("kg_status", "N/A")
                print(f"  - {filename}")
                print(f"    狀態: {status}")
                print(f"    分塊: {chunk_count} 個")
                print(f"    向量: {vector_count} 個")
                print(f"    圖譜: {kg_status}")


def main() -> int:
    """主函數"""
    print_header("第三階段批量文件上傳測試")
    print(f"測試日期: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"測試文件數: {len(TEST_FILES)}")
    print(f"任務ID: {TASK_ID}")
    print(f"用戶ID: {USER_ID}")
    print(f"RQ Worker 數量: {NUM_WORKERS}")

    workers = []

    try:
        # 檢查服務
        if not check_services():
            print_status("環境檢查失敗，請修復後重試", "ERROR")
            return 1

        # 啟動RQ Worker
        workers = start_rq_workers()

        # 獲取 API Token（如果需要）
        api_token = os.getenv("API_TOKEN")
        if not api_token:
            print_status(
                "未設置 API_TOKEN 環境變數，如果 API 需要認證，上傳可能會失敗", "WARNING"
            )

        # 批量上傳
        results = batch_upload_files(api_token)

        # 監控處理
        final_status = monitor_processing()

        # 打印摘要
        print_summary(results, final_status)

        print_header("測試完成")

    except KeyboardInterrupt:
        print_status("收到中斷信號，正在停止...", "WARNING")
    finally:
        # 停止Worker
        if workers:
            stop_rq_workers(workers)

    return 0


if __name__ == "__main__":
    sys.exit(main())
```

**方法二：手動執行（備選方案）**

如果不想使用自動化腳本，可以手動執行：

1. **準備文件列表**

   ```bash
   cat > /tmp/test_files.txt << 'EOF'
   docs/系统设计文档/安全架构说明.md
   docs/系统设计文档/IEE前端系統/IEE前端系统.md
   docs/系统设计文档/核心组件/MCP工具/MCP工具.md
   docs/系统设计文档/核心组件/Agent平台/Data-Agent-規格書.md
   docs/系统设计文档/核心组件/語義與任務分析/AI-Box語義與任務v4重構計劃.md
   EOF
   ```

2. **執行批量上傳**

   ```bash
   # 設置 API Token（如果需要）
   export API_TOKEN="your_api_token_here"

   # 逐個上傳文件
   while read file; do
     echo "上傳: $file"
     curl -X POST "http://localhost:8000/api/v1/files/v2/upload" \
       -H "Authorization: Bearer $API_TOKEN" \
       -F "files=@$file" \
       -F "task_id=SystemDocs"
     sleep 2  # 等待處理
   done < /tmp/test_files.txt
   ```

3. **監控處理進度**

   ```bash
   # 檢查 RQ Worker 日誌
   tail -f logs/rq_worker_rq_worker_phase3_*.log

   # 檢查 Qdrant Collections
   curl -s http://localhost:6333/collections | python3 -c "import sys,json; d=json.load(sys.stdin); print([c['name'] for c in d['result']['collections']])"

   # 檢查處理狀態
   python3 << 'EOF'
   from arango import ArangoClient
   from qdrant_client import QdrantClient

   # ArangoDB 狀態
   client = ArangoClient(hosts='http://localhost:8529')
   db = client.db('ai_box_kg', username='root', password='changeme')

   cursor = db.aql.execute('FOR f IN file_metadata FILTER f.task_id == "SystemDocs" RETURN f')
   files = list(cursor)

   completed = sum(1 for f in files if f.get('status') == 'processed')
   processing = sum(1 for f in files if f.get('status') == 'processing')
   uploaded = sum(1 for f in files if f.get('status') == 'uploaded')

   print(f'總文件數: {len(files)}')
   print(f'已完成: {completed}')
   print(f'處理中: {processing}')
   print(f'待處理: {uploaded}')

   # Qdrant Collections 數量
   qdrant = QdrantClient(host='localhost', port=6333)
   collections = qdrant.get_collections()
   qdrant_count = len([c for c in collections.collections if 'file_' in c.name])
   print(f'\nQdrant Collections: {qdrant_count}')
   EOF
   ```

#### 3.4 驗證項目

- [ ] 所有 5 個文件成功上傳
- [ ] RQ Worker 正確處理任務
- [ ] 任務狀態正確更新
- [ ] 沒有任務死鎖
- [ ] 向量化和圖譜提取都成功
- [ ] **Qdrant Collections 正確創建**

#### 3.5 測試記錄

| 項目                         | 數值     | 備註 |
| ---------------------------- | -------- | ---- |
| 測試日期                     | ___      |      |
| 測試文件數                   | 5 個     |      |
| 成功上傳                     | ___ 個   |      |
| 失敗上傳                     | ___ 個   |      |
| 成功處理                     | ___ 個   |      |
| 失敗處理                     | ___ 個   |      |
| **Qdrant Collections** | ___ 個   |      |
| 總處理時間                   | ___ 分鐘 |      |

---

### 第四階段：完整系統文檔處理（目標：全部文件）

#### 4.1 測試目標

處理 `docs/系統設計文檔/` 目錄下的所有 Markdown 文件。

#### 4.2 文件統計

```bash
# 統計文件數量
find docs/系統設計文檔 -type f -name "*.md" | wc -l

# 列出所有文件
find docs/系統設計文檔 -type f -name "*.md" > /tmp/all_files.txt

# 統計總大小
du -sh docs/系統設計文檔/
```

#### 4.3 執行策略

**分批處理策略**：

- 每批 10 個文件
- 確認一批完成後再進行下一批
- 記錄每批的處理時間和成功率

#### 4.4 進度監控

```python
# scripts/monitor_processing.py
from arango import ArangoClient
from qdrant_client import QdrantClient

def get_processing_status():
    # ArangoDB 狀態
    client = ArangoClient(hosts='http://localhost:8529')
    db = client.db('ai_box_kg', username='root', password='changeme')

    cursor = db.aql.execute('FOR f IN file_metadata FILTER f.task_id == "systemAdmin_SystemDocs" RETURN f')
    files = list(cursor)

    # Qdrant Collections 數量
    qdrant = QdrantClient(host='localhost', port=6333)
    collections = qdrant.get_collections()
    qdrant_count = len([c for c in collections.collections if 'file_' in c.name])

    status = {
        'total': len(files),
        'uploaded': sum(1 for f in files if f.get('status') == 'uploaded'),
        'processing': sum(1 for f in files if f.get('status') == 'processing'),
        'completed': sum(1 for f in files if f.get('status') == 'processed'),
        'failed': sum(1 for f in files if f.get('status') == 'failed'),
        'chunk_count': sum(f.get('chunk_count', 0) for f in files),
        'vector_count': sum(f.get('vector_count', 0) for f in files),
        'qdrant_collections': qdrant_count,
    }

    return status

# 定期檢查
import time
while True:
    status = get_processing_status()
    print(f"總文件: {status['total']}, 完成: {status['completed']}, 處理中: {status['processing']}, 失敗: {status['failed']}")
    print(f"Qdrant Collections: {status['qdrant_collections']}")
    if status['completed'] == status['total'] and status['qdrant_collections'] == status['total']:
        break
    time.sleep(30)
```

#### 4.5 測試記錄

| 項目                         | 數值     | 備註                                            |
| ---------------------------- | -------- | ----------------------------------------------- |
| 測試日期                     | ___      |                                                 |
| 總文件數                     | ___ 個   | `find docs/系統設計文檔 -type f -name "*.md"` |
| 成功上傳                     | ___ 個   |                                                 |
| 失敗上傳                     | ___ 個   |                                                 |
| 成功處理                     | ___ 個   |                                                 |
| 失敗處理                     | ___ 個   |                                                 |
| 總分塊數                     | ___ 個   |                                                 |
| **總向量數 (Qdrant)**  | ___ 個   |                                                 |
| **Qdrant Collections** | ___ 個   |                                                 |
| 總實體數                     | ___ 個   |                                                 |
| 總關係數                     | ___ 個   |                                                 |
| 總處理時間                   | ___ 分鐘 |                                                 |

---

## 📊 驗證檢查清單

### 存儲驗證

#### SeaWeedFS

- [ ] 文件已上傳到 `bucket-ai-box-assets`
- [ ] 文件路徑正確：`tasks/systemAdmin_SystemDocs/{file_id}.md`

#### ArangoDB file_metadata

- [ ] 元數據記錄存在
- [ ] `status` 為 `processed`
- [ ] `chunk_count` > 0
- [ ] `vector_count` > 0
- [ ] `kg_status` 為 `completed`
- [ ] `task_id` 為 `systemAdmin_SystemDocs`

#### **Qdrant**（v4.0 更新）

- [ ] Collection 已創建：`file_{file_id}`
- [ ] Collection 狀態為 `green`
- [ ] 向量數量正確
- [ ] 向量維度正確（768 維度，根據 Embedding 模型）
- [ ] **Dashboard 可訪問**：<http://localhost:6333/dashboard>

#### ArangoDB 知識圖譜

- [ ] 實體已存儲（`entities` collection）
- [ ] 關係已存儲（`relations` collection）
- [ ] 實體包含 `file_id` 字段
- [ ] 關係包含 `file_id` 字段
- [ ] 實體類型符合 Ontology 定義

### 功能驗證

#### 向量檢索

```python
# 測試向量檢索
from qdrant_client import QdrantClient

client = QdrantClient(host='localhost', port=6333)

# 測試查詢
collection_name = f'file_{file_id}'
results = client.query_points(
    collection_name=collection_name,
    query=[0.1] * 768,  # 示例查詢向量
    limit=5,
    with_payload=True,
)
assert len(results.points) > 0
```

#### Qdrant Dashboard 驗證

```
訪問 http://localhost:6333/dashboard
1. 查看 Collections 列表
2. 點擊 file_{file_id} Collection
3. 驗證向量數量和質量
4. 測試搜索功能
```

#### 知識圖譜查詢

```python
# 測試圖查詢
from arango import ArangoClient
client = ArangoClient(hosts='http://localhost:8529')
db = client.db('ai_box_kg', username='root', password='changeme')

# 查詢實體
cursor = db.aql.execute('''
  FOR e IN entities
    FILTER e.file_id == @file_id
    LIMIT 10
    RETURN e
''', bind_vars={'file_id': file_id})
entities = list(cursor)
assert len(entities) > 0
```

---

## 📝 測試記錄說明

### 記錄位置

測試記錄已嵌入到各個階段中：

- **第一階段**：環境確認後的測試記錄（1.3 節）
- **第二階段**：單一文件測試記錄（2.4 節）
- **第三階段**：批量測試記錄（3.5 節）
- **第四階段**：完整處理記錄（4.5 節）

### 整體測試摘要

| 階段               | 測試日期   | 文件數 | 成功 | 失敗 | 處理時間 | VectorDB  | 狀態                      |
| ------------------ | ---------- | ------ | ---- | ---- | -------- | --------- | ------------------------- |
| 第一階段：環境確認 | 2026-01-20 | -      | -    | -    | -        | Qdrant ✅ | ✅                        |
| 第二階段：單一文件 | 2026-01-20 | 1      | 1    | 0    | 66 秒    | Qdrant ✅ | ✅ 通過                   |
| 第三階段：批量測試 | 2026-01-20 | -      | -    | -    | -        | Qdrant    | ⚠️ 跳過（需 API Token） |
| 第四階段：完整處理 | 待執行     | ___    | ___  | ___  | ___ 分鐘 | Qdrant    | ⏳ 待執行                 |

### 2026-01-20 更新紀錄

**第三階段測試說明**：

- API 端點 `/api/v1/files/upload` 需要 JWT 認證
- `batch_upload_system_docs.py` 腳本需要 `API_TOKEN` 環境變數
- 由於測試環境限制，批量上傳測試暫時跳過
- **RQ Worker 已修復**：重啟後成功連接 Redis

**當前系統狀態**：

- Qdrant Collections: 5 個（含測試 collections）
- 已處理文件: 1 個（Phase 2 測試）
- RQ Worker: 運行正常
- Redis: 運行正常

### 詳細文件記錄（第二階段 - v4.0 Qdrant）

| 序號 | 文件名                           | 大小     | 分塊  | 向量  | 實體  | 關係  | 狀態 | 處理時間 |
| ---- | -------------------------------- | -------- | ----- | ----- | ----- | ----- | ---- | -------- |
| 1    | `docs_system_design_README.md` | 18.41 KB | 11 個 | 11 個 | 12 個 | 17 個 | ✅   | 66 秒    |

**測試日期**: 2026-01-20
**File ID**: `cc3d7aee-b5b3-4e11-9458-784575c1dba6`
**S3 Path**: `s3://bucket-ai-box-assets/tasks/systemAdmin_SystemDocs/cc3d7aee-...`
**處理狀態**: ✅ completed
**使用的 Ontology**: Enterprise + Manufacture

**v4.0 Qdrant 驗證結果**：

- ✅ **Qdrant Collection**: `file_cc3d7aee-b5b3-4e11-9458-784575c1dba6`
- ✅ **Qdrant Collection 狀態**: green
- ✅ **Qdrant 向量數量**: 11 個
- ✅ **Qdrant Dashboard**: <http://localhost:6333/dashboard>

**處理結果摘要**：

- ✅ 文件上傳成功（0.14 秒）
- ✅ 分塊完成（11 個 chunks）
- ✅ 向量化完成（11 個 vectors，768 維度）
- ✅ **向量存儲到 Qdrant**（而非 ChromaDB）
- ✅ 知識圖譜完成（12 實體、17 關係）

---

## ⚠️ 問題處理

### 常見問題

1. **上傳後狀態一直是 `uploaded`**

   - 原因：RQ Worker 沒有運行或處理失敗
   - 解決：檢查 RQ Worker 日誌
2. **向量化失敗**

   - 原因：Ollama 服務不可用或模型不存在
   - 解決：檢查 Ollama 服務狀態
3. **Qdrant 連接失敗**

   - 原因：Qdrant 服務未啟動
   - 解決：啟動 Qdrant 容器

   ```bash
   docker run -d --name qdrant -p 6333:6333 -p 6334:6334 \
     -v /Users/daniel/GitHub/AI-Box/data/qdrant:/qdrant/storage \
     qdrant/qdrant:latest
   ```

4. **知識圖譜提取失敗**

   - 原因：Ontology 選擇失敗或 LLM 調用失敗
   - 解決：檢查 LLM 服務狀態和 Ontology 配置

### 日誌位置

- RQ Worker：`/tmp/rq_worker.log`
- API Server：終端輸出或系統日誌
- ArangoDB：Web UI 或 API
- **Qdrant Dashboard**：<http://localhost:6333/dashboard>
- **Qdrant Health**：`curl http://localhost:6333/health`

---

## 🎯 成功標準

### 必須達到的標準

- [X] Qdrant 服務正常運行
- [X] Qdrant Collection 創建功能正常
- [X] 向量存儲到 Qdrant（而非 ChromaDB）
- [X] Qdrant Dashboard 可訪問（<http://localhost:6333/dashboard）>
- [X] 單一文件處理流程完整（Phase 2 測試通過）
- [ ] 批量處理功能正常（待 API Token 後測試）
- [ ] 完整系統文檔處理（Phase 4）
- [ ] 向量檢索功能正常
- [ ] 圖查詢功能正常

### 性能標準

- 單一文件處理時間：< 60 秒
- 批量處理並發數：5 個任務
- 系統穩定性：無死鎖、無記憶體洩漏
- **Qdrant 查詢響應時間**：< 100ms

---

## 📚 相關文檔

### v4.0 新增文檔

- [VectorDB.md](./VectorDB.md) - 向量數據庫完整架構文檔（2026-01-20 新增）
- [上傳的功能架構說明-v4.0.md](./上傳的功能架構說明-v4.0.md) - 更新版架構說明
- [CHROMADB_TO_QDRANT_MIGRATION.md](./CHROMADB_TO_QDRANT_MIGRATION.md) - 遷移指南
- [ROLLBACK_PLAN.md](./ROLLBACK_PLAN.md) - 回滾計畫

### 現有文檔

- [上傳的功能架構說明-v3.0](./上傳的功能架構說明-v3.0.md)
- [文件上傳向量圖譜化測試計劃](./文件上傳向量圖譜化測試計劃.md)
- [Ontology 系統](./Ontology系统.md)
- [知識圖譜系統](./知识图谱系统.md)

---

## 🔄 迭代規劃

### 迭代時程

| 迭代        | 日期       | 目標                         | 測試文件數 |
| ----------- | ---------- | ---------------------------- | ---------- |
| Iteration 0 | 2026-01-20 | 環境準備、單一文件測試       | 1 個       |
| Iteration 1 | 2026-01-21 | 批量測試、清理腳本、計時功能 | 5 個       |
| Iteration 2 | 待定       | 完整文檔處理（全部文件）     | ___ 個     |
| Iteration 3 | 待定       | GraphRAG 整合測試            | ___ 個     |
| Iteration 4 | 待定       | 性能優化與壓力測試           | ___ 個     |

### Iteration 1 待完成事項（2026-01-21）

- [ ] ✅ 通用測試腳本 `scripts/test_file_upload.py`
- [ ] ✅ 清理腳本 `scripts/cleanup_test_data.py`
- [ ] ⏳ 計時功能（--timing 參數）
- [ ] ⏳ 第三階段批量測試（5 個文件）
- [ ] ⏳ 測試報告記錄圖譜抽取模型調用

### Iteration 2 規劃（完整文檔處理）

**目標**：處理 `docs/系統設計文檔/` 目錄下所有 Markdown 文件

**步驟**：

1. 統計文件數量
2. 分批處理（每批 10 個文件）
3. 監控處理進度
4. 驗證完整數據正確性

**預估文件數**：

```bash
find docs/系統設計文檔 -type f -name "*.md" | wc -l
```

### 技術債務

| 項目                  | 描述                        | 優先級 |
| --------------------- | --------------------------- | ------ |
| API Token 認證        | 自動化測試需要 API Token    | 高     |
| RQ Worker 監控        | 改進 Worker 狀態監控        | 中     |
| 測試報告生成          | 自動生成 Markdown/HTML 報告 | 中     |
| Qdrant Graph 面板集成 | 前端嵌入向量空間視覺化      | 低     |

### 監控指標

| 指標              | 目標值     | 當前值 |
| ----------------- | ---------- | ------ |
| 文件處理成功率    | > 95%      | ___    |
| 平均處理時間      | < 60 秒/檔 | ___    |
| Qdrant 查詢延遲   | < 100ms    | ___    |
| ArangoDB 查詢延遲 | < 200ms    | ___    |

---

**最後更新日期**: 2026-01-21 10:30 UTC+8
**版本**: 4.0（Qdrant 遷移版）
