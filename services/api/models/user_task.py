# 代碼功能說明: 用戶任務模型
# 創建日期: 2025-12-08 09:04:21 UTC+8
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-21

"""用戶任務模型 - 定義前端 UI 任務數據結構"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class Message(BaseModel):
    """消息模型"""

    id: str = Field(..., description="消息 ID")
    sender: str = Field(..., description="發送者（user/ai）")
    content: str = Field(..., description="消息內容")
    timestamp: str = Field(..., description="時間戳")
    containsMermaid: Optional[bool] = Field(None, description="是否包含 Mermaid 圖表")


class FileNode(BaseModel):
    """文件節點模型"""

    id: str = Field(..., description="節點 ID")
    name: str = Field(..., description="節點名稱")
    type: str = Field(..., description="節點類型（folder/file）")
    children: Optional[List["FileNode"]] = Field(None, description="子節點列表")


class ExecutionConfig(BaseModel):
    """執行配置模型"""

    mode: str = Field(default="free", description="執行模式（free/assistant/agent）")
    assistantId: Optional[str] = Field(default=None, description="助理 ID")
    agentId: Optional[str] = Field(default=None, description="代理 ID")
    # 修改時間：2025-12-13 18:28:38 (UTC+8) - 產品級 Chat：任務維度模型選擇與 session_id
    modelId: Optional[str] = Field(default=None, description="模型 ID（可選）")
    sessionId: Optional[str] = Field(default=None, description="Session ID（可選）")


class UserTaskBase(BaseModel):
    """用戶任務基礎模型"""

    title: str = Field(..., description="任務標題")
    status: str = Field(default="pending", description="任務狀態（pending/in-progress/completed）")
    # 修改時間：2025-12-09 - 添加任務狀態字段（activate/archive），用於控制任務是否在 Sidebar 中顯示
    # 修改時間：2026-01-21 - 添加 trash 狀態，支援 Soft Delete
    task_status: str = Field(
        default="activate",
        description="任務顯示狀態（activate/archive/trash），activate 表示顯示，archive 表示歸檔不顯示，trash 表示已刪除",
    )
    # 修改時間：2026-01-21 - 添加 Soft Delete 字段
    deleted_at: Optional[datetime] = Field(
        None,
        description="軟刪除時間（Soft Delete），為空表示未刪除",
    )
    # 修改時間：2026-01-21 - 添加預定永久刪除時間
    permanent_delete_at: Optional[datetime] = Field(
        None,
        description="預定永久刪除時間（7 天後自動清理）",
    )
    # 修改時間：2025-12-09 - 添加任務顏色標籤字段（類似 Apple Mac 的顏色標籤）
    label_color: Optional[str] = Field(
        None,
        description="任務顏色標籤（red/orange/yellow/green/blue/purple/gray），None 表示無顏色",
    )
    # 修改時間：2026-01-27 - 添加 Agent 任務標記字段
    is_agent_task: Optional[bool] = Field(
        False,
        description="是否為 Agent 任務（True 表示是 Agent 任務，False 或 None 表示一般任務）",
    )
    dueDate: Optional[str] = Field(None, description="截止日期")
    messages: Optional[List[Message]] = Field(default_factory=list, description="消息列表")
    # 修改時間：2025-01-27 - executionConfig 改為必填，默認值為 {'mode': 'free'}
    executionConfig: ExecutionConfig = Field(
        default_factory=lambda: ExecutionConfig(mode="free"), description="執行配置"
    )
    fileTree: Optional[List[FileNode]] = Field(default_factory=list, description="文件樹結構")


class UserTaskCreate(UserTaskBase):
    """創建用戶任務請求模型"""

    task_id: str = Field(..., description="任務 ID（前端生成的數字 ID）")
    # 修改時間：2025-01-27 - user_id 改為可選，後端會自動使用當前認證用戶的 user_id
    user_id: Optional[str] = Field(None, description="用戶 ID（可選，後端會自動填充）")


class UserTaskUpdate(BaseModel):
    """更新用戶任務請求模型"""

    title: Optional[str] = Field(None, description="任務標題")
    status: Optional[str] = Field(None, description="任務狀態")
    # 修改時間：2025-12-09 - 添加任務狀態字段（activate/archive）
    # 修改時間：2026-01-21 - 添加 trash 狀態
    task_status: Optional[str] = Field(None, description="任務顯示狀態（activate/archive/trash）")
    # 修改時間：2026-01-21 - 添加 Soft Delete 字段
    deleted_at: Optional[datetime] = Field(None, description="軟刪除時間")
    # 修改時間：2026-01-21 - 添加預定永久刪除時間
    permanent_delete_at: Optional[datetime] = Field(None, description="預定永久刪除時間")
    # 修改時間：2025-12-09 - 添加任務顏色標籤字段
    label_color: Optional[str] = Field(
        None, description="任務顏色標籤（red/orange/yellow/green/blue/purple/gray）"
    )
    # 修改時間：2026-01-27 - 添加 Agent 任務標記字段
    is_agent_task: Optional[bool] = Field(
        None, description="是否為 Agent 任務（True 表示是 Agent 任務，False 或 None 表示一般任務）"
    )
    dueDate: Optional[str] = Field(None, description="截止日期")
    messages: Optional[List[Message]] = Field(None, description="消息列表")
    executionConfig: Optional[ExecutionConfig] = Field(None, description="執行配置")
    fileTree: Optional[List[FileNode]] = Field(None, description="文件樹結構")


class UserTask(UserTaskBase):
    """用戶任務響應模型"""

    task_id: str = Field(..., description="任務 ID")
    user_id: str = Field(..., description="用戶 ID")
    created_at: datetime = Field(..., description="創建時間")
    updated_at: datetime = Field(..., description="更新時間")

    class Config:
        from_attributes = True
