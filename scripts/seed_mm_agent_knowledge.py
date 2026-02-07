# 代碼功能說明: MM-Agent 知識庫種子腳本
# 創建日期: 2026-02-04
# 創建人: Daniel Chung
# 最後修改日期: 2026-02-04

"""
MM-Agent 知識庫種子腳本

用於建立 MM-Agent（物料管理代理）的系統知識，包括：
1. MM-Agent 職責範圍
2. 可執行的操作
3. 數據查詢能力

使用方式:
    python scripts/seed_mm_agent_knowledge.py [--force]
    --force: 若知識已存在則覆蓋

前置條件:
    - ArangoDB 已啟動且 .env 已配置
    - SeaweedFS 已啟動
    - Qdrant/ChromaDB 已啟動
    - 請先啟用虛擬環境: source venv/bin/activate
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import structlog

project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

load_dotenv(dotenv_path=project_root / ".env")

from services.api.models.file_metadata import FileMetadataCreate, FileMetadataUpdate
from services.api.services.file_metadata_service import FileMetadataService
from services.api.services.knowledge_asset_encoding_service import KnowledgeAssetEncodingService

logger = structlog.get_logger(__name__)


MM_AGENT_KNOWLEDGE_CONTENT = """# MM-Agent（物料管理代理）系統知識

## 概述

MM-Agent 是 AI-Box 系統中的物料管理專業代理，專注於處理物料管理相關的業務操作和數據查詢。

## 主要職責

### 1. 庫存查詢
- 查詢物料庫存數量
- 查詢庫存位置
- 查詢庫存變動歷史
- 查詢安全庫存水位

### 2. 採購管理
- 創建採購單
- 查詢採購訂單狀態
- 追蹤採購進度
- 管理供應商資訊

### 3. 缺料分析
- 分析缺料情況
- 識別潛在缺料風險
- 提供缺料解決建議

### 4. 料號管理
- 料號基本資訊查詢
- 料號規格確認
- 料號替代品查詢

## 複雜分析技能

### ABC 分類分析（帕累托分析）

**業務定義**：
ABC 分類法是一種庫存分類方法，根據物料的價值佔比進行分類：
- A 類：累計價值佔 70%（重要物料，嚴格管控）
- B 類：累計價值佔 20%（一般物料，常規管理）
- C 類：累計價值佔 10%（不重要物料，簡化管理）

**執行步驟**：
1. 計算每料號庫存價值 = 庫存數量 × 單價
2. 計算總庫存價值 = SUM(所有料號庫存價值)
3. 按價值降序排序
4. 計算累積百分比 = (當前價值 / 總價值) 的累加
5. 分類：
   - 累積 ≤ 70% → A 類
   - 70% < 累積 ≤ 90% → B 類
   - 累積 > 90% → C 類

**數據需求**：
- ima_file（料件主檔）：ima01=料號，ima02=品名，ima44=單價
- img_file（庫存檔）：img01=料號，img10=庫存數量

**範例查詢**：
- "幫我列出ABC分類"
- "顯示A類物料有哪些"
- "哪些是C類料號"

**SQL 範例**：
```sql
-- 計算庫存價值
SELECT img01 AS material_code,
       SUM(CAST(img10 AS DECIMAL)) AS total_qty,
       ima44 AS unit_price,
       SUM(CAST(img10 AS DECIMAL)) * COALESCE(ima44, 0) AS total_value
FROM read_parquet('s3://tiptop-raw/raw/v1/img_file/year=*/month=*/data.parquet', hive_partitioning=true)
LEFT JOIN read_parquet('s3://tiptop-raw/raw/v1/ima_file/year=*/month=*/data.parquet', hive_partitioning=true)
    ON img01 = ima01
WHERE CAST(img10 AS DECIMAL) > 0
GROUP BY img01, ima44
ORDER BY total_value DESC
```

### 缺料分析

**業務定義**：
分析當前庫存是否低於安全水位，識別潛在缺料風險。

**執行步驟**：
1. 查詢當前庫存數量
2. 查詢安全庫存水位
3. 計算缺料數量 = 安全庫存 - 當前庫存
4. 生成缺料風險報告

**數據需求**：
- img_file：img01=料號，img10=庫存數量
- ima_file：ima01=料號，ima159=安全庫存

### 週轉率分析

**業務定義**：
計算物料的庫存週轉率，評估庫存效率。

**執行步驟**：
1. 查詢一段期間的出庫數量
2. 計算平均庫存 = (期初 + 期末) / 2
3. 週轉率 = 出庫數量 / 平均庫存
4. 生成週轉率報告

---

## 使用場景

### 數據查詢（DATA_QUERY）
當用戶詢問具體業務數據時，應路由到 MM-Agent：
- "RM01-003 庫存多少？"
- "查詢最近三個月的採購訂單"
- "哪些料號庫存低於安全水位？"

### 知識查詢（KNOWLEDGE_QUERY）
當用戶詢問 MM-Agent 的功能或能力時，應返回此知識：
- "MM-Agent 能做什麼？"
- "物料管理代理有哪些功能？"
- "怎麼查詢庫存？"

### 複雜分析（COMPLEX_ANALYSIS）
當用戶請求複雜分析時，應使用任務編排：
- "幫我列出ABC分類" → abc_analysis
- "分析缺料風險" → shortage_analysis
- "計算週轉率" → turnover_analysis

## 數據來源

MM-Agent 連接以下系統和數據源：
- ERP 系統（SAP/Oracle 等）
- WMS 倉儲管理系統
- 採購管理系統
- 庫存管理系統

## 注意事項

1. MM-Agent 專注於物料管理領域，不處理其他業務（如 HR、財務等）
2. 數據查詢需要適當的權限驗證
3. 系統會自動識別意圖並路由到對應的 Agent
4. 複雜分析任務需要與用戶確認後才執行
5. 分析結果應包含業務建議
"""


def generate_file_id(content: str) -> str:
    """生成唯一的文件 ID"""
    content_hash = hashlib.md5(content.encode()).hexdigest()[:16]
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"mm_agent_knowledge_{timestamp}_{content_hash}"


async def seed_mm_agent_knowledge_async(force: bool = False) -> bool:
    """
    種子 MM-Agent 知識庫

    Args:
        force: 若知識已存在則覆蓋

    Returns:
        是否成功
    """
    try:
        logger.info("開始種子 MM-Agent 知識庫...")

        # 1. 檢查知識是否已存在
        meta_service = FileMetadataService()
        existing_files = meta_service.list(
            domain="mm_agent",
            major="responsibilities",
            limit=10,
        )

        existing_file_ids = [f.file_id for f in existing_files]
        logger.info(f"找到 {len(existing_file_ids)} 個現有的 MM-Agent 知識文件")

        if existing_file_ids and not force:
            logger.info("MM-Agent 知識已存在，使用 --force 參數可覆蓋")
            return True

        # 2. 準備知識內容
        content = MM_AGENT_KNOWLEDGE_CONTENT
        file_id = generate_file_id(content)
        filename = "mm_agent_knowledge.md"
        file_type = "text/markdown"
        file_size = len(content.encode("utf-8"))

        # 3. 上傳文件到 SeaweedFS
        from storage.s3_storage import S3FileStorage, SeaweedFSService

        endpoint = os.getenv("AI_BOX_SEAWEEDFS_S3_ENDPOINT", "http://localhost:8333")
        access_key = os.getenv("AI_BOX_SEAWEEDFS_S3_ACCESS_KEY", "")
        secret_key = os.getenv("AI_BOX_SEAWEEDFS_S3_SECRET_KEY", "")
        use_ssl = os.getenv("AI_BOX_SEAWEEDFS_USE_SSL", "false").lower() == "true"

        storage = S3FileStorage(
            endpoint=endpoint,
            access_key=access_key,
            secret_key=secret_key,
            use_ssl=use_ssl,
            service_type=SeaweedFSService.AI_BOX,
        )

        bucket_name = "bucket-ai-box-assets"
        storage_key = f"knowledge/{file_id}/{filename}"

        storage.s3_client.put_object(
            Bucket=bucket_name,
            Key=storage_key,
            Body=content.encode("utf-8"),
            ContentType=file_type,
        )

        storage_path = f"s3://{bucket_name}/{storage_key}"
        logger.info(f"文件已上傳到 SeaweedFS: {storage_path}")

        # 4. 建立文件元數據
        metadata = FileMetadataCreate(
            file_id=file_id,
            filename=filename,
            file_type=file_type,
            file_size=file_size,
            user_id="system",
            task_id="system",
            storage_path=storage_path,
            tags=["mm_agent", "knowledge", "system"],
            description="MM-Agent（物料管理代理）系統知識文件",
            domain="mm_agent",
            major="responsibilities",
            lifecycle_state="Active",
            version="1.0.0",
            license="INTERNAL",
            status="vectorized",
            processing_status="completed",
        )

        meta_service.create(metadata)
        logger.info(f"文件元數據已創建: {file_id}")

        # 5. 執行知識編碼（向量化和圖譜提取）
        # 注意：知識編碼需要 LLM，如果 LLM 不可用，我們仍然可以創建文件元數據
        try:
            enc_service = KnowledgeAssetEncodingService()
            enc_result = await enc_service.encode_file(
                file_id=file_id,
                filename=filename,
                file_content_preview=content[:2000],
                file_metadata={
                    "file_type": file_type,
                    "user_id": "system",
                },
            )
            logger.info(
                f"知識編碼完成: knw_code={enc_result['knw_code']}, ka_id={enc_result['ka_id']}"
            )
            has_encoding = True
        except Exception as encode_error:
            logger.warning(f"知識編碼失敗（LLM 不可用），將使用手動設置: {encode_error}")
            # 手動設置編碼結果（當 LLM 不可用時）
            import uuid

            enc_result = {
                "knw_code": f"KNW-{file_id[:16].upper()}",
                "ka_id": f"KA-{uuid.uuid4().hex[:8].upper()}",
                "domain": "mm_agent",
                "major": "responsibilities",
                "lifecycle_state": "Active",
                "version": "1.0.0",
                "graph_extracted": False,
            }
            has_encoding = False

        # 6. 更新文件元數據中的向量和圖譜引用
        update = FileMetadataUpdate(
            task_id="system",
            knw_code=enc_result["knw_code"],
            ka_id=enc_result["ka_id"],
            domain=enc_result["domain"],
            major=enc_result.get("major"),
            lifecycle_state=enc_result["lifecycle_state"],
            version=enc_result["version"],
            vector_refs=["user_based"],
            kg_status="completed" if enc_result.get("graph_extracted") else "skipped",
        )
        meta_service.update(file_id, update)
        logger.info(f"文件元數據已更新: {file_id}")

        logger.info("MM-Agent 知識庫種子完成")
        return True

    except Exception as e:
        logger.error(f"MM-Agent 知識庫種子失敗: {e}", exc_info=True)
        return False


def seed_mm_agent_knowledge(force: bool = False) -> bool:
    """同步包裝器"""
    return asyncio.run(seed_mm_agent_knowledge_async(force))


def main() -> int:
    """主程式"""
    parser = argparse.ArgumentParser(description="種子 MM-Agent 知識庫")
    parser.add_argument(
        "--force",
        action="store_true",
        help="若知識已存在則覆蓋",
    )
    args = parser.parse_args()

    logger.info("開始種子 MM-Agent 知識庫...")
    success = seed_mm_agent_knowledge(force=args.force)
    if success:
        logger.info("MM-Agent 知識庫種子完成")
        return 0
    logger.error("MM-Agent 知識庫種子失敗")
    return 1


if __name__ == "__main__":
    sys.exit(main())
