# 代碼功能說明: API 服務適配器（向後兼容）
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

"""API 服務適配器 - 重新導出 api 模組的內容"""


# 延遲導入以避免循環導入
# 如果需要在模組級別訪問 app，請使用 get_app() 函數
def get_app():
    """獲取 FastAPI 應用實例（延遲導入以避免循環導入）"""
    from api.main import app

    return app


__all__ = ["get_app"]
