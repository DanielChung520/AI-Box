# 代碼功能說明: Data-Agent 數據湖 API 服務
# 創建日期: 2026-02-01
# 作者: AI-Box Development Team

"""FastAPI 服務 - 提供數據湖儀表板 API"""

import sys
import re
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Any
import pandas as pd
import httpx
import os

# 添加專案根目錄到 Python 路徑
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# 導入 DataLakeClient
from dashboard.config import DATA_AGENT_URL, DEFAULT_BUCKET, SEAWEEDFS_ENDPOINT
from dashboard.services.data_access import DataLakeClient

app = FastAPI(
    title="Data-Agent Datalake API",
    description="數據湖儀表板 API 服務",
    version="1.0.0",
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化 DataLakeClient
data_lake_client = DataLakeClient()

# API 客戶端
DATA_AGENT_ENDPOINT = os.getenv("DATA_AGENT_SERVICE_URL", "http://localhost:8004/execute")


class QueryRequest(BaseModel):
    query: str
    action: str = "text_to_sql"


class QueryResponse(BaseModel):
    result: Any
    sql: Optional[str] = None
    response: Optional[str] = None


@app.get("/health")
async def health_check():
    """健康檢查"""
    return {"status": "ok", "service": "datalake-api"}


@app.get("/api/v1/datalake/inventory", response_model=List[dict])
async def get_inventory():
    """獲取庫存數據"""
    try:
        df = data_lake_client.get_inventory_status()
        # 轉換為列表格式，限制 1000 筆
        return df.head(1000).to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/datalake/transactions", response_model=List[dict])
async def get_transactions():
    """獲取交易數據"""
    try:
        df = data_lake_client.query_table("tlf_file_large", is_large=True)
        # 轉換為列表格式，限制 1000 筆
        return df.head(1000).to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/datalake/items", response_model=List[dict])
async def get_items():
    """獲取料號數據"""
    try:
        df = data_lake_client.query_table("ima_file")
        # 轉換為列表格式，限制 1000 筆
        return df.head(1000).to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/datalake/purchase/pmm", response_model=List[dict])
async def get_purchase_pmm():
    """獲取採購單頭"""
    try:
        df = data_lake_client.query_table("pmm_file", years=[2024, 2025])
        return df.head(500).to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/datalake/purchase/pmn", response_model=List[dict])
async def get_purchase_pmn():
    """獲取採購單身"""
    try:
        df = data_lake_client.query_table("pmn_file", years=[2024, 2025])
        return df.head(500).to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/datalake/purchase/rvb", response_model=List[dict])
async def get_purchase_rvb():
    """獲取收料單"""
    try:
        df = data_lake_client.query_table("rvb_file", years=[2024, 2025])
        return df.head(500).to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/datalake/vendors", response_model=List[dict])
async def get_vendors():
    """獲取供應商"""
    try:
        df = data_lake_client.query_table("pmc_file")
        return df.head(100).to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/datalake/orders/coptc", response_model=List[dict])
async def get_orders_coptc():
    """獲取訂單單頭"""
    try:
        df = data_lake_client.query_table("coptc_file", years=[2024, 2025])
        return df.head(500).to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/datalake/orders/coptd", response_model=List[dict])
async def get_orders_coptd():
    """獲取訂單單身"""
    try:
        df = data_lake_client.query_table("coptd_file", years=[2024, 2025])
        return df.head(500).to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/datalake/pricing", response_model=List[dict])
async def get_pricing():
    """獲取訂價單"""
    try:
        df = data_lake_client.query_table("prc_file")
        return df.head(500).to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/datalake/customers", response_model=List[dict])
async def get_customers():
    """獲取客戶"""
    try:
        df = data_lake_client.query_table("cmc_file")
        return df.head(100).to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def simple_intent_analysis(query: str) -> dict:
    """簡單的意圖分析"""
    query_lower = query.lower()
    query_upper = query.upper()

    # 識別交易類型 - 預設為採購進貨
    transaction_type = "101"  # 101: 採購進貨, 202: 銷售出庫

    # 識別表格 - 採購相關 (買、買進、進、進貨)
    if any(kw in query_lower for kw in ["採購", "買", "買進", "進", "進貨"]):
        table = "tlf_file"
        # 識別是否為銷售相關
        if any(kw in query_lower for kw in ["賣", "賣出", "出貨", "銷售"]):
            transaction_type = "202"  # 銷售出庫
    elif any(kw in query_lower for kw in ["訂單", "出貨", "客戶"]):
        table = "coptc_file"
    elif any(kw in query_lower for kw in ["單價", "價格", "訂價"]):
        table = "prc_file"
    elif any(kw in query_lower for kw in ["料件", "物料", "品名", "規格"]):
        table = "ima_file"
    elif any(kw in query_lower for kw in ["採購單"]):
        table = "pmm_file"
    elif any(kw in query_lower for kw in ["收料單"]):
        table = "rvb_file"
    else:
        table = "img_file"  # 預設為庫存表

    # 識別意圖類型
    intent_type = "query_inventory"
    if any(
        kw in query_lower
        for kw in ["採購", "買", "買進", "進", "進貨", "賣", "賣出", "出貨", "銷售", "交易", "異動"]
    ):
        intent_type = "query_transaction"
    elif any(kw in query_lower for kw in ["訂單", "客戶"]):
        intent_type = "query_order"
    elif any(kw in query_lower for kw in ["單價", "價格", "訂價"]):
        intent_type = "query_price"

    # 識別料號
    item_match = re.search(r"(\d{2}-\d{4}|[A-Z]{2}\d{2}-\d+|[A-Z]{2,4}-\d{3,})", query_upper)
    item_code = item_match.group(1) if item_match else None

    # 識別倉庫
    warehouse_match = re.search(r"(W0[1-5])", query_upper)
    warehouse = warehouse_match.group(1) if warehouse_match else None

    # 識別時間條件
    time_condition = ""
    time_description = ""

    # 上個月 / 上月 / 前月
    if "上個月" in query_lower or "上月" in query_lower or "前月" in query_lower:
        time_condition = "tlf06 >= DATE_SUB(CURDATE(), INTERVAL 1 MONTH)"
        time_description = "上個月"

    # 最近 N 天
    recent_match = re.search(r"最近(\d+)天", query_lower)
    if recent_match:
        days = recent_match.group(1)
        time_condition = f"tlf06 >= DATE_SUB(CURDATE(), INTERVAL {days} DAY)"
        time_description = f"最近{days}天"

    # 特定年月 (如 2024年1月, 2024-01)
    year_month_match = re.search(r"(\d{4})[年/\-](\d{1,2})", query)
    if year_month_match:
        year = year_month_match.group(1)
        month = year_month_match.group(2).zfill(2)
        time_condition = f"tlf06 LIKE '{year}-{month}%'"
        time_description = f"{year}年{month}月"

    # 特定年份
    year_match = re.search(r"(\d{4})年", query)
    if year_match and not year_month_match:
        year = year_match.group(1)
        time_condition = f"tlf06 LIKE '{year}%'"
        time_description = f"{year}年"

    return {
        "table": table,
        "intent_type": intent_type,
        "subject_value": item_code,
        "warehouse": warehouse,
        "time_condition": time_condition,
        "time_description": time_description,
        "transaction_type": transaction_type,
    }


@app.post("/api/v1/data-agent/query", response_model=QueryResponse)
async def nlp_query(request: QueryRequest):
    """自然語言查詢 - 正面表列策略"""
    try:
        # Step 1: 簡單意圖分析
        intent_info = simple_intent_analysis(request.query)

        # 步驟 2: 快速關鍵字檢查是否在正面表列
        query_lower = request.query.lower()

        # 正面表列關鍵字
        positive_keywords = [
            # 採購相關
            "採購",
            "買",
            "買進",
            "進",
            "進貨",
            "收料",
            # 銷售相關
            "賣",
            "賣出",
            "出貨",
            "銷售",
            # 數量查詢
            "多少",
            "總數",
            "數量",
            "合計",
            "總計",
            # 時間
            "上月",
            "上個月",
            "前月",
            "最近",
            "今年",
            "去年",
            # 料號
            "10-",
            "RM",
            "ABC-",
            # 庫存相關
            "庫存",
            "存量",
            "W01",
            "W02",
            "W03",
            "W04",
            "W05",
            # 訂單相關
            "訂單",
            "客戶",
        ]

        is_in_positive_list = any(kw in query_lower for kw in positive_keywords)

        async with httpx.AsyncClient() as client:
            response = await client.post(
                DATA_AGENT_ENDPOINT,
                json={
                    "task_id": "nlp_query",
                    "task_type": "data_query",
                    "task_data": {
                        "action": request.action or "text_to_sql",
                        "natural_language": request.query,
                    },
                },
                timeout=60.0,
            )
            data = response.json()

            agent_inner = data.get("result", {})
            agent_result = agent_inner.get("result", {}) if agent_inner else {}

            sql_query = agent_result.get("sql_query", "")
            explanation = agent_result.get("explanation", "")

            # 檢查是否需要回問/回覆
            need_clarification = False
            clarification_message = ""

            # 條件 1: 不在正面表列
            if not is_in_positive_list:
                need_clarification = True
                clarification_message = "抱歉，我目前的專業領域是「進銷存數據查詢」，例如：\n- 查詢某料號的庫存\n- 查詢某段時間的交易\n- 計算採購或銷售數量\n\n請問您的問題是否與這些相關？"

            # 條件 2: 通用 SQL 且意圖不明確
            if "img_file" in sql_query.lower() and intent_info["table"] == "img_file":
                if not intent_info["subject_value"] and not intent_info["warehouse"]:
                    need_clarification = True
                    clarification_message = (
                        "請問您想查詢哪個料號或哪個倉庫的數據？例如：「RM05-008 在 W01 的庫存」"
                    )

            # 條件 3: 庫存查詢但沒有具體條件
            if intent_info["table"] == "img_file" and not is_in_positive_list:
                need_clarification = True
                clarification_message = (
                    "請問您想查詢什麼？例如：\n- 「RM05-008 的庫存量」\n- 「W01 倉庫的庫存」"
                )

            # 如果需要回問/回覆
            if need_clarification:
                return {
                    "sql": "",
                    "response": clarification_message,
                    "result": {
                        "data": [],
                        "rowCount": 0,
                        "sql_query": "",
                        "explanation": clarification_message,
                        "confidence": 0,
                        "intent_type": "needs_clarification",
                        "need_clarification": True,
                    },
                }

            # 以下是原有的 SQL 生成邏輯...
            data = response.json()

            agent_inner = data.get("result", {})
            agent_result = agent_inner.get("result", {}) if agent_inner else {}

            sql_query = agent_result.get("sql_query", "")
            explanation = agent_result.get("explanation", "")

            # 如果 SQL 是通用的，根據意圖分析修正
            if "img_file" in sql_query.lower() and intent_info["table"] == "tlf_file":
                # 構建 SQL
                item_code = intent_info["subject_value"]
                time_cond = intent_info.get("time_condition", "")

                # 檢查是否為數量查詢（如「採購多少」）
                is_quantity_query = any(
                    kw in request.query.lower() for kw in ["多少", "總數", "數量", "合計"]
                )

                if is_quantity_query:
                    # 計算總數量
                    conditions = []
                    if item_code:
                        conditions.append(f"tlf01 = '{item_code}'")
                    trans_type = intent_info.get("transaction_type", "101")
                    conditions.append(f"tlf19 = '{trans_type}'")
                    if time_cond:
                        conditions.append(time_cond)

                    sql_query = (
                        "SELECT tlf01, SUM(tlf10) as total_qty FROM tlf_file WHERE "
                        + " AND ".join(conditions)
                        + " GROUP BY tlf01"
                    )
                    trans_desc = "採購進貨" if trans_type == "101" else "銷售出庫"
                    explanation = "查詢 {} 的{}總數量{}".format(
                        item_code or "所有料號",
                        trans_desc,
                        "（{}）".format(intent_info.get("time_description", ""))
                        if intent_info.get("time_description")
                        else "",
                    )
                else:
                    # 一般查詢
                    conditions = []
                    if item_code:
                        conditions.append(f"tlf01 = '{item_code}'")
                    trans_type = intent_info.get("transaction_type", "101")
                    conditions.append(f"tlf19 = '{trans_type}'")
                    if time_cond:
                        conditions.append(time_cond)

                    sql_query = "SELECT * FROM tlf_file WHERE " + " AND ".join(conditions)
                    trans_desc = "採購進貨" if trans_type == "101" else "銷售出庫"
                    explanation = "查詢 {} 的{}交易{}".format(
                        item_code or "所有料號",
                        trans_desc,
                        "（{}）".format(intent_info.get("time_description", ""))
                        if intent_info.get("time_description")
                        else "",
                    )

            # 執行 SQL 查詢
            query_data = []
            if sql_query:
                try:
                    sql_lower = sql_query.lower()
                    df = pd.DataFrame()

                    if "tlf_file" in sql_lower:
                        df = data_lake_client.query_table("tlf_file_large", is_large=True)
                        if intent_info["subject_value"]:
                            df = df[df["tlf01"] == intent_info["subject_value"]]
                        trans_type = intent_info.get("transaction_type", "101")
                        df = df[df["tlf19"] == trans_type]
                    elif "img_file" in sql_lower:
                        df = data_lake_client.get_inventory_status()
                        if intent_info["subject_value"]:
                            df = df[df["img01"] == intent_info["subject_value"]]
                        if intent_info["warehouse"]:
                            df = df[df["img02"] == intent_info["warehouse"]]
                    elif "ima_file" in sql_lower:
                        df = data_lake_client.query_table("ima_file")
                        if intent_info["subject_value"]:
                            df = df[df["ima01"] == intent_info["subject_value"]]
                    elif "coptc_file" in sql_lower:
                        df = data_lake_client.query_table("coptc_file", years=[2024, 2025])
                        if intent_info["subject_value"]:
                            df = df[df["coptc02"] == intent_info["subject_value"]]
                    else:
                        df = data_lake_client.get_inventory_status()

                    if not df.empty:
                        query_data = df.head(100).to_dict(orient="records")

                    if not explanation:
                        filters = []
                        if intent_info["subject_value"]:
                            filters.append(f"料號={intent_info['subject_value']}")
                        if intent_info["warehouse"]:
                            filters.append(f"倉庫={intent_info['warehouse']}")
                        explanation = "查詢 {}，共返回 {} 筆記錄".format(
                            " 且 ".join(filters) if filters else "所有數據", len(query_data)
                        )

                except Exception as e:
                    query_data = [{"error": str(e)}]

            result = {
                "sql": sql_query,
                "response": explanation,
                "result": {
                    "data": query_data,
                    "rowCount": len(query_data),
                    "sql_query": sql_query,
                    "explanation": explanation,
                    "confidence": agent_result.get("confidence", 0) or 0.7,
                    "intent_type": intent_info["intent_type"],
                },
            }
            return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("API_PORT", "8005"))
    uvicorn.run(app, host="0.0.0.0", port=port)
