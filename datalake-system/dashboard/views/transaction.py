# 代碼功能說明: 交易類別頁面
# 創建日期: 2026-01-31
# 創建人: Daniel Chung
# 最後修改日期: 2026-02-01

"""交易類別頁面組件"""

import streamlit as st
import pandas as pd
import plotly.express as px


def render_transaction(
    tlf_df: pd.DataFrame,
) -> None:
    """渲染交易類別頁面"""
    st.markdown("# 🔄 交易類別")
    st.markdown("*分析交易趨勢與類別分佈*")
    st.markdown("---")

    type_map = {
        "101": "採購進貨",
        "102": "完工入庫",
        "201": "生產領料",
        "202": "銷售出庫",
        "301": "庫存報廢",
    }

    if "交易名稱" not in tlf_df.columns and "tlf19" in tlf_df.columns:
        tlf_df["交易名稱"] = tlf_df["tlf19"].map(type_map).fillna("其他")

    st.markdown("### 📊 上方圖表區")
    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.subheader("業務類型佔比")
        if "交易名稱" in tlf_df.columns:
            type_counts = tlf_df["交易名稱"].value_counts().reset_index()
            type_counts.columns = ["交易類別", "筆數"]
            fig_pie = px.pie(
                type_counts,
                values="筆數",
                names="交易類別",
                hole=0.3,
                color_discrete_sequence=px.colors.qualitative.Pastel,
            )
            st.plotly_chart(fig_pie, use_container_width=True, key="tx_type_pie")

            with st.expander("📊 交易類別明細"):
                st.dataframe(type_counts, use_container_width=True)
        else:
            st.info("無交易類別數據")

    with chart_col2:
        st.subheader("月交易趨勢")
        if "tlf06" in tlf_df.columns:
            tlf_copy = tlf_df.copy()
            tlf_copy["date"] = pd.to_datetime(tlf_copy["tlf06"], errors="coerce")
            tlf_copy["month"] = tlf_copy["date"].dt.to_period("M")

            monthly_type = (
                tlf_copy.groupby(["month", "交易名稱"]).size().reset_index(name="count")
                if "交易名稱" in tlf_copy.columns
                else tlf_copy.groupby("month").size().reset_index(name="count")
            )
            monthly_type["month"] = monthly_type["month"].astype(str)

            if "交易名稱" in monthly_type.columns:
                fig_bar = px.bar(
                    monthly_type,
                    x="month",
                    y="count",
                    color="交易名稱",
                    labels={"month": "月份", "count": "交易筆數", "交易名稱": "類別"},
                    barmode="group",
                )
            else:
                fig_bar = px.bar(
                    monthly_type,
                    x="month",
                    y="count",
                    labels={"month": "月份", "count": "交易筆數"},
                )
            st.plotly_chart(fig_bar, use_container_width=True, key="tx_monthly_bar")
        else:
            st.info("無交易日期數據")

    st.markdown("---")
    st.markdown("### 📋 下方表格區")
    st.subheader("交易明細")

    col_filter1, col_filter2, col_filter3 = st.columns(3)
    with col_filter1:
        type_options = ["全部"] + (
            sorted(tlf_df["交易名稱"].unique().tolist()) if "交易名稱" in tlf_df.columns else []
        )
        selected_type = st.selectbox("選擇交易類別", type_options, key="tx_type")
    with col_filter2:
        sort_options = ["日期降序", "日期升序", "數量降序", "數量升序"]
        selected_sort = st.selectbox("排序方式", sort_options, key="tx_sort")
    with col_filter3:
        page_size = st.selectbox("每頁筆數", [10, 25, 50, 100], index=1, key="tx_page")

    col_date1, col_date2 = st.columns(2)
    with col_date1:
        if "tlf06" in tlf_df.columns:
            min_date = pd.to_datetime(tlf_df["tlf06"], errors="coerce").min()
            max_date = pd.to_datetime(tlf_df["tlf06"], errors="coerce").max()
            if pd.notna(min_date) and pd.notna(max_date):
                date_range = st.date_input(
                    "選擇日期範圍",
                    value=(min_date.date(), max_date.date()),
                    key="tx_date_range",
                )
            else:
                date_range = None
                st.info("無有效日期資料")
        else:
            date_range = None
            st.info("無日期欄位")

    display_df = tlf_df.copy()

    if selected_type != "全部" and "交易名稱" in display_df.columns:
        display_df = display_df[display_df["交易名稱"] == selected_type]

    if date_range and len(date_range) == 2:
        start_date, end_date = date_range
        if "tlf06" in display_df.columns:
            display_df["date_temp"] = pd.to_datetime(display_df["tlf06"], errors="coerce")
            display_df = display_df[
                (display_df["date_temp"].dt.date >= start_date)
                & (display_df["date_temp"].dt.date <= end_date)
            ]
            display_df = display_df.drop(columns=["date_temp"])

    sort_col = "tlf06" if "tlf06" in display_df.columns else None
    sort_by_qty = "tlf10" if "tlf10" in display_df.columns else None

    if sort_col:
        ascending = selected_sort in ["日期升序", "數量升序"]
        if "數量" in selected_sort and sort_by_qty:
            display_df = display_df.sort_values(sort_by_qty, ascending=ascending)
        elif "日期" in selected_sort:
            display_df = display_df.sort_values(sort_col, ascending=ascending)

    if "page_tx" not in st.session_state:
        st.session_state.page_tx = 1

    total_rows = len(display_df)
    total_pages = (total_rows + page_size - 1) // page_size if total_rows > 0 else 1

    col_nav1, col_nav2, col_nav3 = st.columns([1, 2, 1])
    with col_nav1:
        if st.button("◀ 上一頁", disabled=st.session_state.page_tx <= 1, key="tx_prev"):
            st.session_state.page_tx -= 1
            st.rerun()
    with col_nav2:
        st.caption(f"第 {st.session_state.page_tx} / {total_pages} 頁，共 {total_rows} 筆")
    with col_nav3:
        if st.button("下一頁 ▶", disabled=st.session_state.page_tx >= total_pages, key="tx_next"):
            st.session_state.page_tx += 1
            st.rerun()

    start_idx = (st.session_state.page_tx - 1) * page_size
    end_idx = min(start_idx + page_size, total_rows)
    page_df = display_df.iloc[start_idx:end_idx] if total_rows > 0 else pd.DataFrame()

    rename_cols = {
        "tlf01": "料號",
        "ima02": "品名",
        "交易名稱": "交易類別",
        "tlf06": "日期",
        "tlf10": "數量",
        "ima25": "單位",
        "tlf061": "倉庫",
    }

    display_cols = [c for c in rename_cols.keys() if c in page_df.columns]

    if display_cols:
        result_df = page_df[display_cols].rename(columns=rename_cols)

        def color_quantity(val):
            if isinstance(val, (int, float)) and val < 0:
                return "color: red; font-weight: bold"
            return ""

        st.dataframe(
            result_df.style.applymap(color_quantity, subset=["數量"]),
            use_container_width=True,
            height=350,
        )
    else:
        st.info("無可顯示的交易數據")

    with st.expander("🔍 進階搜尋"):
        col_search1, col_search2, col_search3 = st.columns(3)
        with col_search1:
            search_item = st.text_input("料號搜尋", placeholder="輸入料號...", key="tx_item_search")
        with col_search2:
            search_warehouse = st.text_input(
                "倉庫搜尋", placeholder="輸入倉庫...", key="tx_wh_search"
            )
        with col_search3:
            search_source = st.text_input(
                "來源單號搜尋", placeholder="輸入單號...", key="tx_source_search"
            )

        if search_item and "tlf01" in display_df.columns:
            display_df = display_df[
                display_df["tlf01"].astype(str).str.contains(search_item, na=False)
            ]
        if search_warehouse and "tlf061" in display_df.columns:
            display_df = display_df[
                display_df["tlf061"].astype(str).str.contains(search_warehouse, na=False)
            ]
        if search_source and "tlf13" in display_df.columns:
            display_df = display_df[
                display_df["tlf13"].astype(str).str.contains(search_source, na=False)
            ]

        st.caption(f"搜尋結果共 {len(display_df)} 筆記錄")
