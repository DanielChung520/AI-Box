# 代碼功能說明: 採購交易分析頁面
# 創建日期: 2026-02-01
# 創建人: Daniel Chung
# 最後修改日期: 2026-02-01

"""採購交易分析頁面組件"""

import streamlit as st
import pandas as pd
import plotly.express as px


def render_purchase(
    pmm_df: pd.DataFrame,
    pmn_df: pd.DataFrame,
    rvb_df: pd.DataFrame,
    vendors: pd.DataFrame,
) -> None:
    """渲染採購交易分析頁面"""
    st.markdown("### 📥 採購交易分析")
    st.caption("分析採購單據、收料情況與供應商表現")

    if pmm_df.empty and pmn_df.empty:
        st.info("暫無採購數據，請先生成模擬數據")
        return

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**採購單分佈**")
        if "pmm04" in pmm_df.columns and "pmm02" in pmm_df.columns:
            pmm_copy = pmm_df.copy()
            pmm_copy["date"] = pd.to_datetime(pmm_copy["pmm02"], errors="coerce")
            pmm_copy["month"] = pmm_copy["date"].dt.to_period("M")
            monthly_purchases = pmm_copy.groupby("month").size().reset_index(name="count")
            monthly_purchases["month"] = monthly_purchases["month"].astype(str)

            fig_bar = px.bar(
                monthly_purchases,
                x="month",
                y="count",
                labels={"month": "月份", "count": "採購單數"},
                color="count",
                color_continuous_scale="Blues",
            )
            fig_bar.update_layout(margin=dict(l=10, r=10, t=20, b=20), height=220)
            st.plotly_chart(fig_bar, use_container_width=True, key="purchase_monthly_bar")
        else:
            st.caption("無採購日期數據")

    with col2:
        st.markdown("**供應商分佈**")
        if "pmm04" in pmm_df.columns:
            vendor_counts = pmm_df["pmm04"].value_counts().reset_index()
            vendor_counts.columns = ["供應商", "訂單數"]
            if not vendors.empty and "pmc01" in vendors.columns and "pmc03" in vendors.columns:
                vendor_map = dict(zip(vendors["pmc01"], vendors["pmc03"]))
                vendor_counts["供應商名稱"] = (
                    vendor_counts["供應商"].map(vendor_map).fillna(vendor_counts["供應商"])
                )
                vendor_display = vendor_counts.head(10)
                fig_pie = px.pie(
                    vendor_display,
                    values="訂單數",
                    names="供應商名稱",
                    hole=0.4,
                    color_discrete_sequence=px.colors.qualitative.Set3,
                )
                fig_pie.update_layout(margin=dict(l=10, r=10, t=20, b=10), height=220)
                st.plotly_chart(fig_pie, use_container_width=True, key="purchase_vendor_pie")
            else:
                st.caption("無供應商主檔數據")
        else:
            st.caption("無供應商數據")

    st.markdown("---")

    st.markdown("### 📋 採購單據查詢")

    tab1, tab2, tab3 = st.tabs(["📋 採購單頭", "📦 採購單身", "📨 收料記錄"])

    with tab1:
        st.markdown("**採購單頭檔 (pmm_file)**")
        if not pmm_df.empty:
            col_filter1, col_filter2 = st.columns(2)
            with col_filter1:
                if "pmm04" in pmm_df.columns:
                    vendor_options = ["全部"] + sorted(pmm_df["pmm04"].unique().tolist())
                    selected_vendor = st.selectbox("供應商", vendor_options, key="pmm_vendor")
                else:
                    selected_vendor = "全部"
            with col_filter2:
                page_size = st.selectbox("每頁筆數", [10, 25, 50], index=0, key="pmm_page")

            display_df = pmm_df.copy()
            if selected_vendor != "全部" and "pmm04" in display_df.columns:
                display_df = display_df[display_df["pmm04"] == selected_vendor]

            total_rows = len(display_df)
            total_pages = (total_rows + page_size - 1) // page_size if total_rows > 0 else 1

            if "page_pmm" not in st.session_state:
                st.session_state.page_pmm = 1

            col_nav1, col_nav2, col_nav3 = st.columns([1, 2, 1])
            with col_nav1:
                if st.button("◀", disabled=st.session_state.page_pmm <= 1, key="pmm_prev"):
                    st.session_state.page_pmm -= 1
                    st.rerun()
            with col_nav2:
                st.caption(f"第 {st.session_state.page_pmm}/{total_pages} 頁，共 {total_rows} 筆")
            with col_nav3:
                if st.button(
                    "▶", disabled=st.session_state.page_pmm >= total_pages, key="pmm_next"
                ):
                    st.session_state.page_pmm += 1
                    st.rerun()

            start_idx = (st.session_state.page_pmm - 1) * page_size
            end_idx = min(start_idx + page_size, total_rows)
            page_df = display_df.iloc[start_idx:end_idx] if total_rows > 0 else pd.DataFrame()

            rename_cols = {
                "pmm01": "採購單號",
                "pmm02": "單據日期",
                "pmm04": "供應商",
                "pmm09": "採購人員",
            }

            display_cols = [c for c in rename_cols.keys() if c in page_df.columns]
            if display_cols:
                result_df = page_df[display_cols].rename(columns=rename_cols)
                st.dataframe(result_df, use_container_width=True, height=200)
        else:
            st.caption("無採購單頭數據")

    with tab2:
        st.markdown("**採購單身檔 (pmn_file)**")
        if not pmn_df.empty:
            col_filter1, col_filter2, col_filter3 = st.columns(3)
            with col_filter1:
                if "pmn01" in pmn_df.columns:
                    po_options = ["全部"] + sorted(pmn_df["pmn01"].unique().tolist())[:50]
                    selected_po = st.selectbox("採購單號", po_options, key="pmn_po")
                else:
                    selected_po = "全部"
            with col_filter2:
                page_size = st.selectbox("每頁筆數", [10, 25, 50], index=1, key="pmn_page")
            with col_filter3:
                show_details = st.checkbox("展開所有單身明細", key="pmn_expand")

            display_df = pmn_df.copy()
            if selected_po != "全部" and "pmn01" in display_df.columns:
                display_df = display_df[display_df["pmn01"] == selected_po]

            total_rows = len(display_df)
            total_pages = (total_rows + page_size - 1) // page_size if total_rows > 0 else 1

            if "page_pmn" not in st.session_state:
                st.session_state.page_pmn = 1

            col_nav1, col_nav2, col_nav3 = st.columns([1, 2, 1])
            with col_nav1:
                if st.button("◀", disabled=st.session_state.page_pmn <= 1, key="pmn_prev"):
                    st.session_state.page_pmn -= 1
                    st.rerun()
            with col_nav2:
                st.caption(f"第 {st.session_state.page_pmn}/{total_pages} 頁，共 {total_rows} 筆")
            with col_nav3:
                if st.button(
                    "▶", disabled=st.session_state.page_pmn >= total_pages, key="pmn_next"
                ):
                    st.session_state.page_pmn += 1
                    st.rerun()

            start_idx = (st.session_state.page_pmn - 1) * page_size
            end_idx = min(start_idx + page_size, total_rows)
            page_df = display_df.iloc[start_idx:end_idx] if total_rows > 0 else pd.DataFrame()

            rename_cols = {
                "pmn01": "採購單號",
                "pmn02": "項次",
                "pmn04": "料號",
                "pmn20": "採購數量",
                "pmn31": "已交數量",
                "pmn33": "預計到貨日",
            }

            display_cols = [c for c in rename_cols.keys() if c in page_df.columns]
            if display_cols:
                result_df = page_df[display_cols].rename(columns=rename_cols)
                st.dataframe(result_df, use_container_width=True, height=200)

                if show_details and not page_df.empty:
                    with st.expander("📦 展開單身明細"):
                        for idx, row in page_df.iterrows():
                            st.markdown(f"**{row.get('pmn01', '')} - 項次 {row.get('pmn02', '')}**")
                            col_d1, col_d2, col_d3 = st.columns(3)
                            with col_d1:
                                st.info(f"料號: {row.get('pmn04', '')}")
                            with col_d2:
                                st.info(f"採購數量: {row.get('pmn20', 0)}")
                            with col_d3:
                                st.info(f"已交數量: {row.get('pmn31', 0)}")
                            st.divider()
        else:
            st.caption("無採購單身數據")

    with tab3:
        st.markdown("**收料單身檔 (rvb_file)**")
        if not rvb_df.empty:
            col_filter1, col_filter2 = st.columns(2)
            with col_filter1:
                if "rvb07" in rvb_df.columns:
                    po_options = ["全部"] + sorted(rvb_df["rvb07"].unique().tolist())[:50]
                    selected_po = st.selectbox("關聯採購單號", po_options, key="rvb_po")
                else:
                    selected_po = "全部"
            with col_filter2:
                page_size = st.selectbox("每頁筆數", [10, 25, 50], index=0, key="rvb_page")

            display_df = rvb_df.copy()
            if selected_po != "全部" and "rvb07" in display_df.columns:
                display_df = display_df[display_df["rvb07"] == selected_po]

            total_rows = len(display_df)
            total_pages = (total_rows + page_size - 1) // page_size if total_rows > 0 else 1

            if "page_rvb" not in st.session_state:
                st.session_state.page_rvb = 1

            col_nav1, col_nav2, col_nav3 = st.columns([1, 2, 1])
            with col_nav1:
                if st.button("◀", disabled=st.session_state.page_rvb <= 1, key="rvb_prev"):
                    st.session_state.page_rvb -= 1
                    st.rerun()
            with col_nav2:
                st.caption(f"第 {st.session_state.page_rvb}/{total_pages} 頁，共 {total_rows} 筆")
            with col_nav3:
                if st.button(
                    "▶", disabled=st.session_state.page_rvb >= total_pages, key="rvb_next"
                ):
                    st.session_state.page_rvb += 1
                    st.rerun()

            start_idx = (st.session_state.page_rvb - 1) * page_size
            end_idx = min(start_idx + page_size, total_rows)
            page_df = display_df.iloc[start_idx:end_idx] if total_rows > 0 else pd.DataFrame()

            rename_cols = {
                "rvb01": "收料單號",
                "rvb05": "料號",
                "rvb07": "採購單號",
                "rvb33": "驗收數量",
            }

            display_cols = [c for c in rename_cols.keys() if c in page_df.columns]
            if display_cols:
                result_df = page_df[display_cols].rename(columns=rename_cols)
                st.dataframe(result_df, use_container_width=True, height=200)
        else:
            st.caption("無收料記錄數據")
