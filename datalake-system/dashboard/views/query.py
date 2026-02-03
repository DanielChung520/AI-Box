# 代碼功能說明: 數據查詢頁面
# 創建日期: 2026-01-31
# 創建人: Daniel Chung
# 最後修改日期: 2026-02-01

"""數據查詢頁面組件"""

import streamlit as st
import pandas as pd


def render_query(
    items: pd.DataFrame,
    inv_df: pd.DataFrame,
    tlf_df: pd.DataFrame,
) -> None:
    """渲染數據查詢頁面"""
    st.markdown("### 📋 數據查詢")
    st.caption("瀏覽和檢索各資料表")

    table_options = [
        "📦 料號主檔",
        "🏪 庫存主檔",
        "📋 庫存交易檔",
        "📑 採購單據",
    ]

    selected_table = st.radio(
        "選擇資料表",
        table_options,
        horizontal=True,
    )

    if "料號主檔" in selected_table:
        _render_ima_table(items)
    elif "庫存主檔" in selected_table:
        _render_img_table(inv_df, items)
    elif "庫存交易檔" in selected_table:
        _render_tlf_table(tlf_df)
    elif "採購單據" in selected_table:
        _render_po_table(tlf_df)


def _render_pagination(
    display_df: pd.DataFrame,
    page_key: str,
    page_size: int = 10,
) -> tuple:
    """渲染分頁控制"""
    if page_key not in st.session_state:
        st.session_state[page_key] = 1

    total_rows = len(display_df)
    total_pages = (total_rows + page_size - 1) // page_size if total_rows > 0 else 1

    col_nav1, col_nav2, col_nav3 = st.columns([1, 2, 1])
    with col_nav1:
        if st.button("◀", disabled=st.session_state[page_key] <= 1, key=f"{page_key}_prev"):
            st.session_state[page_key] -= 1
            st.rerun()
    with col_nav2:
        st.caption(f"第 {st.session_state[page_key]}/{total_pages} 頁，共 {total_rows} 筆")
    with col_nav3:
        if st.button(
            "▶", disabled=st.session_state[page_key] >= total_pages, key=f"{page_key}_next"
        ):
            st.session_state[page_key] += 1
            st.rerun()

    start_idx = (st.session_state[page_key] - 1) * page_size
    end_idx = min(start_idx + page_size, total_rows)

    return start_idx, end_idx


def _render_ima_table(items: pd.DataFrame) -> None:
    """渲染料號主檔"""
    col1, col2 = st.columns([2, 1])
    with col1:
        search_value = st.text_input("搜尋", placeholder="料號/品名/規格...", key="ima_search")
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("重置", key="ima_reset"):
            st.rerun()

    display_df = items.copy()

    if search_value:
        search_value_lower = search_value.lower()
        mask = (
            display_df["ima01"].astype(str).str.contains(search_value_lower, na=False)
            | display_df["ima02"].astype(str).str.contains(search_value_lower, na=False)
            | display_df["ima021"].astype(str).str.contains(search_value_lower, na=False)
        )
        display_df = display_df[mask]

    start_idx, end_idx = _render_pagination(display_df, "page_ima")
    page_df = display_df.iloc[start_idx:end_idx] if len(display_df) > 0 else pd.DataFrame()

    result_df = page_df.rename(columns={"ima01": "料號", "ima02": "品名", "ima021": "規格"})
    st.dataframe(result_df, use_container_width=True, height=200)


def _render_img_table(inv_df: pd.DataFrame, items: pd.DataFrame) -> None:
    """渲染庫存主檔"""
    col1, col2 = st.columns([2, 1])
    with col1:
        search_value = st.text_input("搜尋", placeholder="料號/倉庫/儲位...", key="img_search")
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("重置", key="img_reset"):
            st.rerun()

    display_df = inv_df.copy()

    if "ima02" not in display_df.columns:
        display_df = pd.merge(
            display_df,
            items[["ima01", "ima02", "ima021"]],
            left_on="img01",
            right_on="ima01",
            how="left",
        )

    if search_value:
        search_value_lower = search_value.lower()
        mask = (
            display_df["img01"].astype(str).str.contains(search_value_lower, na=False)
            | display_df["img02"].astype(str).str.contains(search_value_lower, na=False)
            | display_df["img03"].astype(str).str.contains(search_value_lower, na=False)
        )
        display_df = display_df[mask]

    start_idx, end_idx = _render_pagination(display_df, "page_img")
    page_df = display_df.iloc[start_idx:end_idx] if len(display_df) > 0 else pd.DataFrame()

    rename_cols = {"img01": "料號", "ima02": "品名", "img02": "倉庫", "img10": "庫存量"}
    display_cols = [c for c in rename_cols.keys() if c in page_df.columns]
    result_df = page_df[display_cols].rename(columns=rename_cols)

    st.dataframe(result_df, use_container_width=True, height=200)


def _render_tlf_table(tlf_df: pd.DataFrame) -> None:
    """渲染庫存交易檔"""
    col1, col2 = st.columns([2, 1])
    with col1:
        search_value = st.text_input("搜尋", placeholder="料號/倉庫/單號...", key="tlf_search")
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("重置", key="tlf_reset"):
            st.rerun()

    display_df = tlf_df.head(500).copy()

    if search_value:
        search_value_lower = search_value.lower()
        mask = (
            display_df["tlf01"].astype(str).str.contains(search_value_lower, na=False)
            | display_df["tlf061"].astype(str).str.contains(search_value_lower, na=False)
            | display_df["tlf13"].astype(str).str.contains(search_value_lower, na=False)
        )
        display_df = display_df[mask]

    start_idx, end_idx = _render_pagination(display_df, "page_tlf")
    page_df = display_df.iloc[start_idx:end_idx] if len(display_df) > 0 else pd.DataFrame()

    rename_cols = {
        "tlf01": "料號",
        "交易名稱": "類別",
        "tlf06": "日期",
        "tlf10": "數量",
        "tlf061": "倉庫",
    }
    display_cols = [c for c in rename_cols.keys() if c in page_df.columns]
    result_df = page_df[display_cols].rename(columns=rename_cols)

    st.dataframe(result_df, use_container_width=True, height=200)


def _render_po_table(tlf_df: pd.DataFrame) -> None:
    """渲染採購單據"""
    po_df = tlf_df[tlf_df["tlf19"] == "101"].copy()

    col1, col2 = st.columns([2, 1])
    with col1:
        search_value = st.text_input("搜尋", placeholder="料號/倉庫/單號...", key="po_search")
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("重置", key="po_reset"):
            st.rerun()

    display_df = po_df.head(300).copy()

    if search_value:
        search_value_lower = search_value.lower()
        mask = (
            display_df["tlf01"].astype(str).str.contains(search_value_lower, na=False)
            | display_df["tlf061"].astype(str).str.contains(search_value_lower, na=False)
            | display_df["tlf13"].astype(str).str.contains(search_value_lower, na=False)
        )
        display_df = display_df[mask]

    start_idx, end_idx = _render_pagination(display_df, "page_po")
    page_df = display_df.iloc[start_idx:end_idx] if len(display_df) > 0 else pd.DataFrame()

    rename_cols = {"tlf01": "料號", "tlf06": "日期", "tlf10": "數量", "tlf061": "倉庫"}
    display_cols = [c for c in rename_cols.keys() if c in page_df.columns]
    result_df = page_df[display_cols].rename(columns=rename_cols)

    st.dataframe(result_df, use_container_width=True, height=200)
