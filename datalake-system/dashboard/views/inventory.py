# 代碼功能說明: 庫存分析頁面
# 創建日期: 2026-01-31
# 創建人: Daniel Chung
# 最後修改日期: 2026-02-01

"""庫存分析頁面組件"""

import streamlit as st
import pandas as pd
import plotly.express as px


def render_inventory(
    inv_df: pd.DataFrame,
    items: pd.DataFrame,
) -> None:
    """渲染庫存分析頁面"""
    st.markdown("### 📦 庫存分析")
    st.caption("分析庫存分佈、週轉狀況與異常警示")

    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.markdown("**各倉庫庫存分佈**")
        if "img02" in inv_df.columns and "img10" in inv_df.columns:
            wh_counts = inv_df.groupby("img02")["img10"].sum().reset_index()
            fig_pie = px.pie(
                wh_counts,
                values="img10",
                names="img02",
                hole=0.4,
                color_discrete_sequence=px.colors.qualitative.Set3,
            )
            fig_pie.update_layout(margin=dict(l=10, r=10, t=20, b=10), height=220)
            st.plotly_chart(fig_pie, use_container_width=True, key="inv_wh_pie")
        else:
            st.caption("無倉庫或庫存數據")

    with chart_col2:
        st.markdown("**庫存排行 Top 5**")
        if "img02" in inv_df.columns and "img10" in inv_df.columns:
            top_warehouses = (
                inv_df.groupby("img02")["img10"]
                .sum()
                .sort_values(ascending=False)
                .head(5)
                .index.tolist()
            )
            filtered_df = inv_df[inv_df["img02"].isin(top_warehouses)]
            trend_data = filtered_df.groupby("img02")["img10"].sum().reset_index()

            fig_bar = px.bar(
                trend_data,
                x="img02",
                y="img10",
                labels={"img02": "倉庫", "img10": "庫存量"},
                color="img10",
                color_continuous_scale="Blues",
            )
            fig_bar.update_layout(margin=dict(l=10, r=10, t=20, b=20), height=220)
            st.plotly_chart(fig_bar, use_container_width=True, key="inv_trend_bar")
        else:
            st.caption("無庫存數據")

    st.markdown("**📋 庫存明細**")

    col_filter1, col_filter2 = st.columns(2)
    with col_filter1:
        warehouse_options = ["全部"] + (
            sorted(inv_df["img02"].unique().tolist()) if "img02" in inv_df.columns else []
        )
        selected_warehouse = st.selectbox("倉庫", warehouse_options, key="inv_wh")
    with col_filter2:
        status_options = ["全部", "正常", "低於安全庫存", "過高", "負庫存"]
        selected_status = st.selectbox("狀態", status_options, key="inv_status")

    display_df = inv_df.copy()

    if "ima02" not in display_df.columns and "ima01" in items.columns and "ima02" in items.columns:
        display_df = pd.merge(
            display_df,
            items[["ima01", "ima02"]],
            left_on="img01",
            right_on="ima01",
            how="left",
        )

    if selected_warehouse != "全部" and "img02" in display_df.columns:
        display_df = display_df[display_df["img02"] == selected_warehouse]

    if selected_status != "全部" and "img10" in display_df.columns:
        if selected_status == "正常":
            display_df = display_df[(display_df["img10"] > 0) & (display_df["img10"] <= 10000)]
        elif selected_status == "低於安全庫存":
            display_df = display_df[(display_df["img10"] > 0) & (display_df["img10"] < 100)]
        elif selected_status == "過高":
            display_df = display_df[display_df["img10"] > 10000]
        elif selected_status == "負庫存":
            display_df = display_df[display_df["img10"] < 0]

    page_size = 10
    if "page_inv" not in st.session_state:
        st.session_state.page_inv = 1

    total_rows = len(display_df)
    total_pages = (total_rows + page_size - 1) // page_size if total_rows > 0 else 1

    col_nav1, col_nav2, col_nav3 = st.columns([1, 2, 1])
    with col_nav1:
        if st.button("◀", disabled=st.session_state.page_inv <= 1, key="inv_prev"):
            st.session_state.page_inv -= 1
            st.rerun()
    with col_nav2:
        st.caption(f"第 {st.session_state.page_inv}/{total_pages} 頁，共 {total_rows} 筆")
    with col_nav3:
        if st.button("▶", disabled=st.session_state.page_inv >= total_pages, key="inv_next"):
            st.session_state.page_inv += 1
            st.rerun()

    start_idx = (st.session_state.page_inv - 1) * page_size
    end_idx = min(start_idx + page_size, total_rows)
    page_df = display_df.iloc[start_idx:end_idx] if total_rows > 0 else pd.DataFrame()

    rename_cols = {
        "img01": "料號",
        "ima02": "品名",
        "img02": "倉庫",
        "img10": "庫存量",
    }

    display_cols = [c for c in rename_cols.keys() if c in page_df.columns]

    if display_cols:
        result_df = page_df[display_cols].rename(columns=rename_cols)

        def status_color(val, col_name):
            if col_name == "庫存量" and isinstance(val, (int, float)):
                if val < 0:
                    return "color: red; font-weight: bold"
                elif val < 100:
                    return "color: orange"
                elif val > 10000:
                    return "color: blue"
            return ""

        st.dataframe(
            result_df.style.applymap(lambda x: status_color(x, "庫存量"), subset=["庫存量"]),
            use_container_width=True,
            height=200,
        )
    else:
        st.caption("無可顯示的庫存數據")
