# 代碼功能說明: 自然語言查詢頁面
# 創建日期: 2026-01-31
# 創建人: Daniel Chung
# 最後修改日期: 2026-02-01

"""自然語言查詢頁面組件"""

import streamlit as st
import pandas as pd
from datetime import datetime

from dashboard.services.data_agent_client import call_data_agent_sync


def render_nlp(
    schema_info: dict,
    intent_analyzer=None,
    INTENT_ANALYZER_AVAILABLE: bool = False,
) -> None:
    """渲染自然語言查詢頁面"""
    st.markdown("### 🤖 自然語言查詢")
    st.caption("輸入自然語言，系統自動轉換為 SQL 查詢")

    left_col, right_col = st.columns([1, 1], gap="medium")

    with left_col:
        st.markdown("**💬 對話**")

        if "chat_messages" not in st.session_state:
            st.session_state.chat_messages = [
                {
                    "role": "assistant",
                    "content": "您好！請輸入您的問題，例如：「查詢 W01 倉庫的庫存總量」",
                    "timestamp": datetime.now().isoformat(),
                }
            ]

        chat_container = st.container(height=300)
        with chat_container:
            for msg in st.session_state.chat_messages:
                _render_message(msg["role"], msg["content"])

        query_examples = {
            "warehouse_query": "查詢 W01 倉庫的庫存總量",
            "negative_inventory": "列出所有負庫存的物料",
            "purchase_2024": "統計 2024 年的採購進貨筆數",
            "top_10_items": "列出前 10 個庫存量最多的物料",
        }

        selected_example = st.selectbox(
            "範例查詢",
            options=[None] + list(query_examples.keys()),
            format_func=lambda x: "自訂輸入..." if x is None else query_examples[x],
            key="nlp_example_select",
        )

        if selected_example:
            st.session_state.pending_query = query_examples[selected_example]

        if "pending_query" not in st.session_state:
            st.session_state.pending_query = ""

        user_query = st.text_area(
            "輸入問題",
            value=st.session_state.pending_query,
            height=80,
            placeholder="例如：查詢 W01 倉庫的庫存總量",
            key="nlp_input",
        )

        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("🚀 送出", type="primary", use_container_width=True, key="nlp_submit"):
                if user_query.strip():
                    st.session_state.chat_messages.append(
                        {
                            "role": "user",
                            "content": user_query.strip(),
                            "timestamp": datetime.now().isoformat(),
                        }
                    )
                    st.session_state.pending_query = ""
                    st.session_state.current_query = user_query.strip()
                    st.rerun()
                else:
                    st.error("請輸入查詢內容")

        with col_btn2:
            if st.button("🗑️ 清空", use_container_width=True, key="nlp_clear"):
                st.session_state.chat_messages = [
                    {
                        "role": "assistant",
                        "content": "您好！請輸入您的問題",
                        "timestamp": datetime.now().isoformat(),
                    }
                ]
                st.session_state.current_query = ""
                st.rerun()

    with right_col:
        if "current_query" in st.session_state and st.session_state.current_query:
            _render_query_process(
                st.session_state.current_query,
                schema_info,
                intent_analyzer,
                INTENT_ANALYZER_AVAILABLE,
            )
        else:
            st.info("👈 請在左側輸入查詢問題")


def _render_message(role: str, content: str) -> None:
    """渲染單條訊息"""
    if role == "user":
        st.markdown(
            f"""
            <div style="
                background-color: #4CAF50;
                color: white;
                padding: 8px 12px;
                border-radius: 12px 12px 4px 12px;
                margin: 4px 0;
                margin-left: 30px;
                font-size: 0.9em;
            ">{content}</div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"""
            <div style="
                background-color: #f0f0f0;
                color: black;
                padding: 8px 12px;
                border-radius: 12px 12px 12px 4px;
                margin: 4px 0;
                margin-right: 30px;
                font-size: 0.9em;
            ">{content}</div>
            """,
            unsafe_allow_html=True,
        )


def _render_query_process(
    natural_query: str,
    schema_info: dict,
    intent_analyzer=None,
    INTENT_ANALYZER_AVAILABLE: bool = False,
) -> None:
    """渲染查詢處理過程"""
    st.markdown("**📋 執行步驟**")

    tasks = [
        {"name": "分析查詢意圖", "status": "pending"},
        {"name": "生成 SQL", "status": "pending"},
        {"name": "執行查詢", "status": "pending"},
        {"name": "顯示結果", "status": "pending"},
    ]

    task_containers = [st.empty() for _ in tasks]

    def update_task_display() -> None:
        for i, task in enumerate(tasks):
            status_icon = {
                "pending": "⏳",
                "completed": "✅",
                "failed": "❌",
                "in_progress": "🔄",
            }.get(task["status"], "⚠️")
            with task_containers[i].container():
                st.markdown(f"{status_icon} {task['name']}")

    update_task_display()

    try:
        action = "text_to_sql"
        query_params = {}

        if any(
            kw in natural_query
            for kw in ["料號", "庫存", "倉庫", "W0", "W1", "W2", "W3", "W4", "W5"]
        ):
            action = "text_to_sql"
        elif "負庫存" in natural_query:
            action = "text_to_sql"
        elif "採購" in natural_query:
            action = "text_to_sql"
        elif "前 10" in natural_query or "Top 10" in natural_query:
            action = "text_to_sql"

        tasks[0]["status"] = "in_progress"
        update_task_display()

        if INTENT_ANALYZER_AVAILABLE and intent_analyzer is not None:
            intent_result = intent_analyzer.analyze(natural_query)
            intent_dict = intent_result.to_dict()
        else:
            import re

            part_match = re.search(
                r"(\d{2}-\d{4}|[A-Z]{2}\d{2}-\d+|[A-Z]{2,4}-\d{3,})", natural_query.upper()
            )
            warehouse_match = re.search(r"(W0[1-5])", natural_query.upper())

            if part_match:
                subject_value = part_match.group(1)
                warehouse = ""
                description = f"查詢料號 {subject_value}"
            elif warehouse_match:
                subject_value = ""
                warehouse = warehouse_match.group(1)
                description = f"查詢 {warehouse}"
            else:
                subject_value = ""
                warehouse = "W01"
                description = "查詢 W01"

            intent_dict = {
                "query": natural_query,
                "intent_type": "query_inventory",
                "description": description,
                "table": "img_file",
                "aggregation": "SUM",
                "group_by": "img01",
                "subject_value": subject_value,
                "warehouse": warehouse,
            }

        tasks[0]["status"] = "completed"
        tasks[1]["status"] = "in_progress"
        update_task_display()

        with st.spinner("生成 SQL..."):
            if action == "text_to_sql":
                query_params["schema_info"] = schema_info
                query_params["intent_analysis"] = {
                    "intent_type": intent_dict.get("intent_type", "query_inventory"),
                    "description": intent_dict.get("description", ""),
                    "table": intent_dict.get("table", "img_file"),
                }
            result = call_data_agent_sync(natural_query, action=action, **query_params)

        if result.get("error"):
            tasks[1]["status"] = "failed"
            update_task_display()
            with task_containers[1].container():
                st.error(f"SQL 生成失敗：{result.get('error')}")
        else:
            tasks[1]["status"] = "completed"
            tasks[2]["status"] = "in_progress"
            update_task_display()

            outer_result = result.get("result", {})
            inner_result = outer_result.get("result", {}) if isinstance(outer_result, dict) else {}
            sql_query = inner_result.get("sql_query", "") if isinstance(inner_result, dict) else ""

            with task_containers[1].container():
                st.code(sql_query, language="sql", height=80)

            with st.spinner("執行查詢..."):
                execute_result = call_data_agent_sync(
                    "", action="execute_sql_on_datalake", sql_query_datalake=sql_query
                )

            if execute_result.get("error"):
                tasks[2]["status"] = "failed"
                update_task_display()
            else:
                tasks[2]["status"] = "completed"
                tasks[3]["status"] = "completed"
                update_task_display()

                exec_outer = execute_result.get("result", {})
                exec_inner = exec_outer.get("result", {}) if isinstance(exec_outer, dict) else {}
                rows = exec_inner.get("rows", []) if isinstance(exec_inner, dict) else []
                row_count = exec_inner.get("row_count", 0) if isinstance(exec_inner, dict) else 0

                st.success(f"✅ 返回 {row_count} 筆記錄")
                if rows:
                    df_result = pd.DataFrame(rows[:20])
                    st.dataframe(df_result, use_container_width=True, height=200)

                    st.session_state.chat_messages.append(
                        {
                            "role": "assistant",
                            "content": f"查詢完成！共返回 {row_count} 筆記錄",
                            "timestamp": datetime.now().isoformat(),
                        }
                    )

    except Exception as e:
        st.error(f"錯誤：{str(e)}")
        for task in tasks:
            if task["status"] in ("pending", "in_progress"):
                task["status"] = "failed"
        update_task_display()
