#!/usr/bin/env python3
"""
DataAgent Intent RAG 系統

使用 Qwen3-embedding 生成向量，存入 Qdrant 向量資料庫
支援配置外部化，可透過 DataAgentConfig 配置
"""

import json
import requests
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance
from pathlib import Path
import sys

# 將 datalake-system 添加到路徑
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from data_agent.config_manager import get_config

config = get_config()

QDRANT_URL = "http://localhost:6333"
COLLECTION_NAME = "data_agent_intents"

EMBEDDING_MODEL = config.get_embedding_model()
EMBEDDING_ENDPOINT = config.get_embedding_endpoint()
EMBEDDING_TIMEOUT = config.get_embedding_timeout()
VECTOR_DIM = config.get_embedding_dimension()

INTENT_TEMPLATES = [
    # === 庫存查詢 ===
    {
        "id": "inv_001",
        "query": "查詢 W01 倉庫的庫存",
        "sql": "SELECT * FROM img_file WHERE img02 = 'W01'",
        "type": "query_inventory",
    },
    {
        "id": "inv_002",
        "query": "查W01 庫房每個料號存量",
        "sql": "SELECT img01, SUM(img10) FROM img_file WHERE img02 = 'W01' GROUP BY img01",
        "type": "statistics",
    },
    {
        "id": "inv_003",
        "query": "計算各倉庫的總庫存量",
        "sql": "SELECT img02, SUM(img10) FROM img_file GROUP BY img02",
        "type": "statistics",
    },
    {
        "id": "inv_004",
        "query": "查詢料號 10-0001 的庫存信息",
        "sql": "SELECT * FROM img_file WHERE img01 = '10-0001'",
        "type": "query_inventory",
    },
    {
        "id": "inv_005",
        "query": "列出所有負庫存的物料",
        "sql": "SELECT * FROM img_file WHERE img10 < 0",
        "type": "query_inventory",
    },
    {
        "id": "inv_006",
        "query": "列出前 10 個庫存量最多的物料",
        "sql": "SELECT * FROM img_file ORDER BY img10 DESC LIMIT 10",
        "type": "query_inventory",
    },
    {
        "id": "inv_007",
        "query": "統計 W03 成品倉的總庫存量",
        "sql": "SELECT SUM(img10) FROM img_file WHERE img02 = 'W03'",
        "type": "statistics",
    },
    {
        "id": "inv_008",
        "query": "計算各倉庫的平均庫存量",
        "sql": "SELECT img02, AVG(img10) FROM img_file GROUP BY img02",
        "type": "statistics",
    },
    {
        "id": "inv_009",
        "query": "查詢 2024 年有多少筆採購進貨",
        "sql": "SELECT COUNT(*) FROM tlf_file WHERE tlf19 = '101' AND tlf06 LIKE '2024%'",
        "type": "calculate_count",
    },
    {
        "id": "inv_010",
        "query": "查詢 W01 原料倉的庫存",
        "sql": "SELECT * FROM img_file WHERE img02 = 'W01'",
        "type": "query_inventory",
    },
    {
        "id": "inv_011",
        "query": "W02 倉有多少庫存",
        "sql": "SELECT * FROM img_file WHERE img02 = 'W02'",
        "type": "query_inventory",
    },
    {
        "id": "inv_012",
        "query": "給我 W03 的庫存資料",
        "sql": "SELECT * FROM img_file WHERE img02 = 'W03'",
        "type": "query_inventory",
    },
    {
        "id": "inv_013",
        "query": "統計所有倉庫的庫存",
        "sql": "SELECT img02, SUM(img10) FROM img_file GROUP BY img02",
        "type": "statistics",
    },
    {
        "id": "inv_014",
        "query": "每個料號的庫存量",
        "sql": "SELECT img01, SUM(img10) FROM img_file GROUP BY img01",
        "type": "statistics",
    },
    {
        "id": "inv_015",
        "query": "查原料倉的庫存",
        "sql": "SELECT * FROM img_file WHERE img02 = 'W01'",
        "type": "query_inventory",
    },
    {
        "id": "inv_016",
        "query": "總計 W01 倉庫的庫存",
        "sql": "SELECT SUM(img10) FROM img_file WHERE img02 = 'W01'",
        "type": "statistics",
    },
    {
        "id": "inv_017",
        "query": "W01 倉庫總共有多少存貨",
        "sql": "SELECT SUM(img10) FROM img_file WHERE img02 = 'W01'",
        "type": "statistics",
    },
    {
        "id": "inv_018",
        "query": "帮我查 W01 的库存",
        "sql": "SELECT * FROM img_file WHERE img02 = 'W01'",
        "type": "query_inventory",
    },
    {
        "id": "inv_019",
        "query": "show me inventory for W01",
        "sql": "SELECT * FROM img_file WHERE img02 = 'W01'",
        "type": "query_inventory",
    },
    {
        "id": "inv_020",
        "query": "庫存量最高的 5 個物料",
        "sql": "SELECT * FROM img_file ORDER BY img10 DESC LIMIT 5",
        "type": "query_inventory",
    },
    {
        "id": "inv_021",
        "query": "找出庫存最少的 10 個料號",
        "sql": "SELECT * FROM img_file ORDER BY img10 ASC LIMIT 10",
        "type": "query_inventory",
    },
    {
        "id": "inv_022",
        "query": "2025 年 1 月的採購記錄",
        "sql": "SELECT * FROM tlf_file WHERE tlf06 LIKE '2025-01%'",
        "type": "query_transaction",
    },
    {
        "id": "inv_023",
        "query": "最近 30 天的進貨",
        "sql": "SELECT * FROM tlf_file WHERE tlf19 = '101' ORDER BY tlf06 DESC LIMIT 100",
        "type": "query_transaction",
    },
    {
        "id": "inv_024",
        "query": "查 W02 成品倉的庫存",
        "sql": "SELECT * FROM img_file WHERE img02 = 'W02'",
        "type": "query_inventory",
    },
    {
        "id": "inv_025",
        "query": "W05 倉有什麼存貨",
        "sql": "SELECT * FROM img_file WHERE img02 = 'W05'",
        "type": "query_inventory",
    },
    {
        "id": "inv_026",
        "query": "計算 W01 加 W02 的庫存總和",
        "sql": "SELECT SUM(img10) FROM img_file WHERE img02 IN ('W01', 'W02')",
        "type": "statistics",
    },
    {
        "id": "inv_027",
        "query": "料號 RM01-003 的庫存",
        "sql": "SELECT * FROM img_file WHERE img01 = 'RM01-003'",
        "type": "query_inventory",
    },
    {
        "id": "inv_028",
        "query": "各倉庫庫存數量統計",
        "sql": "SELECT img02, COUNT(*) FROM img_file GROUP BY img02",
        "type": "statistics",
    },
    {
        "id": "inv_029",
        "query": "庫存為 0 的料號",
        "sql": "SELECT * FROM img_file WHERE img10 = 0",
        "type": "query_inventory",
    },
    {
        "id": "inv_030",
        "query": "查詢 W04 倉庫的進貨記錄",
        "sql": "SELECT * FROM tlf_file WHERE tlf02 = 'W04' LIMIT 100",
        "type": "query_transaction",
    },
    # === 料件主檔查詢 ===
    {
        "id": "ima_001",
        "query": "查詢料號 10-0001 的品名和規格",
        "sql": "SELECT ima01, ima02, ima021 FROM ima_file WHERE ima01 = '10-0001'",
        "type": "query_item",
    },
    {
        "id": "ima_002",
        "query": "列出所有料件",
        "sql": "SELECT * FROM ima_file LIMIT 100",
        "type": "query_item",
    },
    {
        "id": "ima_003",
        "query": "料號 10-0001 是什麼",
        "sql": "SELECT * FROM ima_file WHERE ima01 = '10-0001'",
        "type": "query_item",
    },
    {
        "id": "ima_004",
        "query": "查詢所有料件的品名",
        "sql": "SELECT ima01, ima02 FROM ima_file",
        "type": "query_item",
    },
    {
        "id": "ima_005",
        "query": "有多少種料件",
        "sql": "SELECT COUNT(*) FROM ima_file",
        "type": "calculate_count",
    },
    # === 訂單查詢 ===
    {
        "id": "coptc_001",
        "query": "查詢所有訂單",
        "sql": "SELECT * FROM coptc_file LIMIT 100",
        "type": "query_order",
    },
    {
        "id": "coptc_002",
        "query": "統計每個客户的訂單數量",
        "sql": "SELECT coptc02, COUNT(*) FROM coptc_file GROUP BY coptc02",
        "type": "statistics",
    },
    {
        "id": "coptc_003",
        "query": "查詢最近 10 筆訂單",
        "sql": "SELECT * FROM coptc_file ORDER BY coptc03 DESC LIMIT 10",
        "type": "query_order",
    },
    {
        "id": "coptc_004",
        "query": "某客户的訂單",
        "sql": "SELECT * FROM coptc_file WHERE coptc02 = 'D003' LIMIT 100",
        "type": "query_order",
    },
    {
        "id": "coptc_005",
        "query": "統計未出貨訂單數量",
        "sql": "SELECT COUNT(*) FROM coptc_file WHERE coptc05 = '10'",
        "type": "calculate_count",
    },
    {
        "id": "coptc_006",
        "query": "查詢已出貨訂單",
        "sql": "SELECT * FROM coptc_file WHERE coptc05 = '30' LIMIT 100",
        "type": "query_order",
    },
    {
        "id": "coptc_007",
        "query": "2024 年有多少筆訂單",
        "sql": "SELECT COUNT(*) FROM coptc_file WHERE coptc03 LIKE '2024%'",
        "type": "calculate_count",
    },
    {
        "id": "coptc_008",
        "query": "按月份統計訂單數量",
        "sql": "SELECT SUBSTR(coptc03, 1, 7) as month, COUNT(*) FROM coptc_file GROUP BY month ORDER BY month",
        "type": "statistics",
    },
    # === 訂單明細查詢 ===
    {
        "id": "coptd_001",
        "query": "查詢訂單 SO-2024010001 的明細",
        "sql": "SELECT * FROM coptd_file WHERE coptd01 = 'SO-2024010001'",
        "type": "query_order_detail",
    },
    {
        "id": "coptd_002",
        "query": "查詢某訂單的總金額",
        "sql": "SELECT coptd01, SUM(coptd20 * coptd30) as total FROM coptd_file GROUP BY coptd01",
        "type": "statistics",
    },
    {
        "id": "coptd_003",
        "query": "查詢料號 10-0001 的訂購數量",
        "sql": "SELECT SUM(coptd20) FROM coptd_file WHERE coptd04 = '10-0001'",
        "type": "statistics",
    },
    # === 價格查詢 ===
    {
        "id": "prc_001",
        "query": "查詢料號 10-0001 的單價",
        "sql": "SELECT * FROM prc_file WHERE prc01 = '10-0001' LIMIT 10",
        "type": "query_price",
    },
    {
        "id": "prc_002",
        "query": "料號 10-0001 的最新報價",
        "sql": "SELECT * FROM prc_file WHERE prc01 = '10-0001' ORDER BY prc03 DESC LIMIT 1",
        "type": "query_price",
    },
    {
        "id": "prc_003",
        "query": "所有料件的價格列表",
        "sql": "SELECT prc01, prc02 FROM prc_file LIMIT 100",
        "type": "query_price",
    },
    {
        "id": "prc_004",
        "query": "查詢已批准的訂價",
        "sql": "SELECT * FROM prc_file WHERE prc04 = 'Y' LIMIT 100",
        "type": "query_price",
    },
    # === 客戶查詢 ===
    {
        "id": "cmc_001",
        "query": "查詢所有客戶",
        "sql": "SELECT * FROM cmc_file LIMIT 100",
        "type": "query_customer",
    },
    {
        "id": "cmc_002",
        "query": "某客戶的聯絡人",
        "sql": "SELECT * FROM cmc_file WHERE cmc01 = 'D003'",
        "type": "query_customer",
    },
    # === 採購單頭查詢 ===
    {
        "id": "pmm_001",
        "query": "查詢所有採購單",
        "sql": "SELECT * FROM pmm_file LIMIT 100",
        "type": "query_purchase",
    },
    {
        "id": "pmm_002",
        "query": "按供應商統計採購單數量",
        "sql": "SELECT pmm04, COUNT(*) FROM pmm_file GROUP BY pmm04",
        "type": "statistics",
    },
    {
        "id": "pmm_003",
        "query": "2024 年有多少筆採購單",
        "sql": "SELECT COUNT(*) FROM pmm_file WHERE pmm02 LIKE '2024%'",
        "type": "calculate_count",
    },
    {
        "id": "pmm_004",
        "query": "查詢某供應商的採購單",
        "sql": "SELECT * FROM pmm_file WHERE pmm04 = 'VND001' LIMIT 100",
        "type": "query_purchase",
    },
    {
        "id": "pmm_005",
        "query": "按月份統計採購單數量",
        "sql": "SELECT SUBSTR(pmm02, 1, 7) as month, COUNT(*) FROM pmm_file GROUP BY month ORDER BY month",
        "type": "statistics",
    },
    # === 採購單身查詢 ===
    {
        "id": "pmn_001",
        "query": "查詢採購單 PO-2024010001 的明細",
        "sql": "SELECT * FROM pmn_file WHERE pmn01 = 'PO-2024010001'",
        "type": "query_purchase_detail",
    },
    {
        "id": "pmn_002",
        "query": "查詢某料號的採購數量",
        "sql": "SELECT SUM(pmn20) FROM pmn_file WHERE pmn04 = '10-0001'",
        "type": "statistics",
    },
    {
        "id": "pmn_003",
        "query": "查詢已交貨數量",
        "sql": "SELECT SUM(pmn31) FROM pmn_file",
        "type": "statistics",
    },
    # === 收料單查詢 ===
    {
        "id": "rvb_001",
        "query": "查詢所有收料記錄",
        "sql": "SELECT * FROM rvb_file LIMIT 100",
        "type": "query_receiving",
    },
    {
        "id": "rvb_002",
        "query": "查詢某採購單的收料記錄",
        "sql": "SELECT * FROM rvb_file WHERE rvb07 = 'PO-2024010001'",
        "type": "query_receiving",
    },
    {
        "id": "rvb_003",
        "query": "查詢某料號的收料數量",
        "sql": "SELECT SUM(rvb33) FROM rvb_file WHERE rvb05 = '10-0001'",
        "type": "statistics",
    },
    # === 供應商查詢 ===
    {
        "id": "pmc_001",
        "query": "查詢所有供應商",
        "sql": "SELECT * FROM pmc_file LIMIT 100",
        "type": "query_vendor",
    },
    {
        "id": "pmc_002",
        "query": "某供應商的聯絡人",
        "sql": "SELECT * FROM pmc_file WHERE pmc01 = 'VND001'",
        "type": "query_vendor",
    },
    # === 採購交易查詢 (tlf) ===
    {
        "id": "pur_001",
        "query": "2024 年採購進貨筆數",
        "sql": "SELECT COUNT(*) FROM tlf_file WHERE tlf19 = '101' AND tlf06 LIKE '2024%'",
        "type": "calculate_count",
    },
    {
        "id": "pur_002",
        "query": "查詢所有採購進貨交易",
        "sql": "SELECT * FROM tlf_file WHERE tlf19 = '101' LIMIT 100",
        "type": "query_transaction",
    },
    {
        "id": "pur_003",
        "query": "按供應商統計採購量",
        "sql": "SELECT tlf14, SUM(tlf10) FROM tlf_file WHERE tlf19 = '101' GROUP BY tlf14",
        "type": "statistics",
    },
    {
        "id": "pur_004",
        "query": "計算 2024 年採購總數量",
        "sql": "SELECT SUM(tlf10) FROM tlf_file WHERE tlf19 = '101' AND tlf06 LIKE '2024%'",
        "type": "statistics",
    },
    {
        "id": "pur_005",
        "query": "10-0003 上個月的採購交易",
        "sql": "SELECT * FROM tlf_file WHERE tlf01 = '10-0003' AND tlf19 = '101' AND tlf06 >= DATE_SUB(CURDATE(), INTERVAL 1 MONTH)",
        "type": "query_transaction",
    },
    {
        "id": "pur_006",
        "query": "查詢料號 10-0001 的採購記錄",
        "sql": "SELECT * FROM tlf_file WHERE tlf01 = '10-0001' AND tlf19 = '101'",
        "type": "query_transaction",
    },
    {
        "id": "pur_007",
        "query": "上個月的採購進貨",
        "sql": "SELECT * FROM tlf_file WHERE tlf19 = '101' AND tlf06 >= DATE_SUB(CURDATE(), INTERVAL 1 MONTH)",
        "type": "query_transaction",
    },
    {
        "id": "pur_008",
        "query": "RM05-008 買進多少",
        "sql": "SELECT SUM(tlf10) FROM tlf_file WHERE tlf01 = 'RM05-008' AND tlf19 = '101'",
        "type": "statistics",
    },
    {
        "id": "pur_009",
        "query": "RM05-008 進貨多少",
        "sql": "SELECT SUM(tlf10) FROM tlf_file WHERE tlf01 = 'RM05-008' AND tlf19 = '101'",
        "type": "statistics",
    },
    {
        "id": "pur_010",
        "query": "RM05-008 買了多少",
        "sql": "SELECT SUM(tlf10) FROM tlf_file WHERE tlf01 = 'RM05-008' AND tlf19 = '101'",
        "type": "statistics",
    },
    {
        "id": "pur_011",
        "query": "料號 RM05-008 上月進",
        "sql": "SELECT * FROM tlf_file WHERE tlf01 = 'RM05-008' AND tlf19 = '101' AND tlf06 >= DATE_SUB(CURDATE(), INTERVAL 1 MONTH)",
        "type": "query_transaction",
    },
    # === 銷售交易查詢 (tlf) ===
    {
        "id": "sal_001",
        "query": "2024 年銷售出庫筆數",
        "sql": "SELECT COUNT(*) FROM tlf_file WHERE tlf19 = '202' AND tlf06 LIKE '2024%'",
        "type": "calculate_count",
    },
    {
        "id": "sal_002",
        "query": "查詢所有銷貨記錄",
        "sql": "SELECT * FROM tlf_file WHERE tlf19 = '202' LIMIT 100",
        "type": "query_transaction",
    },
    {
        "id": "sal_003",
        "query": "按客户統計銷售額",
        "sql": "SELECT coptc02, SUM(coptd20 * coptd30) FROM coptc_file JOIN coptd_file ON coptc01 = coptd01 GROUP BY coptc02",
        "type": "statistics",
    },
    {
        "id": "sal_004",
        "query": "RM05-008 賣出多少",
        "sql": "SELECT SUM(tlf10) FROM tlf_file WHERE tlf01 = 'RM05-008' AND tlf19 = '202'",
        "type": "statistics",
    },
    {
        "id": "sal_005",
        "query": "RM05-008 出貨多少",
        "sql": "SELECT SUM(tlf10) FROM tlf_file WHERE tlf01 = 'RM05-008' AND tlf19 = '202'",
        "type": "statistics",
    },
    {
        "id": "sal_006",
        "query": "RM05-008 賣了多少",
        "sql": "SELECT SUM(tlf10) FROM tlf_file WHERE tlf01 = 'RM05-008' AND tlf19 = '202'",
        "type": "statistics",
    },
    # === 銷售相關 ===
    {
        "id": "sal_001",
        "query": "2024 年銷售出庫筆數",
        "sql": "SELECT COUNT(*) FROM tlf_file WHERE tlf19 = '202' AND tlf06 LIKE '2024%'",
        "type": "calculate_count",
    },
    {
        "id": "sal_002",
        "query": "查詢所有銷貨記錄",
        "sql": "SELECT * FROM tlf_file WHERE tlf19 = '202' LIMIT 100",
        "type": "query_transaction",
    },
    {
        "id": "sal_003",
        "query": "按客户統計訂單金額",
        "sql": "SELECT coptc02, SUM(coptd20 * coptd30) FROM coptc_file JOIN coptd_file ON coptc01 = coptd01 GROUP BY coptc02",
        "type": "statistics",
    },
    # === 庫位相關 ===
    {
        "id": "loc_001",
        "query": "查詢 W01 倉庫的所有儲位",
        "sql": "SELECT DISTINCT img03 FROM img_file WHERE img02 = 'W01'",
        "type": "query_inventory",
    },
    {
        "id": "loc_002",
        "query": "某儲位的庫存",
        "sql": "SELECT * FROM img_file WHERE img02 = 'W01' AND img03 = 'LOC001'",
        "type": "query_inventory",
    },
    # === 變化表達方式 ===
    {
        "id": "var_001",
        "query": "給我 W01 倉現在的庫存",
        "sql": "SELECT * FROM img_file WHERE img02 = 'W01'",
        "type": "query_inventory",
    },
    {
        "id": "var_002",
        "query": "現在 W02 倉有多少貨",
        "sql": "SELECT SUM(img10) FROM img_file WHERE img02 = 'W02'",
        "type": "statistics",
    },
    {
        "id": "var_003",
        "query": "原料倉存貨總額",
        "sql": "SELECT SUM(img10) FROM img_file WHERE img02 = 'W01'",
        "type": "statistics",
    },
    {
        "id": "var_004",
        "query": "成品倉各料號庫存",
        "sql": "SELECT img01, SUM(img10) FROM img_file WHERE img02 = 'W03' GROUP BY img01",
        "type": "statistics",
    },
    {
        "id": "var_005",
        "query": "顯示 W04 的庫存",
        "sql": "SELECT * FROM img_file WHERE img02 = 'W04'",
        "type": "query_inventory",
    },
]


def get_embedding(text: str):
    """獲取文本嵌入向量"""
    payload = {"model": EMBEDDING_MODEL, "prompt": text}
    response = requests.post(EMBEDDING_ENDPOINT, json=payload, timeout=60)
    response.raise_for_status()
    return response.json()["embedding"]


def init_rag():
    """初始化 RAG 系統"""
    print("=" * 60)
    print("初始化 DataAgent Intent RAG 系統")
    print("=" * 60)

    client = QdrantClient(url=QDRANT_URL)

    # 刪除舊 collection
    try:
        client.delete_collection(COLLECTION_NAME)
        print(f"🗑️ 已刪除舊 collection: {COLLECTION_NAME}")
    except:
        pass

    # 建立新 collection
    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=VECTOR_DIM, distance=Distance.COSINE),
    )
    print(f"✅ 已建立 collection: {COLLECTION_NAME}")

    # 生成向量並存入
    print(f"\n📦 正在處理 {len(INTENT_TEMPLATES)} 個意圖模板...")

    points = []
    for i, template in enumerate(INTENT_TEMPLATES):
        combined_text = f"{template['query']} | {template['sql']}"
        embedding = get_embedding(combined_text)

        point = PointStruct(
            id=i + 1,
            vector=embedding,
            payload=template,
        )
        points.append(point)
        print(f"  [{i + 1:02d}/{len(INTENT_TEMPLATES)}] {template['query']}")

    print(f"\n💾 正在存入 Qdrant...")
    client.upsert(collection_name=COLLECTION_NAME, points=points)

    print(f"\n✅ RAG 系統初始化完成！")
    print(f"   Collection: {COLLECTION_NAME}")
    print(f"   模板數量: {len(INTENT_TEMPLATES)}")
    print(f"   向量維度: {VECTOR_DIM}")


def query_rag(query: str, top_k: int = 3):
    """查詢意圖"""
    client = QdrantClient(url=QDRANT_URL)

    embedding = get_embedding(query)
    results = client.query_points(collection_name=COLLECTION_NAME, query=embedding, limit=top_k)

    print("=" * 60)
    print(f"查詢: {query}")
    print("=" * 60)

    for i, r in enumerate(results.points, 1):
        if r.payload:
            query_text = r.payload.get("query", "N/A")
            sql_text = r.payload.get("sql", "N/A")
        else:
            query_text = "N/A"
            sql_text = "N/A"
        print(f"\n{i}. {query_text}")
        print(f"   相似度: {r.score:.4f}")
        print(f"   SQL: {sql_text}")

    return [r.payload for r in results.points]


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "init":
        init_rag()
    elif len(sys.argv) > 1:
        query_rag(" ".join(sys.argv[1:]))
    else:
        print("用法:")
        print("  python data_agent_intent_rag.py init   # 初始化")
        print("  python data_agent_intent_rag.py <查詢>  # 查詢")
