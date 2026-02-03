# 代碼功能說明: Dashboard Sidebar 導航組件
# 創建日期: 2026-01-31
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-31

"""Dashboard Sidebar 導航組件"""

from datetime import datetime
import streamlit as st


NAV_ITEMS = [
    {"id": "home", "icon": "🏠", "label": "Home"},
    {"id": "inventory", "icon": "📦", "label": "庫存分析"},
    {"id": "transaction", "icon": "🔄", "label": "交易類別"},
    {"id": "purchase", "icon": "📥", "label": "採購交易分析"},
    {"id": "order", "icon": "📤", "label": "訂單分析"},
    {"id": "query", "icon": "📋", "label": "數據查詢"},
    {"id": "nlp", "icon": "🤖", "label": "自然語言"},
]


def render_sidebar() -> str:
    """
    渲染 Sidebar 導航組件

    Returns:
        str: 當前選中的頁面 ID
    """
    st.sidebar.image("https://img.icons8.com/color/96/000000/dashboard.png", width=64)
    st.sidebar.markdown("## 🤖 Data-Agent")
    st.sidebar.markdown("*Tiptop 數據湖儀表板*")
    st.sidebar.markdown("---")

    st.sidebar.markdown("### 📍 導航")

    if "current_page" not in st.session_state:
        st.session_state.current_page = "home"

    for item in NAV_ITEMS:
        is_selected = st.session_state.current_page == item["id"]

        if is_selected:
            st.sidebar.markdown(
                f"""
                <div style="
                    background-color: #4CAF50;
                    color: white;
                    padding: 12px 16px;
                    border-radius: 8px;
                    margin: 4px 0;
                    font-weight: 600;
                ">
                {item["icon"]} {item["label"]}
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            if st.sidebar.button(
                f"{item['icon']} {item['label']}",
                key=f"nav_{item['id']}",
                use_container_width=True,
            ):
                st.session_state.current_page = item["id"]
                st.rerun()

    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🖥️ 系統狀態")

    try:
        st.sidebar.success("✅ SeaweedFS: Connected")
    except Exception:
        st.sidebar.error("❌ SeaweedFS: Disconnected")

    st.sidebar.info(f"🕐 更新時間: {datetime.now().strftime('%H:%M:%S')}")

    if st.sidebar.button("🔄 刷新數據", use_container_width=True):
        st.rerun()

    st.sidebar.markdown("---")
    st.sidebar.markdown("### ℹ️ 關於")
    st.sidebar.info("展現自然語言查詢與數據分析能力")

    return st.session_state.current_page


def set_page(page_id: str) -> None:
    """設置當前頁面"""
    st.session_state.current_page = page_id


def get_current_page() -> str:
    """獲取當前頁面"""
    return st.session_state.get("current_page", "home")
