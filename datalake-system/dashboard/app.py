# 代碼功能說明: Tiptop 模擬系統 Dashboard 主程式 - 重構版
# 創建日期: 2026-01-29
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-31

"""Tiptop 模擬系統 Dashboard - Streamlit 儀表板（重構版）"""

import sys
from pathlib import Path

_dashboard_dir = Path(__file__).resolve().parent
_datalake_root = _dashboard_dir.parent
if str(_datalake_root) not in sys.path:
    sys.path.insert(0, str(_datalake_root))

import streamlit as st
import pandas as pd
import json

from dashboard.config import SCHEMA_REGISTRY_PATH
from dashboard.services.data_access import DataLakeClient
from dashboard.components.sidebar import render_sidebar
from dashboard.views.home import render_home
from dashboard.views.inventory import render_inventory
from dashboard.views.transaction import render_transaction
from dashboard.views.purchase import render_purchase
from dashboard.views.order import render_order
from dashboard.views.query import render_query
from dashboard.views.nlp import render_nlp


st.set_page_config(page_title="Data-Agent | Tiptop 數據湖儀表板", layout="wide")

st.markdown(
    """
<style>
    .block-container {
        padding-top: 0.5rem;
        padding-bottom: 0.5rem;
        padding-left: 1rem;
        padding-right: 1rem;
    }
    div[data-testid="stMarkdownContainer"] {
        margin-bottom: 0.2rem;
    }
    div[data-testid="stCaption"] {
        margin-top: -0.3rem;
        margin-bottom: 0.3rem;
    }
    .stDataFrame {
        padding: 0.2rem;
    }
    div[data-testid="stPlotlyChart"] {
        margin-bottom: 0.3rem;
    }
    div[data-testid="stMetric"] {
        padding: 0.3rem;
    }
    section[data-testid="stSidebar"] {
        padding: 0.5rem;
    }
    div[data-testid="stExpander"] {
        margin-top: 0.2rem;
        margin-bottom: 0.2rem;
    }
    .stTextInput > div > div {
        padding: 0.2rem;
    }
    .stSelectbox > div > div {
        padding: 0.2rem;
    }
    .stRadio > div {
        padding: 0.2rem;
    }
    .stButton > button {
        margin: 0.1rem;
        padding: 0.3rem 0.5rem;
    }
    div[data-testid="stHorizontalBlock"] {
        gap: 0.5rem;
    }
    div[data-testid="stVerticalBlock"] {
        gap: 0.3rem;
    }
    h3 {
        margin-bottom: 0.2rem;
        margin-top: 0.3rem;
    }
    hr {
        margin: 0.3rem 0;
    }
    /* 隱藏內建 header */
    header[data-testid="stHeader"] {
        display: none !important;
    }
    /* 自定義頂部標題欄 */
    .custom-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0.3rem 0.5rem;
        background: linear-gradient(90deg, #1e1e1e 0%, #2d2d2d 100%);
        border-radius: 0.3rem;
        margin-bottom: 0.3rem;
        border-left: 4px solid #4CAF50;
    }
    .custom-header h1 {
        font-size: 1.1rem !important;
        font-weight: 600;
        margin: 0;
        padding: 0;
        color: #ffffff;
    }
    .custom-header .subtitle {
        font-size: 0.75rem;
        color: #aaaaaa;
        margin: 0;
        padding: 0;
    }
    .custom-header .version {
        font-size: 0.7rem;
        color: #666666;
        background: #333333;
        padding: 0.1rem 0.4rem;
        border-radius: 0.2rem;
    }
 </style>
""",
    unsafe_allow_html=True,
)

st.markdown(
    """
<div class="custom-header">
    <div>
        <h1>🤖 Data-Agent Tiptop 數據湖儀表板</h1>
        <p class="subtitle">自然語言查詢與數據分析平台</p>
    </div>
    <span class="version">v1.2</span>
</div>
""",
    unsafe_allow_html=True,
)


@st.cache_resource
def get_schema_info() -> dict:
    with open(SCHEMA_REGISTRY_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@st.cache_resource
def get_client() -> DataLakeClient:
    return DataLakeClient()


def initialize_session_state() -> None:
    if "current_page" not in st.session_state:
        st.session_state.current_page = "home"
    if "data_loaded" not in st.session_state:
        st.session_state.data_loaded = False


def load_data(client: DataLakeClient):
    if not st.session_state.data_loaded:
        with st.spinner("正在從 DataLake 讀取數據..."):
            inv_df = client.get_inventory_status()
            tlf_df = client.query_table("tlf_file_large", is_large=True)
            items = client.query_table("ima_file")

            tlf_df = pd.merge(
                tlf_df,
                items[["ima01", "ima02", "ima021", "ima25"]],
                left_on="tlf01",
                right_on="ima01",
                how="left",
            )

            type_map = {
                "101": "採購進貨",
                "102": "完工入庫",
                "201": "生產領料",
                "202": "銷售出庫",
                "301": "庫存報廢",
            }
            tlf_df["交易名稱"] = tlf_df["tlf19"].map(type_map).fillna("其他")

            purchase_data = client.get_purchase_data()
            order_data = client.get_order_data()

            st.session_state.inv_df = inv_df
            st.session_state.tlf_df = tlf_df
            st.session_state.items = items
            st.session_state.pmm_df = purchase_data["pmm_file"]
            st.session_state.pmn_df = purchase_data["pmn_file"]
            st.session_state.rvb_df = purchase_data["rvb_file"]
            st.session_state.vendors = purchase_data["pmc_file"]
            st.session_state.coptc_df = order_data["coptc_file"]
            st.session_state.coptd_df = order_data["coptd_file"]
            st.session_state.prc_df = order_data["prc_file"]
            st.session_state.customers = order_data["cmc_file"]
            st.session_state.data_loaded = True


def main():
    initialize_session_state()

    schema_info = get_schema_info()
    client = get_client()

    try:
        from data_agent.intent_analyzer import IntentAnalyzer

        intent_analyzer = IntentAnalyzer()
        INTENT_ANALYZER_AVAILABLE = True
    except ImportError as e:
        intent_analyzer = None
        INTENT_ANALYZER_AVAILABLE = False
        print(f"⚠️ IntentAnalyzer 不可用: {e}")

    load_data(client)

    current_page = render_sidebar()

    st.markdown("## 🤖 Data-Agent Tiptop 數據湖儀表板")
    st.caption("展現自然語言查詢與數據分析能力")

    if current_page == "home":
        render_home(
            inv_df=st.session_state.inv_df,
            tlf_df=st.session_state.tlf_df,
            items=st.session_state.items,
        )
    elif current_page == "inventory":
        render_inventory(
            inv_df=st.session_state.inv_df,
            items=st.session_state.items,
        )
    elif current_page == "transaction":
        render_transaction(
            tlf_df=st.session_state.tlf_df,
        )
    elif current_page == "purchase":
        render_purchase(
            pmm_df=st.session_state.pmm_df,
            pmn_df=st.session_state.pmn_df,
            rvb_df=st.session_state.rvb_df,
            vendors=st.session_state.vendors,
        )
    elif current_page == "order":
        render_order(
            coptc_df=st.session_state.coptc_df,
            coptd_df=st.session_state.coptd_df,
            prc_df=st.session_state.prc_df,
            customers=st.session_state.customers,
        )
    elif current_page == "query":
        render_query(
            items=st.session_state.items,
            inv_df=st.session_state.inv_df,
            tlf_df=st.session_state.tlf_df,
        )
    elif current_page == "nlp":
        render_nlp(
            schema_info=schema_info,
            intent_analyzer=intent_analyzer,
            INTENT_ANALYZER_AVAILABLE=INTENT_ANALYZER_AVAILABLE,
        )


if __name__ == "__main__":
    main()
