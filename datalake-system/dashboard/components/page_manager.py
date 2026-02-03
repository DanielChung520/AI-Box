# 代碼功能說明: Dashboard 頁面路由管理
# 創建日期: 2026-01-31
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-31

"""Dashboard 頁面路由管理"""

import streamlit as st
from typing import Callable, Dict, Any


class PageManager:
    """頁面管理器"""

    def __init__(self):
        self._pages: Dict[str, Callable] = {}
        self._data_loaded = False

    def register_page(self, page_id: str, render_func: Callable) -> None:
        """註冊頁面"""
        self._pages[page_id] = render_func

    def render(self, page_id: str, **kwargs: Any) -> None:
        """渲染指定頁面"""
        if page_id in self._pages:
            self._pages[page_id](**kwargs)
        else:
            st.error(f"頁面不存在: {page_id}")

    def get_registered_pages(self) -> list:
        """獲取已註冊頁面列表"""
        return list(self._pages.keys())

    def set_data_loaded(self, loaded: bool = True) -> None:
        """設置數據是否已載入"""
        self._data_loaded = loaded

    def is_data_loaded(self) -> bool:
        """檢查數據是否已載入"""
        return self._data_loaded


page_manager = PageManager()


def render_page(page_id: str, **kwargs: Any) -> None:
    """便捷函數：渲染頁面"""
    page_manager.render(page_id, **kwargs)


def register_page(page_id: str, render_func: Callable) -> None:
    """便捷函數：註冊頁面"""
    page_manager.register_page(page_id, render_func)
