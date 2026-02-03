# 代碼功能說明: Home 首頁
# 創建日期: 2026-01-31
# 創建人: Daniel Chung
# 最後修改日期: 2026-02-01

"""Home 首頁組件"""

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta


def render_home(
    inv_df: pd.DataFrame,
    tlf_df: pd.DataFrame,
    items: pd.DataFrame,
) -> None:
    """渲染 Home 首頁"""
    st.markdown("### 📊 數據湖總覽")
    st.caption("快速掌握系統狀態與關鍵指標")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("總品項數", f"{len(items):,}", help="料號主檔中的物料種類數")
    with col2:
        st.metric("總交易筆數", f"{len(tlf_df):,}", help="庫存交易檔中的所有交易記錄")
    with col3:
        unique_warehouses = inv_df["img02"].nunique() if "img02" in inv_df.columns else 0
        st.metric("總倉庫數", f"{unique_warehouses}", help="有多少個不同倉庫")
    with col4:
        abnormal_count = len(inv_df[inv_df["img10"] < 0]) if "img10" in inv_df.columns else 0
        st.metric(
            "庫存異常數",
            f"{abnormal_count}",
            delta_color="inverse",
            help="負庫存或異常狀態的品項數",
        )

    st.markdown("**📈 最近 30 天交易趨勢**")

    if "tlf06" in tlf_df.columns:
        tlf_df_copy = tlf_df.copy()
        tlf_df_copy["date"] = pd.to_datetime(tlf_df_copy["tlf06"], errors="coerce")
        thirty_days_ago = datetime.now() - timedelta(days=30)
        recent_df = tlf_df_copy[tlf_df_copy["date"] >= thirty_days_ago]

        if not recent_df.empty:
            trend_data = (
                recent_df.groupby(recent_df["date"].dt.date).size().reset_index(name="count")
            )
            trend_data.columns = ["date", "count"]
            trend_data = trend_data.sort_values("date")

            fig_line = px.area(
                trend_data,
                x="date",
                y="count",
                labels={"date": "日期", "count": "交易筆數"},
                color_discrete_sequence=["#4CAF50"],
            )
            fig_line.update_layout(
                margin=dict(l=20, r=20, t=30, b=20),
                height=250,
                xaxis_title="",
                yaxis_title="",
            )
            st.plotly_chart(fig_line, use_container_width=True, key="home_trend_chart")
        else:
            st.caption("近期無交易數據")
    else:
        st.caption("無交易日期欄位")

    st.markdown("**📋 各表記錄統計**")

    table_stats = [
        {
            "資料表": "料號主檔 (ima_file)",
            "記錄筆數": f"{len(items):,}",
            "更新時間": "今日",
            "狀態": "✓ 正常",
        },
        {
            "資料表": "庫存主檔 (img_file)",
            "記錄筆數": f"{len(inv_df):,}",
            "更新時間": "今日",
            "狀態": "✓ 正常",
        },
        {
            "資料表": "庫存交易檔 (tlf_file)",
            "記錄筆數": f"{len(tlf_df):,}",
            "更新時間": "今日",
            "狀態": "✓ 正常",
        },
    ]

    stats_df = pd.DataFrame(table_stats)
    st.dataframe(
        stats_df,
        use_container_width=True,
        hide_index=True,
        height=80,
        column_config={
            "狀態": st.column_config.TextColumn("狀態", width="small"),
            "記錄筆數": st.column_config.TextColumn("記錄筆數", width="medium"),
        },
    )

    with st.expander("📊 各表數據預覽", expanded=False):
        tab_tables = st.tabs(["料號主檔", "庫存主檔", "交易記錄"])

        with tab_tables[0]:
            st.dataframe(items.head(5), use_container_width=True, height=150)
            st.caption(f"料號主檔共 {len(items)} 筆")

        with tab_tables[1]:
            st.dataframe(inv_df.head(5), use_container_width=True, height=150)
            st.caption(f"庫存主檔共 {len(inv_df)} 筆")

        with tab_tables[2]:
            st.dataframe(tlf_df.head(5), use_container_width=True, height=150)
            st.caption(f"交易記錄共 {len(tlf_df)} 筆")
