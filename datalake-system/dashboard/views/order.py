# 代碼功能說明: 訂單分析頁面
# 創建日期: 2026-02-01
# 創建人: Daniel Chung
# 最後修改日期: 2026-02-01

"""訂單分析頁面組件"""

import streamlit as st
import pandas as pd
import plotly.express as px


def render_order(
    coptc_df: pd.DataFrame,
    coptd_df: pd.DataFrame,
    prc_df: pd.DataFrame,
    customers: pd.DataFrame,
) -> None:
    """渲染訂單分析頁面"""
    st.markdown("### 📤 訂單分析")
    st.caption("分析客戶訂單、訂單明細與報價情況")

    if coptc_df.empty and coptd_df.empty:
        st.info("暫無訂單數據，請先生成模擬數據")
        return

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**訂單趨勢**")
        if "coptc03" in coptc_df.columns:
            coptc_copy = coptc_df.copy()
            coptc_copy["date"] = pd.to_datetime(coptc_copy["coptc03"], errors="coerce")
            coptc_copy["month"] = coptc_copy["date"].dt.to_period("M")
            monthly_orders = coptc_copy.groupby("month").size().reset_index(name="count")
            monthly_orders["month"] = monthly_orders["month"].astype(str)

            fig_bar = px.bar(
                monthly_orders,
                x="month",
                y="count",
                labels={"month": "月份", "count": "訂單數"},
                color="count",
                color_continuous_scale="Greens",
            )
            fig_bar.update_layout(margin=dict(l=10, r=10, t=20, b=20), height=220)
            st.plotly_chart(fig_bar, use_container_width=True, key="order_monthly_bar")
        else:
            st.caption("無訂單日期數據")

    with col2:
        st.markdown("**訂單狀態分佈**")
        if "coptc05" in coptc_df.columns:
            status_map = {"10": "未出貨", "20": "部分出貨", "30": "已出貨"}
            status_counts = coptc_df["coptc05"].value_counts().reset_index()
            status_counts.columns = ["狀態", "數量"]
            status_counts["狀態名稱"] = (
                status_counts["狀態"].map(status_map).fillna(status_counts["狀態"])
            )

            fig_pie = px.pie(
                status_counts,
                values="數量",
                names="狀態名稱",
                hole=0.4,
                color_discrete_sequence=px.colors.qualitative.Pastel1,
            )
            fig_pie.update_layout(margin=dict(l=10, r=10, t=20, b=10), height=220)
            st.plotly_chart(fig_pie, use_container_width=True, key="order_status_pie")
        else:
            st.caption("無訂單狀態數據")

    st.markdown("---")

    st.markdown("### 📋 訂單查詢")

    tab1, tab2, tab3 = st.tabs(["📋 訂單單頭", "📦 訂單單身", "💰 訂價單"])

    with tab1:
        st.markdown("**客戶訂單單頭檔 (coptc_file)**")
        if not coptc_df.empty:
            col_filter1, col_filter2, col_filter3 = st.columns(3)
            with col_filter1:
                if "coptc02" in coptc_df.columns:
                    customer_options = ["全部"] + sorted(coptc_df["coptc02"].unique().tolist())
                    selected_customer = st.selectbox("客戶", customer_options, key="coptc_customer")
                else:
                    selected_customer = "全部"
            with col_filter2:
                if "coptc05" in coptc_df.columns:
                    status_options = ["全部", "10", "20", "30"]
                    status_labels = {"10": "未出貨", "20": "部分出貨", "30": "已出貨"}
                    selected_status = st.selectbox(
                        "訂單狀態",
                        status_options,
                        format_func=lambda x: status_labels.get(x, x),
                        key="coptc_status",
                    )
                else:
                    selected_status = "全部"
            with col_filter3:
                page_size = st.selectbox("每頁筆數", [10, 25, 50], index=0, key="coptc_page")

            display_df = coptc_df.copy()
            if selected_customer != "全部" and "coptc02" in display_df.columns:
                display_df = display_df[display_df["coptc02"] == selected_customer]
            if selected_status != "全部" and "coptc05" in display_df.columns:
                display_df = display_df[display_df["coptc05"] == selected_status]

            total_rows = len(display_df)
            total_pages = (total_rows + page_size - 1) // page_size if total_rows > 0 else 1

            if "page_coptc" not in st.session_state:
                st.session_state.page_coptc = 1

            col_nav1, col_nav2, col_nav3 = st.columns([1, 2, 1])
            with col_nav1:
                if st.button("◀", disabled=st.session_state.page_coptc <= 1, key="coptc_prev"):
                    st.session_state.page_coptc -= 1
                    st.rerun()
            with col_nav2:
                st.caption(f"第 {st.session_state.page_coptc}/{total_pages} 頁，共 {total_rows} 筆")
            with col_nav3:
                if st.button(
                    "▶", disabled=st.session_state.page_coptc >= total_pages, key="coptc_next"
                ):
                    st.session_state.page_coptc += 1
                    st.rerun()

            start_idx = (st.session_state.page_coptc - 1) * page_size
            end_idx = min(start_idx + page_size, total_rows)
            page_df = display_df.iloc[start_idx:end_idx] if total_rows > 0 else pd.DataFrame()

            status_map = {"10": "未出貨", "20": "部分出貨", "30": "已出貨"}
            rename_cols = {
                "coptc01": "訂單號",
                "coptc02": "客戶代碼",
                "coptc03": "單據日期",
                "coptc04": "預計出貨日",
                "coptc05": "訂單狀態",
                "coptc06": "業務人員",
            }

            display_cols = [c for c in rename_cols.keys() if c in page_df.columns]
            if display_cols:
                result_df = page_df[display_cols].rename(columns=rename_cols)
                if "訂單狀態" in result_df.columns:
                    result_df["訂單狀態"] = (
                        result_df["訂單狀態"].map(status_map).fillna(result_df["訂單狀態"])
                    )
                st.dataframe(result_df, use_container_width=True, height=200)
        else:
            st.caption("無訂單單頭數據")

    with tab2:
        st.markdown("**客戶訂單單身檔 (coptd_file)**")
        if not coptd_df.empty:
            col_filter1, col_filter2, col_filter3 = st.columns(3)
            with col_filter1:
                if "coptd01" in coptd_df.columns:
                    order_options = ["全部"] + sorted(coptd_df["coptd01"].unique().tolist())[:50]
                    selected_order = st.selectbox("訂單號", order_options, key="coptd_order")
                else:
                    selected_order = "全部"
            with col_filter2:
                page_size = st.selectbox("每頁筆數", [10, 25, 50], index=1, key="coptd_page")
            with col_filter3:
                show_details = st.checkbox("展開所有單身明細", key="coptd_expand")

            display_df = coptd_df.copy()
            if selected_order != "全部" and "coptd01" in display_df.columns:
                display_df = display_df[display_df["coptd01"] == selected_order]

            total_rows = len(display_df)
            total_pages = (total_rows + page_size - 1) // page_size if total_rows > 0 else 1

            if "page_coptd" not in st.session_state:
                st.session_state.page_coptd = 1

            col_nav1, col_nav2, col_nav3 = st.columns([1, 2, 1])
            with col_nav1:
                if st.button("◀", disabled=st.session_state.page_coptd <= 1, key="coptd_prev"):
                    st.session_state.page_coptd -= 1
                    st.rerun()
            with col_nav2:
                st.caption(f"第 {st.session_state.page_coptd}/{total_pages} 頁，共 {total_rows} 筆")
            with col_nav3:
                if st.button(
                    "▶", disabled=st.session_state.page_coptd >= total_pages, key="coptd_next"
                ):
                    st.session_state.page_coptd += 1
                    st.rerun()

            start_idx = (st.session_state.page_coptd - 1) * page_size
            end_idx = min(start_idx + page_size, total_rows)
            page_df = display_df.iloc[start_idx:end_idx] if total_rows > 0 else pd.DataFrame()

            rename_cols = {
                "coptd01": "訂單號",
                "coptd02": "項次",
                "coptd04": "料號",
                "coptd20": "訂購數量",
                "coptd30": "單價",
                "coptd31": "已出貨數量",
                "coptd32": "訂單批次",
            }

            display_cols = [c for c in rename_cols.keys() if c in page_df.columns]
            if display_cols:
                result_df = page_df[display_cols].rename(columns=rename_cols)
                st.dataframe(result_df, use_container_width=True, height=200)

                if show_details and not page_df.empty:
                    with st.expander("📦 展開單身明細"):
                        for idx, row in page_df.iterrows():
                            order_no = row.get("coptd01", "")
                            line_no = row.get("coptd02", "")
                            item_id = row.get("coptd04", "")
                            qty = row.get("coptd20", 0)
                            price = row.get("coptd30", 0)
                            shipped = row.get("coptd31", 0)

                            st.markdown(f"**{order_no} - 項次 {line_no}**")
                            col_d1, col_d2, col_d3, col_d4 = st.columns(4)
                            with col_d1:
                                st.info(f"料號: {item_id}")
                            with col_d2:
                                st.info(f"訂購數量: {qty}")
                            with col_d3:
                                st.info(f"單價: {price}")
                            with col_d4:
                                st.info(f"已出貨: {shipped}")
                            st.divider()
        else:
            st.caption("無訂單單身數據")

    with tab3:
        st.markdown("**訂價單檔 (prc_file)**")
        if not prc_df.empty:
            col_filter1, col_filter2 = st.columns(2)
            with col_filter1:
                if "prc01" in prc_df.columns:
                    item_options = ["全部"] + sorted(prc_df["prc01"].unique().tolist())[:50]
                    selected_item = st.selectbox("料號", item_options, key="prc_item")
                else:
                    selected_item = "全部"
            with col_filter2:
                page_size = st.selectbox("每頁筆數", [10, 25, 50], index=0, key="prc_page")

            display_df = prc_df.copy()
            if selected_item != "全部" and "prc01" in display_df.columns:
                display_df = display_df[display_df["prc01"] == selected_item]

            total_rows = len(display_df)
            total_pages = (total_rows + page_size - 1) // page_size if total_rows > 0 else 1

            if "page_prc" not in st.session_state:
                st.session_state.page_prc = 1

            col_nav1, col_nav2, col_nav3 = st.columns([1, 2, 1])
            with col_nav1:
                if st.button("◀", disabled=st.session_state.page_prc <= 1, key="prc_prev"):
                    st.session_state.page_prc -= 1
                    st.rerun()
            with col_nav2:
                st.caption(f"第 {st.session_state.page_prc}/{total_pages} 頁，共 {total_rows} 筆")
            with col_nav3:
                if st.button(
                    "▶", disabled=st.session_state.page_prc >= total_pages, key="prc_next"
                ):
                    st.session_state.page_prc += 1
                    st.rerun()

            start_idx = (st.session_state.page_prc - 1) * page_size
            end_idx = min(start_idx + page_size, total_rows)
            page_df = display_df.iloc[start_idx:end_idx] if total_rows > 0 else pd.DataFrame()

            rename_cols = {
                "prc01": "料號",
                "prc02": "單價",
                "prc03": "批准日期",
                "prc04": "批准狀態",
                "prc05": "生效日",
                "prc06": "失效日",
            }

            display_cols = [c for c in rename_cols.keys() if c in page_df.columns]
            if display_cols:
                result_df = page_df[display_cols].rename(columns=rename_cols)
                if "批准狀態" in result_df.columns:
                    status_map = {"Y": "已批准", "N": "待批准"}
                    result_df["批准狀態"] = (
                        result_df["批准狀態"].map(status_map).fillna(result_df["批准狀態"])
                    )
                st.dataframe(result_df, use_container_width=True, height=200)
        else:
            st.caption("無訂價單數據")
