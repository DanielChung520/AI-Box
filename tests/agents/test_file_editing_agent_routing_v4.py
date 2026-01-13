# 代碼功能說明: 文件編輯 Agent 語義路由測試腳本 v4.0
# 創建日期: 2026-01-12
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-13

"""文件編輯 Agent 語義路由測試腳本 v4.0

測試文件編輯 Agent 的語義路由能力（50 個 md-editor 場景：MD-001 ~ MD-050）
包含 L1-L5 層級驗證：
- L1: 語義理解（Semantic Understanding）
- L2: Intent DSL 匹配
- L3: Capability 發現和 Task DAG 生成
- L4: Policy & Constraint 檢查
- L5: 執行和觀察
"""

import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

# 添加項目根目錄到路徑
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from agents.services.orchestrator.orchestrator import AgentOrchestrator
from agents.task_analyzer.models import TaskAnalysisRequest

# Agent ID 定義
MD_EDITOR_AGENT_ID = "md-editor"
XLS_EDITOR_AGENT_ID = "xls-editor"
MD_TO_PDF_AGENT_ID = "md-to-pdf"
XLS_TO_PDF_AGENT_ID = "xls-to-pdf"
PDF_TO_MD_AGENT_ID = "pdf-to-md"

# md-editor 測試場景定義（50 個場景）
MD_EDITOR_SCENARIOS = [
    # 第一部分：基本編輯操作（MD-001 ~ MD-010）
    {
        "scenario_id": "MD-001",
        "category": "md-editor",
        "user_input": "編輯文件 README.md",
        "expected_task_type": "execution",
        "expected_agent": MD_EDITOR_AGENT_ID,
        "complexity": "簡單",
        "description": "基本編輯操作",
    },
    {
        "scenario_id": "MD-002",
        "category": "md-editor",
        "user_input": "修改 docs/guide.md 文件中的第一章節",
        "expected_task_type": "execution",
        "expected_agent": MD_EDITOR_AGENT_ID,
        "complexity": "中等",
        "description": "內容修改",
    },
    {
        "scenario_id": "MD-003",
        "category": "md-editor",
        "user_input": "在 README.md 中添加安裝說明",
        "expected_task_type": "execution",
        "expected_agent": MD_EDITOR_AGENT_ID,
        "complexity": "中等",
        "description": "內容添加",
    },
    {
        "scenario_id": "MD-004",
        "category": "md-editor",
        "user_input": "更新 CHANGELOG.md 文件",
        "expected_task_type": "execution",
        "expected_agent": MD_EDITOR_AGENT_ID,
        "complexity": "簡單",
        "description": "文件更新",
    },
    {
        "scenario_id": "MD-005",
        "category": "md-editor",
        "user_input": "刪除 docs/api.md 中的過時文檔",
        "expected_task_type": "execution",
        "expected_agent": MD_EDITOR_AGENT_ID,
        "complexity": "中等",
        "description": "內容刪除",
    },
    {
        "scenario_id": "MD-006",
        "category": "md-editor",
        "user_input": "將 README.md 中的 '舊版本' 替換為 '新版本'",
        "expected_task_type": "execution",
        "expected_agent": MD_EDITOR_AGENT_ID,
        "complexity": "中等",
        "description": "內容替換",
    },
    {
        "scenario_id": "MD-007",
        "category": "md-editor",
        "user_input": "重寫 docs/guide.md 中的使用說明章節",
        "expected_task_type": "execution",
        "expected_agent": MD_EDITOR_AGENT_ID,
        "complexity": "中等",
        "description": "內容重寫",
    },
    {
        "scenario_id": "MD-008",
        "category": "md-editor",
        "user_input": "在 README.md 的開頭插入版本信息",
        "expected_task_type": "execution",
        "expected_agent": MD_EDITOR_AGENT_ID,
        "complexity": "中等",
        "description": "內容插入",
    },
    {
        "scenario_id": "MD-009",
        "category": "md-editor",
        "user_input": "格式化整個 README.md 文件",
        "expected_task_type": "execution",
        "expected_agent": MD_EDITOR_AGENT_ID,
        "complexity": "簡單",
        "description": "文件格式化",
    },
    {
        "scenario_id": "MD-010",
        "category": "md-editor",
        "user_input": "整理 docs/guide.md 的章節結構",
        "expected_task_type": "execution",
        "expected_agent": MD_EDITOR_AGENT_ID,
        "complexity": "中等",
        "description": "結構整理",
    },
    # 第二部分：內容編輯（MD-011 ~ MD-020）
    {
        "scenario_id": "MD-011",
        "category": "md-editor",
        "user_input": "創建一個新的 Markdown 文件 CONTRIBUTING.md",
        "expected_task_type": "execution",
        "expected_agent": MD_EDITOR_AGENT_ID,
        "complexity": "簡單",
        "description": "文件創建",
    },
    {
        "scenario_id": "MD-012",
        "category": "md-editor",
        "user_input": "幫我產生一份 API 文檔 api.md",
        "expected_task_type": "execution",
        "expected_agent": MD_EDITOR_AGENT_ID,
        "complexity": "中等",
        "description": "文檔生成",
    },
    {
        "scenario_id": "MD-013",
        "category": "md-editor",
        "user_input": "在 README.md 中添加功能對照表",
        "expected_task_type": "execution",
        "expected_agent": MD_EDITOR_AGENT_ID,
        "complexity": "中等",
        "description": "表格添加",
    },
    {
        "scenario_id": "MD-014",
        "category": "md-editor",
        "user_input": "更新 docs/links.md 中的所有外部鏈接",
        "expected_task_type": "execution",
        "expected_agent": MD_EDITOR_AGENT_ID,
        "complexity": "中等",
        "description": "鏈接更新",
    },
    {
        "scenario_id": "MD-015",
        "category": "md-editor",
        "user_input": "在 README.md 中添加安裝代碼示例",
        "expected_task_type": "execution",
        "expected_agent": MD_EDITOR_AGENT_ID,
        "complexity": "中等",
        "description": "代碼示例添加",
    },
    {
        "scenario_id": "MD-016",
        "category": "md-editor",
        "user_input": "將 docs/guide.md 的主標題改為 '用戶指南'",
        "expected_task_type": "execution",
        "expected_agent": MD_EDITOR_AGENT_ID,
        "complexity": "簡單",
        "description": "標題修改",
    },
    {
        "scenario_id": "MD-017",
        "category": "md-editor",
        "user_input": "在 README.md 中添加項目截圖",
        "expected_task_type": "execution",
        "expected_agent": MD_EDITOR_AGENT_ID,
        "complexity": "中等",
        "description": "圖片添加",
    },
    {
        "scenario_id": "MD-018",
        "category": "md-editor",
        "user_input": "優化 docs/api.md 的 Markdown 格式",
        "expected_task_type": "execution",
        "expected_agent": MD_EDITOR_AGENT_ID,
        "complexity": "中等",
        "description": "格式優化",
    },
    {
        "scenario_id": "MD-019",
        "category": "md-editor",
        "user_input": "在 README.md 開頭添加目錄",
        "expected_task_type": "execution",
        "expected_agent": MD_EDITOR_AGENT_ID,
        "complexity": "中等",
        "description": "目錄添加",
    },
    {
        "scenario_id": "MD-020",
        "category": "md-editor",
        "user_input": "重組 docs/guide.md 的內容結構",
        "expected_task_type": "execution",
        "expected_agent": MD_EDITOR_AGENT_ID,
        "complexity": "複雜",
        "description": "結構重組",
    },
    # 第三部分：格式編輯（MD-021 ~ MD-030）
    {
        "scenario_id": "MD-021",
        "category": "md-editor",
        "user_input": "在 README.md 中添加二級標題 '功能介紹'",
        "expected_task_type": "execution",
        "expected_agent": MD_EDITOR_AGENT_ID,
        "complexity": "簡單",
        "description": "標題添加",
    },
    {
        "scenario_id": "MD-022",
        "category": "md-editor",
        "user_input": "將 docs/guide.md 中的無序列表改為有序列表",
        "expected_task_type": "execution",
        "expected_agent": MD_EDITOR_AGENT_ID,
        "complexity": "中等",
        "description": "列表格式轉換",
    },
    {
        "scenario_id": "MD-023",
        "category": "md-editor",
        "user_input": "在 README.md 中添加代碼塊示例",
        "expected_task_type": "execution",
        "expected_agent": MD_EDITOR_AGENT_ID,
        "complexity": "中等",
        "description": "代碼塊添加",
    },
    {
        "scenario_id": "MD-024",
        "category": "md-editor",
        "user_input": "將 docs/api.md 中的普通文本改為粗體",
        "expected_task_type": "execution",
        "expected_agent": MD_EDITOR_AGENT_ID,
        "complexity": "簡單",
        "description": "文本格式",
    },
    {
        "scenario_id": "MD-025",
        "category": "md-editor",
        "user_input": "在 README.md 中添加引用塊",
        "expected_task_type": "execution",
        "expected_agent": MD_EDITOR_AGENT_ID,
        "complexity": "簡單",
        "description": "引用塊添加",
    },
    {
        "scenario_id": "MD-026",
        "category": "md-editor",
        "user_input": "將 docs/guide.md 中的鏈接更新為新的 URL",
        "expected_task_type": "execution",
        "expected_agent": MD_EDITOR_AGENT_ID,
        "complexity": "中等",
        "description": "鏈接更新",
    },
    {
        "scenario_id": "MD-027",
        "category": "md-editor",
        "user_input": "在 README.md 中添加表格",
        "expected_task_type": "execution",
        "expected_agent": MD_EDITOR_AGENT_ID,
        "complexity": "中等",
        "description": "表格添加",
    },
    {
        "scenario_id": "MD-028",
        "category": "md-editor",
        "user_input": "將 docs/api.md 中的圖片路徑更新",
        "expected_task_type": "execution",
        "expected_agent": MD_EDITOR_AGENT_ID,
        "complexity": "中等",
        "description": "圖片路徑更新",
    },
    {
        "scenario_id": "MD-029",
        "category": "md-editor",
        "user_input": "在 README.md 中添加水平分隔線",
        "expected_task_type": "execution",
        "expected_agent": MD_EDITOR_AGENT_ID,
        "complexity": "簡單",
        "description": "分隔線添加",
    },
    {
        "scenario_id": "MD-030",
        "category": "md-editor",
        "user_input": "將 docs/guide.md 中的行內代碼格式化",
        "expected_task_type": "execution",
        "expected_agent": MD_EDITOR_AGENT_ID,
        "complexity": "中等",
        "description": "行內代碼格式",
    },
    # 第四部分：結構編輯（MD-031 ~ MD-040）
    {
        "scenario_id": "MD-031",
        "category": "md-editor",
        "user_input": "在 README.md 中重新組織章節順序",
        "expected_task_type": "execution",
        "expected_agent": MD_EDITOR_AGENT_ID,
        "complexity": "中等",
        "description": "章節重組",
    },
    {
        "scenario_id": "MD-032",
        "category": "md-editor",
        "user_input": "將 docs/guide.md 中的段落合併",
        "expected_task_type": "execution",
        "expected_agent": MD_EDITOR_AGENT_ID,
        "complexity": "中等",
        "description": "段落合併",
    },
    {
        "scenario_id": "MD-033",
        "category": "md-editor",
        "user_input": "在 README.md 中拆分過長的章節",
        "expected_task_type": "execution",
        "expected_agent": MD_EDITOR_AGENT_ID,
        "complexity": "中等",
        "description": "章節拆分",
    },
    {
        "scenario_id": "MD-034",
        "category": "md-editor",
        "user_input": "將 docs/api.md 中的內容按功能分類",
        "expected_task_type": "execution",
        "expected_agent": MD_EDITOR_AGENT_ID,
        "complexity": "複雜",
        "description": "內容分類",
    },
    {
        "scenario_id": "MD-035",
        "category": "md-editor",
        "user_input": "在 README.md 中添加新的章節 '常見問題'",
        "expected_task_type": "execution",
        "expected_agent": MD_EDITOR_AGENT_ID,
        "complexity": "簡單",
        "description": "章節添加",
    },
    {
        "scenario_id": "MD-036",
        "category": "md-editor",
        "user_input": "將 docs/guide.md 中的章節標題統一格式",
        "expected_task_type": "execution",
        "expected_agent": MD_EDITOR_AGENT_ID,
        "complexity": "中等",
        "description": "標題格式統一",
    },
    {
        "scenario_id": "MD-037",
        "category": "md-editor",
        "user_input": "在 README.md 中調整段落間距",
        "expected_task_type": "execution",
        "expected_agent": MD_EDITOR_AGENT_ID,
        "complexity": "簡單",
        "description": "段落間距",
    },
    {
        "scenario_id": "MD-038",
        "category": "md-editor",
        "user_input": "將 docs/api.md 中的嵌套列表展開",
        "expected_task_type": "execution",
        "expected_agent": MD_EDITOR_AGENT_ID,
        "complexity": "中等",
        "description": "列表展開",
    },
    {
        "scenario_id": "MD-039",
        "category": "md-editor",
        "user_input": "在 README.md 中重新編號所有章節",
        "expected_task_type": "execution",
        "expected_agent": MD_EDITOR_AGENT_ID,
        "complexity": "中等",
        "description": "章節編號",
    },
    {
        "scenario_id": "MD-040",
        "category": "md-editor",
        "user_input": "將 docs/guide.md 中的內容重新分組",
        "expected_task_type": "execution",
        "expected_agent": MD_EDITOR_AGENT_ID,
        "complexity": "複雜",
        "description": "內容分組",
    },
    # 第五部分：批量操作（MD-041 ~ MD-050）
    {
        "scenario_id": "MD-041",
        "category": "md-editor",
        "user_input": "批量替換 README.md 中所有的 '舊名稱' 為 '新名稱'",
        "expected_task_type": "execution",
        "expected_agent": MD_EDITOR_AGENT_ID,
        "complexity": "中等",
        "description": "批量替換",
    },
    {
        "scenario_id": "MD-042",
        "category": "md-editor",
        "user_input": "將 docs/ 目錄下所有 .md 文件的標題格式統一",
        "expected_task_type": "execution",
        "expected_agent": MD_EDITOR_AGENT_ID,
        "complexity": "複雜",
        "description": "批量格式統一",
    },
    {
        "scenario_id": "MD-043",
        "category": "md-editor",
        "user_input": "批量更新 README.md 中所有鏈接的域名",
        "expected_task_type": "execution",
        "expected_agent": MD_EDITOR_AGENT_ID,
        "complexity": "中等",
        "description": "批量鏈接更新",
    },
    {
        "scenario_id": "MD-044",
        "category": "md-editor",
        "user_input": "將 docs/guide.md 中所有圖片路徑前綴更新",
        "expected_task_type": "execution",
        "expected_agent": MD_EDITOR_AGENT_ID,
        "complexity": "中等",
        "description": "批量圖片路徑",
    },
    {
        "scenario_id": "MD-045",
        "category": "md-editor",
        "user_input": "在 README.md 中批量添加代碼語言標識",
        "expected_task_type": "execution",
        "expected_agent": MD_EDITOR_AGENT_ID,
        "complexity": "中等",
        "description": "批量代碼標識",
    },
    {
        "scenario_id": "MD-046",
        "category": "md-editor",
        "user_input": "將 docs/api.md 中所有表格對齊方式統一",
        "expected_task_type": "execution",
        "expected_agent": MD_EDITOR_AGENT_ID,
        "complexity": "中等",
        "description": "批量表格格式",
    },
    {
        "scenario_id": "MD-047",
        "category": "md-editor",
        "user_input": "批量格式化 README.md 中所有代碼塊",
        "expected_task_type": "execution",
        "expected_agent": MD_EDITOR_AGENT_ID,
        "complexity": "中等",
        "description": "批量代碼塊格式",
    },
    {
        "scenario_id": "MD-048",
        "category": "md-editor",
        "user_input": "將 docs/guide.md 中所有引用塊的格式統一",
        "expected_task_type": "execution",
        "expected_agent": MD_EDITOR_AGENT_ID,
        "complexity": "中等",
        "description": "批量引用塊格式",
    },
    {
        "scenario_id": "MD-049",
        "category": "md-editor",
        "user_input": "在 README.md 中批量添加章節錨點",
        "expected_task_type": "execution",
        "expected_agent": MD_EDITOR_AGENT_ID,
        "complexity": "中等",
        "description": "批量錨點添加",
    },
    {
        "scenario_id": "MD-050",
        "category": "md-editor",
        "user_input": "將 docs/ 目錄下所有 Markdown 文件的元數據更新",
        "expected_task_type": "execution",
        "expected_agent": MD_EDITOR_AGENT_ID,
        "complexity": "複雜",
        "description": "批量元數據更新",
    },
]

# xls-editor 測試場景定義（10 個場景）
XLS_EDITOR_SCENARIOS = [
    {
        "scenario_id": "XLS-001",
        "category": "xls-editor",
        "user_input": "編輯 data.xlsx 文件",
        "expected_task_type": "execution",
        "expected_agent": XLS_EDITOR_AGENT_ID,
        "complexity": "簡單",
        "description": "基本編輯操作",
    },
    {
        "scenario_id": "XLS-002",
        "category": "xls-editor",
        "user_input": "在 data.xlsx 的 Sheet1 中 A1 單元格輸入數據",
        "expected_task_type": "execution",
        "expected_agent": XLS_EDITOR_AGENT_ID,
        "complexity": "簡單",
        "description": "單元格編輯",
    },
    {
        "scenario_id": "XLS-003",
        "category": "xls-editor",
        "user_input": "將 data.xlsx 中 A1 單元格設置為粗體和紅色",
        "expected_task_type": "execution",
        "expected_agent": XLS_EDITOR_AGENT_ID,
        "complexity": "中等",
        "description": "格式設置",
    },
    {
        "scenario_id": "XLS-004",
        "category": "xls-editor",
        "user_input": "在 data.xlsx 的 Sheet1 中 B 列前插入一列",
        "expected_task_type": "execution",
        "expected_agent": XLS_EDITOR_AGENT_ID,
        "complexity": "中等",
        "description": "列插入",
    },
    {
        "scenario_id": "XLS-005",
        "category": "xls-editor",
        "user_input": "更新 data.xlsx 中 B10 單元格的公式為 =SUM(A1:A9)",
        "expected_task_type": "execution",
        "expected_agent": XLS_EDITOR_AGENT_ID,
        "complexity": "中等",
        "description": "公式編輯",
    },
    {
        "scenario_id": "XLS-006",
        "category": "xls-editor",
        "user_input": "刪除 data.xlsx 中 Sheet1 的第 5 行",
        "expected_task_type": "execution",
        "expected_agent": XLS_EDITOR_AGENT_ID,
        "complexity": "簡單",
        "description": "行刪除",
    },
    {
        "scenario_id": "XLS-007",
        "category": "xls-editor",
        "user_input": "在 data.xlsx 的 Sheet1 中添加一行數據",
        "expected_task_type": "execution",
        "expected_agent": XLS_EDITOR_AGENT_ID,
        "complexity": "中等",
        "description": "行添加",
    },
    {
        "scenario_id": "XLS-008",
        "category": "xls-editor",
        "user_input": "在 data.xlsx 的 Sheet1 中填充 A1 到 A10 的序號",
        "expected_task_type": "execution",
        "expected_agent": XLS_EDITOR_AGENT_ID,
        "complexity": "中等",
        "description": "數據填充",
    },
    {
        "scenario_id": "XLS-009",
        "category": "xls-editor",
        "user_input": "在 data.xlsx 中創建一個新的工作表 '統計'",
        "expected_task_type": "execution",
        "expected_agent": XLS_EDITOR_AGENT_ID,
        "complexity": "簡單",
        "description": "工作表創建",
    },
    {
        "scenario_id": "XLS-010",
        "category": "xls-editor",
        "user_input": "將 data.xlsx 中的 Sheet1 重命名為 '數據'",
        "expected_task_type": "execution",
        "expected_agent": XLS_EDITOR_AGENT_ID,
        "complexity": "簡單",
        "description": "工作表重命名",
    },
]

# md-to-pdf 測試場景定義（10 個場景）
MD_TO_PDF_SCENARIOS = [
    {
        "scenario_id": "MD2PDF-001",
        "category": "md-to-pdf",
        "user_input": "將 README.md 轉換為 PDF",
        "expected_task_type": "execution",
        "expected_agent": MD_TO_PDF_AGENT_ID,
        "complexity": "簡單",
        "description": "基本轉換",
    },
    {
        "scenario_id": "MD2PDF-002",
        "category": "md-to-pdf",
        "user_input": "幫我把 docs/guide.md 轉成 PDF 文件",
        "expected_task_type": "execution",
        "expected_agent": MD_TO_PDF_AGENT_ID,
        "complexity": "簡單",
        "description": "轉換操作",
    },
    {
        "scenario_id": "MD2PDF-003",
        "category": "md-to-pdf",
        "user_input": "生成 README.md 的 PDF 版本",
        "expected_task_type": "execution",
        "expected_agent": MD_TO_PDF_AGENT_ID,
        "complexity": "簡單",
        "description": "版本生成",
    },
    {
        "scenario_id": "MD2PDF-004",
        "category": "md-to-pdf",
        "user_input": "將 docs/api.md 導出為 PDF 文件",
        "expected_task_type": "execution",
        "expected_agent": MD_TO_PDF_AGENT_ID,
        "complexity": "簡單",
        "description": "導出操作",
    },
    {
        "scenario_id": "MD2PDF-005",
        "category": "md-to-pdf",
        "user_input": "將 CHANGELOG.md 轉換為 PDF 文檔",
        "expected_task_type": "execution",
        "expected_agent": MD_TO_PDF_AGENT_ID,
        "complexity": "簡單",
        "description": "文檔轉換",
    },
    {
        "scenario_id": "MD2PDF-006",
        "category": "md-to-pdf",
        "user_input": "把 README.md 製作成 PDF 文件",
        "expected_task_type": "execution",
        "expected_agent": MD_TO_PDF_AGENT_ID,
        "complexity": "簡單",
        "description": "文件製作",
    },
    {
        "scenario_id": "MD2PDF-007",
        "category": "md-to-pdf",
        "user_input": "將 docs/guide.md 轉為 PDF，頁面大小設為 A4",
        "expected_task_type": "execution",
        "expected_agent": MD_TO_PDF_AGENT_ID,
        "complexity": "中等",
        "description": "帶參數轉換",
    },
    {
        "scenario_id": "MD2PDF-008",
        "category": "md-to-pdf",
        "user_input": "將 README.md 轉為 PDF，並添加頁眉和頁腳",
        "expected_task_type": "execution",
        "expected_agent": MD_TO_PDF_AGENT_ID,
        "complexity": "中等",
        "description": "帶頁眉頁腳",
    },
    {
        "scenario_id": "MD2PDF-009",
        "category": "md-to-pdf",
        "user_input": "將 docs/guide.md 轉為 PDF，並自動生成目錄",
        "expected_task_type": "execution",
        "expected_agent": MD_TO_PDF_AGENT_ID,
        "complexity": "中等",
        "description": "帶目錄生成",
    },
    {
        "scenario_id": "MD2PDF-010",
        "category": "md-to-pdf",
        "user_input": "將 README.md 轉為 PDF，使用學術模板",
        "expected_task_type": "execution",
        "expected_agent": MD_TO_PDF_AGENT_ID,
        "complexity": "中等",
        "description": "帶模板轉換",
    },
]

# xls-to-pdf 測試場景定義（10 個場景）
XLS_TO_PDF_SCENARIOS = [
    {
        "scenario_id": "XLS2PDF-001",
        "category": "xls-to-pdf",
        "user_input": "將 data.xlsx 轉換為 PDF",
        "expected_task_type": "execution",
        "expected_agent": XLS_TO_PDF_AGENT_ID,
        "complexity": "簡單",
        "description": "基本轉換",
    },
    {
        "scenario_id": "XLS2PDF-002",
        "category": "xls-to-pdf",
        "user_input": "幫我把 report.xlsx 轉成 PDF 文件",
        "expected_task_type": "execution",
        "expected_agent": XLS_TO_PDF_AGENT_ID,
        "complexity": "簡單",
        "description": "轉換操作",
    },
    {
        "scenario_id": "XLS2PDF-003",
        "category": "xls-to-pdf",
        "user_input": "生成 data.xlsx 的 PDF 版本",
        "expected_task_type": "execution",
        "expected_agent": XLS_TO_PDF_AGENT_ID,
        "complexity": "簡單",
        "description": "版本生成",
    },
    {
        "scenario_id": "XLS2PDF-004",
        "category": "xls-to-pdf",
        "user_input": "將 report.xlsx 導出為 PDF 文件",
        "expected_task_type": "execution",
        "expected_agent": XLS_TO_PDF_AGENT_ID,
        "complexity": "簡單",
        "description": "導出操作",
    },
    {
        "scenario_id": "XLS2PDF-005",
        "category": "xls-to-pdf",
        "user_input": "將 data.xlsx 轉換為 PDF 文檔",
        "expected_task_type": "execution",
        "expected_agent": XLS_TO_PDF_AGENT_ID,
        "complexity": "簡單",
        "description": "文檔轉換",
    },
    {
        "scenario_id": "XLS2PDF-006",
        "category": "xls-to-pdf",
        "user_input": "把 report.xlsx 製作成 PDF 文件",
        "expected_task_type": "execution",
        "expected_agent": XLS_TO_PDF_AGENT_ID,
        "complexity": "簡單",
        "description": "文件製作",
    },
    {
        "scenario_id": "XLS2PDF-007",
        "category": "xls-to-pdf",
        "user_input": "將 data.xlsx 轉為 PDF，頁面大小設為 A4",
        "expected_task_type": "execution",
        "expected_agent": XLS_TO_PDF_AGENT_ID,
        "complexity": "中等",
        "description": "帶參數轉換",
    },
    {
        "scenario_id": "XLS2PDF-008",
        "category": "xls-to-pdf",
        "user_input": "將 report.xlsx 轉為 PDF，頁面方向設為橫向",
        "expected_task_type": "execution",
        "expected_agent": XLS_TO_PDF_AGENT_ID,
        "complexity": "中等",
        "description": "帶方向設置",
    },
    {
        "scenario_id": "XLS2PDF-009",
        "category": "xls-to-pdf",
        "user_input": "將 data.xlsx 轉為 PDF，縮放設為適合頁面",
        "expected_task_type": "execution",
        "expected_agent": XLS_TO_PDF_AGENT_ID,
        "complexity": "中等",
        "description": "帶縮放設置",
    },
    {
        "scenario_id": "XLS2PDF-010",
        "category": "xls-to-pdf",
        "user_input": "將 report.xlsx 轉為 PDF，邊距設為 1cm",
        "expected_task_type": "execution",
        "expected_agent": XLS_TO_PDF_AGENT_ID,
        "complexity": "中等",
        "description": "帶邊距設置",
    },
]

# pdf-to-md 測試場景定義（10 個場景）
PDF_TO_MD_SCENARIOS = [
    {
        "scenario_id": "PDF2MD-001",
        "category": "pdf-to-md",
        "user_input": "將 document.pdf 轉換為 Markdown",
        "expected_task_type": "execution",
        "expected_agent": PDF_TO_MD_AGENT_ID,
        "complexity": "簡單",
        "description": "基本轉換",
    },
    {
        "scenario_id": "PDF2MD-002",
        "category": "pdf-to-md",
        "user_input": "幫我把 report.pdf 轉成 Markdown 文件",
        "expected_task_type": "execution",
        "expected_agent": PDF_TO_MD_AGENT_ID,
        "complexity": "簡單",
        "description": "轉換操作",
    },
    {
        "scenario_id": "PDF2MD-003",
        "category": "pdf-to-md",
        "user_input": "生成 document.pdf 的 Markdown 版本",
        "expected_task_type": "execution",
        "expected_agent": PDF_TO_MD_AGENT_ID,
        "complexity": "簡單",
        "description": "版本生成",
    },
    {
        "scenario_id": "PDF2MD-004",
        "category": "pdf-to-md",
        "user_input": "將 report.pdf 導出為 Markdown 文件",
        "expected_task_type": "execution",
        "expected_agent": PDF_TO_MD_AGENT_ID,
        "complexity": "簡單",
        "description": "導出操作",
    },
    {
        "scenario_id": "PDF2MD-005",
        "category": "pdf-to-md",
        "user_input": "將 document.pdf 轉換為 Markdown 文檔",
        "expected_task_type": "execution",
        "expected_agent": PDF_TO_MD_AGENT_ID,
        "complexity": "簡單",
        "description": "文檔轉換",
    },
    {
        "scenario_id": "PDF2MD-006",
        "category": "pdf-to-md",
        "user_input": "把 report.pdf 提取為 Markdown 文件",
        "expected_task_type": "execution",
        "expected_agent": PDF_TO_MD_AGENT_ID,
        "complexity": "簡單",
        "description": "內容提取",
    },
    {
        "scenario_id": "PDF2MD-007",
        "category": "pdf-to-md",
        "user_input": "將 document.pdf 轉為 Markdown，並識別表格",
        "expected_task_type": "execution",
        "expected_agent": PDF_TO_MD_AGENT_ID,
        "complexity": "中等",
        "description": "帶表格識別",
    },
    {
        "scenario_id": "PDF2MD-008",
        "category": "pdf-to-md",
        "user_input": "將 report.pdf 轉為 Markdown，並提取所有圖片",
        "expected_task_type": "execution",
        "expected_agent": PDF_TO_MD_AGENT_ID,
        "complexity": "中等",
        "description": "帶圖片提取",
    },
    {
        "scenario_id": "PDF2MD-009",
        "category": "pdf-to-md",
        "user_input": "將 document.pdf 轉為 Markdown，並自動識別標題結構",
        "expected_task_type": "execution",
        "expected_agent": PDF_TO_MD_AGENT_ID,
        "complexity": "中等",
        "description": "帶結構識別",
    },
    {
        "scenario_id": "PDF2MD-010",
        "category": "pdf-to-md",
        "user_input": "將 report.pdf 轉為 Markdown，並識別列表結構",
        "expected_task_type": "execution",
        "expected_agent": PDF_TO_MD_AGENT_ID,
        "complexity": "中等",
        "description": "帶列表識別",
    },
]

# 測試結果收集器
_test_results: List[Dict[str, Any]] = []
_xls_test_results: List[Dict[str, Any]] = []
_md_to_pdf_test_results: List[Dict[str, Any]] = []
_xls_to_pdf_test_results: List[Dict[str, Any]] = []
_pdf_to_md_test_results: List[Dict[str, Any]] = []


class TestFileEditingAgentRoutingV4:
    """文件編輯 Agent 語義路由測試類 v4.0"""

    @pytest.fixture
    def orchestrator(self):
        """創建 Orchestrator 實例"""
        return AgentOrchestrator()

    @pytest.mark.asyncio
    @pytest.mark.parametrize("scenario", MD_EDITOR_SCENARIOS)
    async def test_md_editor_routing_v4(self, orchestrator, scenario):
        """測試 md-editor Agent 語義路由（v4 架構，包含 L1-L5 層級驗證）"""
        global _test_results

        scenario_id = scenario["scenario_id"]
        user_input = scenario["user_input"]
        expected_task_type = scenario.get("expected_task_type")
        expected_agent = scenario.get("expected_agent")
        complexity = scenario.get("complexity", "未知")
        description = scenario.get("description", "")

        print(f"\n{'='*80}")
        print(f"測試場景: {scenario_id}")
        print(f"類別: {scenario['category']}")
        print(f"複雜度: {complexity}")
        print(f"說明: {description}")
        print(f"用戶輸入: {user_input}")
        print(f"預期 Agent: {expected_agent}")
        print(f"{'='*80}")

        # 記錄開始時間（用於性能測試）
        start_time = time.time()

        # 執行意圖解析
        try:
            # 確保 builtin agents 已註冊到 Registry
            try:
                from agents.builtin import register_builtin_agents

                registered_agents = register_builtin_agents()
                if registered_agents:
                    print(
                        f"\n[Agent 註冊] 已註冊 {len(registered_agents)} 個內建 Agent: {list(registered_agents.keys())}"
                    )
            except Exception as e:
                print(f"\n[Agent 註冊警告] 註冊內建 Agent 時發生錯誤: {e}")

            analysis_request = TaskAnalysisRequest(task=user_input)
            task_analyzer = orchestrator._get_task_analyzer()
            analysis_result = await task_analyzer.analyze(analysis_request)

            # 計算響應時間
            latency_ms = (time.time() - start_time) * 1000

            print("\n[意圖解析結果]")
            print(f"  任務類型: {analysis_result.task_type.value}")
            intent_type = None
            if analysis_result.router_decision:
                intent_type = analysis_result.router_decision.intent_type
                print(f"  意圖類型: {intent_type}")
                print(f"  複雜度: {analysis_result.router_decision.complexity}")
                print(f"  需要 Agent: {analysis_result.router_decision.needs_agent}")
            print(f"  工作流類型: {analysis_result.workflow_type.value}")
            print(f"  置信度: {analysis_result.confidence:.2f}")
            print(f"  建議的 Agent: {analysis_result.suggested_agents}")
            print(f"  響應時間: {latency_ms:.2f}ms")

            # ========== L1 層級驗證：語義理解 ==========
            l1_passed = False
            l1_topics = None
            l1_entities = None
            l1_action_signals = None
            if analysis_result.router_decision:
                # 檢查 SemanticUnderstandingOutput Schema
                # 注意：v4 架構可能還沒有完全實現，這裡先檢查基本字段
                l1_passed = analysis_result.router_decision is not None
                # 如果 router_decision 有 topics、entities、action_signals 字段，則提取
                router_dict = analysis_result.router_decision.model_dump() if hasattr(analysis_result.router_decision, 'model_dump') else {}
                l1_topics = router_dict.get("topics", [])
                l1_entities = router_dict.get("entities", [])
                l1_action_signals = router_dict.get("action_signals", [])

            print("\n[L1 層級驗證：語義理解]")
            status_icon = "✅" if l1_passed else "⚠️"
            print(f"  {status_icon} L1 語義理解輸出: {'通過' if l1_passed else '部分通過（v4 架構可能尚未完全實現）'}")
            if l1_topics:
                print(f"    Topics: {l1_topics}")
            if l1_entities:
                print(f"    Entities: {l1_entities}")
            if l1_action_signals:
                print(f"    Action Signals: {l1_action_signals}")

            # ========== L2 層級驗證：Intent DSL 匹配 ==========
            l2_passed = False
            l2_intent = None
            if intent_type:
                l2_passed = True
                l2_intent = intent_type

            print("\n[L2 層級驗證：Intent DSL 匹配]")
            status_icon = "✅" if l2_passed else "⚠️"
            print(f"  {status_icon} L2 Intent DSL 匹配: {'通過' if l2_passed else '未匹配（v4 架構可能尚未完全實現）'}")
            if l2_intent:
                print(f"    Intent: {l2_intent}")

            # ========== L3 層級驗證：Capability 發現和 Task DAG ==========
            l3_passed = False
            l3_capability = None
            l3_task_dag = None
            # 檢查 analysis_details 中是否有 task_dag 或 capability 信息
            if analysis_result.analysis_details:
                l3_task_dag = analysis_result.analysis_details.get("task_dag")
                l3_capability = analysis_result.analysis_details.get("capability")
                if l3_task_dag or l3_capability:
                    l3_passed = True

            print("\n[L3 層級驗證：Capability 發現和 Task DAG]")
            status_icon = "✅" if l3_passed else "⚠️"
            print(f"  {status_icon} L3 Capability 發現: {'通過' if l3_passed else '未發現（v4 架構可能尚未完全實現）'}")
            if l3_capability:
                print(f"    Capability: {l3_capability}")
            if l3_task_dag:
                print(f"    Task DAG: {l3_task_dag}")

            # ========== L4 層級驗證：Policy & Constraint 檢查 ==========
            l4_passed = False
            l4_policy_check = None
            # 檢查 analysis_details 中是否有 policy_check 信息
            if analysis_result.analysis_details:
                l4_policy_check = analysis_result.analysis_details.get("policy_check")
                if l4_policy_check is not None:
                    l4_passed = True

            print("\n[L4 層級驗證：Policy & Constraint 檢查]")
            status_icon = "✅" if l4_passed else "⚠️"
            print(f"  {status_icon} L4 Policy 檢查: {'通過' if l4_passed else '未檢查（v4 架構可能尚未完全實現）'}")
            if l4_policy_check:
                print(f"    Policy Check: {l4_policy_check}")

            # ========== L5 層級驗證：執行和觀察 ==========
            l5_passed = False
            l5_execution_record = None
            # 檢查是否有執行記錄（通常通過 ExecutionRecord Store 記錄）
            # 注意：這裡只是檢查是否有相關信息，實際執行記錄可能在其他地方

            print("\n[L5 層級驗證：執行和觀察]")
            status_icon = "✅" if l5_passed else "⚠️"
            print(f"  {status_icon} L5 執行記錄: {'通過' if l5_passed else '未記錄（v4 架構可能尚未完全實現）'}")

            # ========== 基礎驗證：任務類型和 Agent 調用 ==========
            # 驗證任務類型
            task_type_match = False
            if expected_task_type:
                task_type_match = analysis_result.task_type.value == expected_task_type
                status_icon = "✅" if task_type_match else "❌"
                print("\n[基礎驗證]")
                print(
                    f"  {status_icon} 任務類型: 預期 {expected_task_type}, 實際 {analysis_result.task_type.value}"
                )

            # 驗證 Agent 調用
            agent_match = False
            if expected_agent:
                agent_match = expected_agent in analysis_result.suggested_agents
                status_icon = "✅" if agent_match else "❌"
                print(
                    f"  {status_icon} Agent 調用: 預期 {expected_agent}, 實際 {analysis_result.suggested_agents}"
                )

            # 檢查是否調用了 document-editing-agent（不應該調用）
            called_document_editing_agent = (
                "document-editing-agent" in analysis_result.suggested_agents
            )
            if called_document_editing_agent:
                print("  ⚠️  警告: 調用了已停用的 document-editing-agent")

            # 總結
            # 基礎驗證必須通過，L1-L5 層級驗證作為額外檢查（v4 架構可能尚未完全實現）
            all_passed = task_type_match and agent_match and not called_document_editing_agent
            print("\n[測試總結]")
            if all_passed:
                print("  ✅ 基礎驗證通過")
            else:
                print("  ❌ 基礎驗證未通過")
                if not task_type_match:
                    print("    - 任務類型不匹配")
                if not agent_match:
                    print("    - Agent 調用不匹配")
                if called_document_editing_agent:
                    print("    - 調用了已停用的 document-editing-agent")

            # 構建結果
            result = {
                "scenario_id": scenario_id,
                "category": scenario["category"],
                "complexity": complexity,
                "description": description,
                "user_input": user_input,
                "expected_task_type": expected_task_type,
                "expected_agent": expected_agent,
                "actual_task_type": analysis_result.task_type.value,
                "actual_intent_type": intent_type,
                "actual_agents": analysis_result.suggested_agents,
                "task_type_match": task_type_match,
                "agent_match": agent_match,
                "called_document_editing_agent": called_document_editing_agent,
                "all_passed": all_passed,
                "confidence": analysis_result.confidence,
                "router_confidence": (
                    analysis_result.router_decision.confidence
                    if analysis_result.router_decision
                    else None
                ),
                "latency_ms": latency_ms,
                # L1-L5 層級驗證結果
                "l1_passed": l1_passed,
                "l1_topics": l1_topics,
                "l1_entities": l1_entities,
                "l1_action_signals": l1_action_signals,
                "l2_passed": l2_passed,
                "l2_intent": l2_intent,
                "l3_passed": l3_passed,
                "l3_capability": l3_capability,
                "l3_task_dag": l3_task_dag is not None,
                "l4_passed": l4_passed,
                "l4_policy_check": l4_policy_check,
                "l5_passed": l5_passed,
                "l5_execution_record": l5_execution_record,
                "status": "✅ 通過" if all_passed else "❌ 失敗",
                "error": None,
            }

            _test_results.append(result)
            return result

        except Exception as e:
            print("\n[錯誤]")
            print(f"  ❌ 測試執行失敗: {e}")
            import traceback

            traceback.print_exc()

            error_result = {
                "scenario_id": scenario_id,
                "category": scenario["category"],
                "complexity": complexity,
                "description": description,
                "user_input": user_input,
                "expected_task_type": expected_task_type,
                "expected_agent": expected_agent,
                "actual_task_type": None,
                "actual_intent_type": None,
                "actual_agents": [],
                "task_type_match": False,
                "agent_match": False,
                "called_document_editing_agent": False,
                "all_passed": False,
                "confidence": 0.0,
                "router_confidence": None,
                "latency_ms": None,
                "l1_passed": False,
                "l2_passed": False,
                "l3_passed": False,
                "l4_passed": False,
                "l5_passed": False,
                "status": "❌ 錯誤",
                "error": str(e),
            }

            _test_results.append(error_result)
            raise

    @pytest.mark.asyncio
    @pytest.mark.parametrize("scenario", XLS_EDITOR_SCENARIOS)
    async def test_xls_editor_routing_v4(self, orchestrator, scenario):
        """測試 xls-editor Agent 語義路由（v4 架構，包含 L1-L5 層級驗證）"""
        global _xls_test_results

        scenario_id = scenario["scenario_id"]
        user_input = scenario["user_input"]
        expected_task_type = scenario.get("expected_task_type")
        expected_agent = scenario.get("expected_agent")
        complexity = scenario.get("complexity", "未知")
        description = scenario.get("description", "")

        print(f"\n{'='*80}")
        print(f"測試場景: {scenario_id}")
        print(f"類別: {scenario['category']}")
        print(f"複雜度: {complexity}")
        print(f"說明: {description}")
        print(f"用戶輸入: {user_input}")
        print(f"預期 Agent: {expected_agent}")
        print(f"{'='*80}")

        # 記錄開始時間（用於性能測試）
        start_time = time.time()

        # 執行意圖解析
        try:
            # 確保 builtin agents 已註冊到 Registry
            try:
                from agents.builtin import register_builtin_agents

                registered_agents = register_builtin_agents()
                if registered_agents:
                    print(
                        f"\n[Agent 註冊] 已註冊 {len(registered_agents)} 個內建 Agent: {list(registered_agents.keys())}"
                    )
            except Exception as e:
                print(f"\n[Agent 註冊警告] 註冊內建 Agent 時發生錯誤: {e}")

            analysis_request = TaskAnalysisRequest(task=user_input)
            task_analyzer = orchestrator._get_task_analyzer()
            analysis_result = await task_analyzer.analyze(analysis_request)

            # 計算響應時間
            latency_ms = (time.time() - start_time) * 1000

            print("\n[意圖解析結果]")
            print(f"  任務類型: {analysis_result.task_type.value}")
            intent_type = None
            if analysis_result.router_decision:
                intent_type = analysis_result.router_decision.intent_type
                print(f"  意圖類型: {intent_type}")
                print(f"  複雜度: {analysis_result.router_decision.complexity}")
                print(f"  需要 Agent: {analysis_result.router_decision.needs_agent}")
            print(f"  工作流類型: {analysis_result.workflow_type.value}")
            print(f"  置信度: {analysis_result.confidence:.2f}")
            print(f"  建議的 Agent: {analysis_result.suggested_agents}")
            print(f"  響應時間: {latency_ms:.2f}ms")

            # ========== L1 層級驗證：語義理解 ==========
            l1_passed = False
            l1_topics = None
            l1_entities = None
            l1_action_signals = None
            if analysis_result.router_decision:
                # 檢查 SemanticUnderstandingOutput Schema
                # 注意：v4 架構可能還沒有完全實現，這裡先檢查基本字段
                l1_passed = analysis_result.router_decision is not None
                # 如果 router_decision 有 topics、entities、action_signals 字段，則提取
                router_dict = analysis_result.router_decision.model_dump() if hasattr(analysis_result.router_decision, 'model_dump') else {}
                l1_topics = router_dict.get("topics", [])
                l1_entities = router_dict.get("entities", [])
                l1_action_signals = router_dict.get("action_signals", [])

            print("\n[L1 層級驗證：語義理解]")
            status_icon = "✅" if l1_passed else "⚠️"
            print(f"  {status_icon} L1 語義理解輸出: {'通過' if l1_passed else '部分通過（v4 架構可能尚未完全實現）'}")
            if l1_topics:
                print(f"    Topics: {l1_topics}")
            if l1_entities:
                print(f"    Entities: {l1_entities}")
            if l1_action_signals:
                print(f"    Action Signals: {l1_action_signals}")

            # ========== L2 層級驗證：Intent DSL 匹配 ==========
            l2_passed = False
            l2_intent = None
            if intent_type:
                l2_passed = True
                l2_intent = intent_type

            print("\n[L2 層級驗證：Intent DSL 匹配]")
            status_icon = "✅" if l2_passed else "⚠️"
            print(f"  {status_icon} L2 Intent DSL 匹配: {'通過' if l2_passed else '未匹配（v4 架構可能尚未完全實現）'}")
            if l2_intent:
                print(f"    Intent: {l2_intent}")

            # ========== L3 層級驗證：Capability 發現和 Task DAG ==========
            l3_passed = False
            l3_capability = None
            l3_task_dag = None
            # 檢查 analysis_details 中是否有 task_dag 或 capability 信息
            if analysis_result.analysis_details:
                l3_task_dag = analysis_result.analysis_details.get("task_dag")
                l3_capability = analysis_result.analysis_details.get("capability")
                if l3_task_dag or l3_capability:
                    l3_passed = True

            print("\n[L3 層級驗證：Capability 發現和 Task DAG]")
            status_icon = "✅" if l3_passed else "⚠️"
            print(f"  {status_icon} L3 Capability 發現: {'通過' if l3_passed else '未發現（v4 架構可能尚未完全實現）'}")
            if l3_capability:
                print(f"    Capability: {l3_capability}")
            if l3_task_dag:
                print(f"    Task DAG: {l3_task_dag}")

            # ========== L4 層級驗證：Policy & Constraint 檢查 ==========
            l4_passed = False
            l4_policy_check = None
            # 檢查 analysis_details 中是否有 policy_check 信息
            if analysis_result.analysis_details:
                l4_policy_check = analysis_result.analysis_details.get("policy_check")
                if l4_policy_check is not None:
                    l4_passed = True

            print("\n[L4 層級驗證：Policy & Constraint 檢查]")
            status_icon = "✅" if l4_passed else "⚠️"
            print(f"  {status_icon} L4 Policy 檢查: {'通過' if l4_passed else '未檢查（v4 架構可能尚未完全實現）'}")
            if l4_policy_check:
                print(f"    Policy Check: {l4_policy_check}")

            # ========== L5 層級驗證：執行和觀察 ==========
            l5_passed = False
            l5_execution_record = None
            # 檢查是否有執行記錄（通常通過 ExecutionRecord Store 記錄）
            # 注意：這裡只是檢查是否有相關信息，實際執行記錄可能在其他地方

            print("\n[L5 層級驗證：執行和觀察]")
            status_icon = "✅" if l5_passed else "⚠️"
            print(f"  {status_icon} L5 執行記錄: {'通過' if l5_passed else '未記錄（v4 架構可能尚未完全實現）'}")

            # ========== 基礎驗證：任務類型和 Agent 調用 ==========
            # 驗證任務類型
            task_type_match = False
            if expected_task_type:
                task_type_match = analysis_result.task_type.value == expected_task_type
                status_icon = "✅" if task_type_match else "❌"
                print("\n[基礎驗證]")
                print(
                    f"  {status_icon} 任務類型: 預期 {expected_task_type}, 實際 {analysis_result.task_type.value}"
                )

            # 驗證 Agent 調用
            agent_match = False
            if expected_agent:
                agent_match = expected_agent in analysis_result.suggested_agents
                status_icon = "✅" if agent_match else "❌"
                print(
                    f"  {status_icon} Agent 調用: 預期 {expected_agent}, 實際 {analysis_result.suggested_agents}"
                )

            # 檢查是否調用了 document-editing-agent（不應該調用）
            called_document_editing_agent = (
                "document-editing-agent" in analysis_result.suggested_agents
            )
            if called_document_editing_agent:
                print("  ⚠️  警告: 調用了已停用的 document-editing-agent")

            # 總結
            # 基礎驗證必須通過，L1-L5 層級驗證作為額外檢查（v4 架構可能尚未完全實現）
            all_passed = task_type_match and agent_match and not called_document_editing_agent
            print("\n[測試總結]")
            if all_passed:
                print("  ✅ 基礎驗證通過")
            else:
                print("  ❌ 基礎驗證未通過")
                if not task_type_match:
                    print("    - 任務類型不匹配")
                if not agent_match:
                    print("    - Agent 調用不匹配")
                if called_document_editing_agent:
                    print("    - 調用了已停用的 document-editing-agent")

            # 構建結果
            result = {
                "scenario_id": scenario_id,
                "category": scenario["category"],
                "complexity": complexity,
                "description": description,
                "user_input": user_input,
                "expected_task_type": expected_task_type,
                "expected_agent": expected_agent,
                "actual_task_type": analysis_result.task_type.value,
                "actual_intent_type": intent_type,
                "actual_agents": analysis_result.suggested_agents,
                "task_type_match": task_type_match,
                "agent_match": agent_match,
                "called_document_editing_agent": called_document_editing_agent,
                "all_passed": all_passed,
                "confidence": analysis_result.confidence,
                "router_confidence": (
                    analysis_result.router_decision.confidence
                    if analysis_result.router_decision
                    else None
                ),
                "latency_ms": latency_ms,
                # L1-L5 層級驗證結果
                "l1_passed": l1_passed,
                "l1_topics": l1_topics,
                "l1_entities": l1_entities,
                "l1_action_signals": l1_action_signals,
                "l2_passed": l2_passed,
                "l2_intent": l2_intent,
                "l3_passed": l3_passed,
                "l3_capability": l3_capability,
                "l3_task_dag": l3_task_dag is not None,
                "l4_passed": l4_passed,
                "l4_policy_check": l4_policy_check,
                "l5_passed": l5_passed,
                "l5_execution_record": l5_execution_record,
                "status": "✅ 通過" if all_passed else "❌ 失敗",
                "error": None,
            }

            _xls_test_results.append(result)
            return result

        except Exception as e:
            print("\n[錯誤]")
            print(f"  ❌ 測試執行失敗: {e}")
            import traceback

            traceback.print_exc()

            error_result = {
                "scenario_id": scenario_id,
                "category": scenario["category"],
                "complexity": complexity,
                "description": description,
                "user_input": user_input,
                "expected_task_type": expected_task_type,
                "expected_agent": expected_agent,
                "actual_task_type": None,
                "actual_intent_type": None,
                "actual_agents": [],
                "task_type_match": False,
                "agent_match": False,
                "called_document_editing_agent": False,
                "all_passed": False,
                "confidence": 0.0,
                "router_confidence": None,
                "latency_ms": None,
                "l1_passed": False,
                "l2_passed": False,
                "l3_passed": False,
                "l4_passed": False,
                "l5_passed": False,
                "status": "❌ 錯誤",
                "error": str(e),
            }

            _xls_test_results.append(error_result)
            raise

    @pytest.mark.asyncio
    @pytest.mark.parametrize("scenario", MD_TO_PDF_SCENARIOS)
    async def test_md_to_pdf_routing_v4(self, orchestrator, scenario):
        """測試 md-to-pdf Agent 語義路由（v4 架構，包含 L1-L5 層級驗證）"""
        global _md_to_pdf_test_results

        scenario_id = scenario["scenario_id"]
        user_input = scenario["user_input"]
        expected_task_type = scenario.get("expected_task_type")
        expected_agent = scenario.get("expected_agent")
        complexity = scenario.get("complexity", "未知")
        description = scenario.get("description", "")

        print(f"\n{'='*80}")
        print(f"測試場景: {scenario_id}")
        print(f"類別: {scenario['category']}")
        print(f"複雜度: {complexity}")
        print(f"說明: {description}")
        print(f"用戶輸入: {user_input}")
        print(f"預期 Agent: {expected_agent}")
        print(f"{'='*80}")

        # 記錄開始時間（用於性能測試）
        start_time = time.time()

        # 執行意圖解析
        try:
            # 確保 builtin agents 已註冊到 Registry
            try:
                from agents.builtin import register_builtin_agents

                registered_agents = register_builtin_agents()
                if registered_agents:
                    print(
                        f"\n[Agent 註冊] 已註冊 {len(registered_agents)} 個內建 Agent: {list(registered_agents.keys())}"
                    )
            except Exception as e:
                print(f"\n[Agent 註冊警告] 註冊內建 Agent 時發生錯誤: {e}")

            analysis_request = TaskAnalysisRequest(task=user_input)
            task_analyzer = orchestrator._get_task_analyzer()
            analysis_result = await task_analyzer.analyze(analysis_request)

            # 計算響應時間
            latency_ms = (time.time() - start_time) * 1000

            print("\n[意圖解析結果]")
            print(f"  任務類型: {analysis_result.task_type.value}")
            intent_type = None
            if analysis_result.router_decision:
                intent_type = analysis_result.router_decision.intent_type
                print(f"  意圖類型: {intent_type}")
                print(f"  複雜度: {analysis_result.router_decision.complexity}")
                print(f"  需要 Agent: {analysis_result.router_decision.needs_agent}")
            print(f"  工作流類型: {analysis_result.workflow_type.value}")
            print(f"  置信度: {analysis_result.confidence:.2f}")
            print(f"  建議的 Agent: {analysis_result.suggested_agents}")
            print(f"  響應時間: {latency_ms:.2f}ms")

            # ========== L1 層級驗證：語義理解 ==========
            l1_passed = False
            l1_topics = None
            l1_entities = None
            l1_action_signals = None
            if analysis_result.router_decision:
                l1_passed = analysis_result.router_decision is not None
                router_dict = analysis_result.router_decision.model_dump() if hasattr(analysis_result.router_decision, 'model_dump') else {}
                l1_topics = router_dict.get("topics", [])
                l1_entities = router_dict.get("entities", [])
                l1_action_signals = router_dict.get("action_signals", [])

            print("\n[L1 層級驗證：語義理解]")
            status_icon = "✅" if l1_passed else "⚠️"
            print(f"  {status_icon} L1 語義理解輸出: {'通過' if l1_passed else '部分通過（v4 架構可能尚未完全實現）'}")
            if l1_topics:
                print(f"    Topics: {l1_topics}")
            if l1_entities:
                print(f"    Entities: {l1_entities}")
            if l1_action_signals:
                print(f"    Action Signals: {l1_action_signals}")

            # ========== L2 層級驗證：Intent DSL 匹配 ==========
            l2_passed = False
            l2_intent = None
            if intent_type:
                l2_passed = True
                l2_intent = intent_type

            print("\n[L2 層級驗證：Intent DSL 匹配]")
            status_icon = "✅" if l2_passed else "⚠️"
            print(f"  {status_icon} L2 Intent DSL 匹配: {'通過' if l2_passed else '未匹配（v4 架構可能尚未完全實現）'}")
            if l2_intent:
                print(f"    Intent: {l2_intent}")

            # ========== L3 層級驗證：Capability 發現和 Task DAG ==========
            l3_passed = False
            l3_capability = None
            l3_task_dag = None
            if analysis_result.analysis_details:
                l3_task_dag = analysis_result.analysis_details.get("task_dag")
                l3_capability = analysis_result.analysis_details.get("capability")
                if l3_task_dag or l3_capability:
                    l3_passed = True

            print("\n[L3 層級驗證：Capability 發現和 Task DAG]")
            status_icon = "✅" if l3_passed else "⚠️"
            print(f"  {status_icon} L3 Capability 發現: {'通過' if l3_passed else '未發現（v4 架構可能尚未完全實現）'}")
            if l3_capability:
                print(f"    Capability: {l3_capability}")
            if l3_task_dag:
                print(f"    Task DAG: {l3_task_dag}")

            # ========== L4 層級驗證：Policy & Constraint 檢查 ==========
            l4_passed = False
            l4_policy_check = None
            if analysis_result.analysis_details:
                l4_policy_check = analysis_result.analysis_details.get("policy_check")
                if l4_policy_check is not None:
                    l4_passed = True

            print("\n[L4 層級驗證：Policy & Constraint 檢查]")
            status_icon = "✅" if l4_passed else "⚠️"
            print(f"  {status_icon} L4 Policy 檢查: {'通過' if l4_passed else '未檢查（v4 架構可能尚未完全實現）'}")
            if l4_policy_check:
                print(f"    Policy Check: {l4_policy_check}")

            # ========== L5 層級驗證：執行和觀察 ==========
            l5_passed = False
            l5_execution_record = None

            print("\n[L5 層級驗證：執行和觀察]")
            status_icon = "✅" if l5_passed else "⚠️"
            print(f"  {status_icon} L5 執行記錄: {'通過' if l5_passed else '未記錄（v4 架構可能尚未完全實現）'}")

            # ========== 基礎驗證：任務類型和 Agent 調用 ==========
            task_type_match = False
            if expected_task_type:
                task_type_match = analysis_result.task_type.value == expected_task_type
                status_icon = "✅" if task_type_match else "❌"
                print("\n[基礎驗證]")
                print(
                    f"  {status_icon} 任務類型: 預期 {expected_task_type}, 實際 {analysis_result.task_type.value}"
                )

            agent_match = False
            if expected_agent:
                agent_match = expected_agent in analysis_result.suggested_agents
                status_icon = "✅" if agent_match else "❌"
                print(
                    f"  {status_icon} Agent 調用: 預期 {expected_agent}, 實際 {analysis_result.suggested_agents}"
                )

            called_document_editing_agent = (
                "document-editing-agent" in analysis_result.suggested_agents
            )
            if called_document_editing_agent:
                print("  ⚠️  警告: 調用了已停用的 document-editing-agent")

            all_passed = task_type_match and agent_match and not called_document_editing_agent
            print("\n[測試總結]")
            if all_passed:
                print("  ✅ 基礎驗證通過")
            else:
                print("  ❌ 基礎驗證未通過")
                if not task_type_match:
                    print("    - 任務類型不匹配")
                if not agent_match:
                    print("    - Agent 調用不匹配")
                if called_document_editing_agent:
                    print("    - 調用了已停用的 document-editing-agent")

            result = {
                "scenario_id": scenario_id,
                "category": scenario["category"],
                "complexity": complexity,
                "description": description,
                "user_input": user_input,
                "expected_task_type": expected_task_type,
                "expected_agent": expected_agent,
                "actual_task_type": analysis_result.task_type.value,
                "actual_intent_type": intent_type,
                "actual_agents": analysis_result.suggested_agents,
                "task_type_match": task_type_match,
                "agent_match": agent_match,
                "called_document_editing_agent": called_document_editing_agent,
                "all_passed": all_passed,
                "confidence": analysis_result.confidence,
                "router_confidence": (
                    analysis_result.router_decision.confidence
                    if analysis_result.router_decision
                    else None
                ),
                "latency_ms": latency_ms,
                "l1_passed": l1_passed,
                "l1_topics": l1_topics,
                "l1_entities": l1_entities,
                "l1_action_signals": l1_action_signals,
                "l2_passed": l2_passed,
                "l2_intent": l2_intent,
                "l3_passed": l3_passed,
                "l3_capability": l3_capability,
                "l3_task_dag": l3_task_dag is not None,
                "l4_passed": l4_passed,
                "l4_policy_check": l4_policy_check,
                "l5_passed": l5_passed,
                "l5_execution_record": l5_execution_record,
                "status": "✅ 通過" if all_passed else "❌ 失敗",
                "error": None,
            }

            _md_to_pdf_test_results.append(result)
            return result

        except Exception as e:
            print("\n[錯誤]")
            print(f"  ❌ 測試執行失敗: {e}")
            import traceback

            traceback.print_exc()

            error_result = {
                "scenario_id": scenario_id,
                "category": scenario["category"],
                "complexity": complexity,
                "description": description,
                "user_input": user_input,
                "expected_task_type": expected_task_type,
                "expected_agent": expected_agent,
                "actual_task_type": None,
                "actual_intent_type": None,
                "actual_agents": [],
                "task_type_match": False,
                "agent_match": False,
                "called_document_editing_agent": False,
                "all_passed": False,
                "confidence": 0.0,
                "router_confidence": None,
                "latency_ms": None,
                "l1_passed": False,
                "l2_passed": False,
                "l3_passed": False,
                "l4_passed": False,
                "l5_passed": False,
                "status": "❌ 錯誤",
                "error": str(e),
            }

            _md_to_pdf_test_results.append(error_result)
            raise

    @pytest.mark.asyncio
    @pytest.mark.parametrize("scenario", XLS_TO_PDF_SCENARIOS)
    async def test_xls_to_pdf_routing_v4(self, orchestrator, scenario):
        """測試 xls-to-pdf Agent 語義路由（v4 架構，包含 L1-L5 層級驗證）"""
        global _xls_to_pdf_test_results

        scenario_id = scenario["scenario_id"]
        user_input = scenario["user_input"]
        expected_task_type = scenario.get("expected_task_type")
        expected_agent = scenario.get("expected_agent")
        complexity = scenario.get("complexity", "未知")
        description = scenario.get("description", "")

        print(f"\n{'='*80}")
        print(f"測試場景: {scenario_id}")
        print(f"類別: {scenario['category']}")
        print(f"複雜度: {complexity}")
        print(f"說明: {description}")
        print(f"用戶輸入: {user_input}")
        print(f"預期 Agent: {expected_agent}")
        print(f"{'='*80}")

        start_time = time.time()

        try:
            try:
                from agents.builtin import register_builtin_agents

                registered_agents = register_builtin_agents()
                if registered_agents:
                    print(
                        f"\n[Agent 註冊] 已註冊 {len(registered_agents)} 個內建 Agent: {list(registered_agents.keys())}"
                    )
            except Exception as e:
                print(f"\n[Agent 註冊警告] 註冊內建 Agent 時發生錯誤: {e}")

            analysis_request = TaskAnalysisRequest(task=user_input)
            task_analyzer = orchestrator._get_task_analyzer()
            analysis_result = await task_analyzer.analyze(analysis_request)

            latency_ms = (time.time() - start_time) * 1000

            print("\n[意圖解析結果]")
            print(f"  任務類型: {analysis_result.task_type.value}")
            intent_type = None
            if analysis_result.router_decision:
                intent_type = analysis_result.router_decision.intent_type
                print(f"  意圖類型: {intent_type}")
                print(f"  複雜度: {analysis_result.router_decision.complexity}")
                print(f"  需要 Agent: {analysis_result.router_decision.needs_agent}")
            print(f"  工作流類型: {analysis_result.workflow_type.value}")
            print(f"  置信度: {analysis_result.confidence:.2f}")
            print(f"  建議的 Agent: {analysis_result.suggested_agents}")
            print(f"  響應時間: {latency_ms:.2f}ms")

            # L1 層級驗證
            l1_passed = False
            l1_topics = None
            l1_entities = None
            l1_action_signals = None
            if analysis_result.router_decision:
                l1_passed = analysis_result.router_decision is not None
                router_dict = analysis_result.router_decision.model_dump() if hasattr(analysis_result.router_decision, 'model_dump') else {}
                l1_topics = router_dict.get("topics", [])
                l1_entities = router_dict.get("entities", [])
                l1_action_signals = router_dict.get("action_signals", [])

            print("\n[L1 層級驗證：語義理解]")
            status_icon = "✅" if l1_passed else "⚠️"
            print(f"  {status_icon} L1 語義理解輸出: {'通過' if l1_passed else '部分通過（v4 架構可能尚未完全實現）'}")

            # L2 層級驗證
            l2_passed = False
            l2_intent = None
            if intent_type:
                l2_passed = True
                l2_intent = intent_type

            print("\n[L2 層級驗證：Intent DSL 匹配]")
            status_icon = "✅" if l2_passed else "⚠️"
            print(f"  {status_icon} L2 Intent DSL 匹配: {'通過' if l2_passed else '未匹配（v4 架構可能尚未完全實現）'}")

            # L3 層級驗證
            l3_passed = False
            l3_capability = None
            l3_task_dag = None
            if analysis_result.analysis_details:
                l3_task_dag = analysis_result.analysis_details.get("task_dag")
                l3_capability = analysis_result.analysis_details.get("capability")
                if l3_task_dag or l3_capability:
                    l3_passed = True

            print("\n[L3 層級驗證：Capability 發現和 Task DAG]")
            status_icon = "✅" if l3_passed else "⚠️"
            print(f"  {status_icon} L3 Capability 發現: {'通過' if l3_passed else '未發現（v4 架構可能尚未完全實現）'}")

            # L4 層級驗證
            l4_passed = False
            l4_policy_check = None
            if analysis_result.analysis_details:
                l4_policy_check = analysis_result.analysis_details.get("policy_check")
                if l4_policy_check is not None:
                    l4_passed = True

            print("\n[L4 層級驗證：Policy & Constraint 檢查]")
            status_icon = "✅" if l4_passed else "⚠️"
            print(f"  {status_icon} L4 Policy 檢查: {'通過' if l4_passed else '未檢查（v4 架構可能尚未完全實現）'}")

            # L5 層級驗證
            l5_passed = False
            l5_execution_record = None

            print("\n[L5 層級驗證：執行和觀察]")
            status_icon = "✅" if l5_passed else "⚠️"
            print(f"  {status_icon} L5 執行記錄: {'通過' if l5_passed else '未記錄（v4 架構可能尚未完全實現）'}")

            # 基礎驗證
            task_type_match = False
            if expected_task_type:
                task_type_match = analysis_result.task_type.value == expected_task_type
                status_icon = "✅" if task_type_match else "❌"
                print("\n[基礎驗證]")
                print(
                    f"  {status_icon} 任務類型: 預期 {expected_task_type}, 實際 {analysis_result.task_type.value}"
                )

            agent_match = False
            if expected_agent:
                agent_match = expected_agent in analysis_result.suggested_agents
                status_icon = "✅" if agent_match else "❌"
                print(
                    f"  {status_icon} Agent 調用: 預期 {expected_agent}, 實際 {analysis_result.suggested_agents}"
                )

            called_document_editing_agent = (
                "document-editing-agent" in analysis_result.suggested_agents
            )
            if called_document_editing_agent:
                print("  ⚠️  警告: 調用了已停用的 document-editing-agent")

            all_passed = task_type_match and agent_match and not called_document_editing_agent
            print("\n[測試總結]")
            if all_passed:
                print("  ✅ 基礎驗證通過")
            else:
                print("  ❌ 基礎驗證未通過")
                if not task_type_match:
                    print("    - 任務類型不匹配")
                if not agent_match:
                    print("    - Agent 調用不匹配")
                if called_document_editing_agent:
                    print("    - 調用了已停用的 document-editing-agent")

            result = {
                "scenario_id": scenario_id,
                "category": scenario["category"],
                "complexity": complexity,
                "description": description,
                "user_input": user_input,
                "expected_task_type": expected_task_type,
                "expected_agent": expected_agent,
                "actual_task_type": analysis_result.task_type.value,
                "actual_intent_type": intent_type,
                "actual_agents": analysis_result.suggested_agents,
                "task_type_match": task_type_match,
                "agent_match": agent_match,
                "called_document_editing_agent": called_document_editing_agent,
                "all_passed": all_passed,
                "confidence": analysis_result.confidence,
                "router_confidence": (
                    analysis_result.router_decision.confidence
                    if analysis_result.router_decision
                    else None
                ),
                "latency_ms": latency_ms,
                "l1_passed": l1_passed,
                "l1_topics": l1_topics,
                "l1_entities": l1_entities,
                "l1_action_signals": l1_action_signals,
                "l2_passed": l2_passed,
                "l2_intent": l2_intent,
                "l3_passed": l3_passed,
                "l3_capability": l3_capability,
                "l3_task_dag": l3_task_dag is not None,
                "l4_passed": l4_passed,
                "l4_policy_check": l4_policy_check,
                "l5_passed": l5_passed,
                "l5_execution_record": l5_execution_record,
                "status": "✅ 通過" if all_passed else "❌ 失敗",
                "error": None,
            }

            _xls_to_pdf_test_results.append(result)
            return result

        except Exception as e:
            print("\n[錯誤]")
            print(f"  ❌ 測試執行失敗: {e}")
            import traceback

            traceback.print_exc()

            error_result = {
                "scenario_id": scenario_id,
                "category": scenario["category"],
                "complexity": complexity,
                "description": description,
                "user_input": user_input,
                "expected_task_type": expected_task_type,
                "expected_agent": expected_agent,
                "actual_task_type": None,
                "actual_intent_type": None,
                "actual_agents": [],
                "task_type_match": False,
                "agent_match": False,
                "called_document_editing_agent": False,
                "all_passed": False,
                "confidence": 0.0,
                "router_confidence": None,
                "latency_ms": None,
                "l1_passed": False,
                "l2_passed": False,
                "l3_passed": False,
                "l4_passed": False,
                "l5_passed": False,
                "status": "❌ 錯誤",
                "error": str(e),
            }

            _xls_to_pdf_test_results.append(error_result)
            raise

    @pytest.mark.asyncio
    @pytest.mark.parametrize("scenario", PDF_TO_MD_SCENARIOS)
    async def test_pdf_to_md_routing_v4(self, orchestrator, scenario):
        """測試 pdf-to-md Agent 語義路由（v4 架構，包含 L1-L5 層級驗證）"""
        global _pdf_to_md_test_results

        scenario_id = scenario["scenario_id"]
        user_input = scenario["user_input"]
        expected_task_type = scenario.get("expected_task_type")
        expected_agent = scenario.get("expected_agent")
        complexity = scenario.get("complexity", "未知")
        description = scenario.get("description", "")

        print(f"\n{'='*80}")
        print(f"測試場景: {scenario_id}")
        print(f"類別: {scenario['category']}")
        print(f"複雜度: {complexity}")
        print(f"說明: {description}")
        print(f"用戶輸入: {user_input}")
        print(f"預期 Agent: {expected_agent}")
        print(f"{'='*80}")

        start_time = time.time()

        try:
            try:
                from agents.builtin import register_builtin_agents

                registered_agents = register_builtin_agents()
                if registered_agents:
                    print(
                        f"\n[Agent 註冊] 已註冊 {len(registered_agents)} 個內建 Agent: {list(registered_agents.keys())}"
                    )
            except Exception as e:
                print(f"\n[Agent 註冊警告] 註冊內建 Agent 時發生錯誤: {e}")

            analysis_request = TaskAnalysisRequest(task=user_input)
            task_analyzer = orchestrator._get_task_analyzer()
            analysis_result = await task_analyzer.analyze(analysis_request)

            latency_ms = (time.time() - start_time) * 1000

            print("\n[意圖解析結果]")
            print(f"  任務類型: {analysis_result.task_type.value}")
            intent_type = None
            if analysis_result.router_decision:
                intent_type = analysis_result.router_decision.intent_type
                print(f"  意圖類型: {intent_type}")
                print(f"  複雜度: {analysis_result.router_decision.complexity}")
                print(f"  需要 Agent: {analysis_result.router_decision.needs_agent}")
            print(f"  工作流類型: {analysis_result.workflow_type.value}")
            print(f"  置信度: {analysis_result.confidence:.2f}")
            print(f"  建議的 Agent: {analysis_result.suggested_agents}")
            print(f"  響應時間: {latency_ms:.2f}ms")

            # L1 層級驗證
            l1_passed = False
            l1_topics = None
            l1_entities = None
            l1_action_signals = None
            if analysis_result.router_decision:
                l1_passed = analysis_result.router_decision is not None
                router_dict = analysis_result.router_decision.model_dump() if hasattr(analysis_result.router_decision, 'model_dump') else {}
                l1_topics = router_dict.get("topics", [])
                l1_entities = router_dict.get("entities", [])
                l1_action_signals = router_dict.get("action_signals", [])

            print("\n[L1 層級驗證：語義理解]")
            status_icon = "✅" if l1_passed else "⚠️"
            print(f"  {status_icon} L1 語義理解輸出: {'通過' if l1_passed else '部分通過（v4 架構可能尚未完全實現）'}")

            # L2 層級驗證
            l2_passed = False
            l2_intent = None
            if intent_type:
                l2_passed = True
                l2_intent = intent_type

            print("\n[L2 層級驗證：Intent DSL 匹配]")
            status_icon = "✅" if l2_passed else "⚠️"
            print(f"  {status_icon} L2 Intent DSL 匹配: {'通過' if l2_passed else '未匹配（v4 架構可能尚未完全實現）'}")

            # L3 層級驗證
            l3_passed = False
            l3_capability = None
            l3_task_dag = None
            if analysis_result.analysis_details:
                l3_task_dag = analysis_result.analysis_details.get("task_dag")
                l3_capability = analysis_result.analysis_details.get("capability")
                if l3_task_dag or l3_capability:
                    l3_passed = True

            print("\n[L3 層級驗證：Capability 發現和 Task DAG]")
            status_icon = "✅" if l3_passed else "⚠️"
            print(f"  {status_icon} L3 Capability 發現: {'通過' if l3_passed else '未發現（v4 架構可能尚未完全實現）'}")

            # L4 層級驗證
            l4_passed = False
            l4_policy_check = None
            if analysis_result.analysis_details:
                l4_policy_check = analysis_result.analysis_details.get("policy_check")
                if l4_policy_check is not None:
                    l4_passed = True

            print("\n[L4 層級驗證：Policy & Constraint 檢查]")
            status_icon = "✅" if l4_passed else "⚠️"
            print(f"  {status_icon} L4 Policy 檢查: {'通過' if l4_passed else '未檢查（v4 架構可能尚未完全實現）'}")

            # L5 層級驗證
            l5_passed = False
            l5_execution_record = None

            print("\n[L5 層級驗證：執行和觀察]")
            status_icon = "✅" if l5_passed else "⚠️"
            print(f"  {status_icon} L5 執行記錄: {'通過' if l5_passed else '未記錄（v4 架構可能尚未完全實現）'}")

            # 基礎驗證
            task_type_match = False
            if expected_task_type:
                task_type_match = analysis_result.task_type.value == expected_task_type
                status_icon = "✅" if task_type_match else "❌"
                print("\n[基礎驗證]")
                print(
                    f"  {status_icon} 任務類型: 預期 {expected_task_type}, 實際 {analysis_result.task_type.value}"
                )

            agent_match = False
            if expected_agent:
                agent_match = expected_agent in analysis_result.suggested_agents
                status_icon = "✅" if agent_match else "❌"
                print(
                    f"  {status_icon} Agent 調用: 預期 {expected_agent}, 實際 {analysis_result.suggested_agents}"
                )

            called_document_editing_agent = (
                "document-editing-agent" in analysis_result.suggested_agents
            )
            if called_document_editing_agent:
                print("  ⚠️  警告: 調用了已停用的 document-editing-agent")

            all_passed = task_type_match and agent_match and not called_document_editing_agent
            print("\n[測試總結]")
            if all_passed:
                print("  ✅ 基礎驗證通過")
            else:
                print("  ❌ 基礎驗證未通過")
                if not task_type_match:
                    print("    - 任務類型不匹配")
                if not agent_match:
                    print("    - Agent 調用不匹配")
                if called_document_editing_agent:
                    print("    - 調用了已停用的 document-editing-agent")

            result = {
                "scenario_id": scenario_id,
                "category": scenario["category"],
                "complexity": complexity,
                "description": description,
                "user_input": user_input,
                "expected_task_type": expected_task_type,
                "expected_agent": expected_agent,
                "actual_task_type": analysis_result.task_type.value,
                "actual_intent_type": intent_type,
                "actual_agents": analysis_result.suggested_agents,
                "task_type_match": task_type_match,
                "agent_match": agent_match,
                "called_document_editing_agent": called_document_editing_agent,
                "all_passed": all_passed,
                "confidence": analysis_result.confidence,
                "router_confidence": (
                    analysis_result.router_decision.confidence
                    if analysis_result.router_decision
                    else None
                ),
                "latency_ms": latency_ms,
                "l1_passed": l1_passed,
                "l1_topics": l1_topics,
                "l1_entities": l1_entities,
                "l1_action_signals": l1_action_signals,
                "l2_passed": l2_passed,
                "l2_intent": l2_intent,
                "l3_passed": l3_passed,
                "l3_capability": l3_capability,
                "l3_task_dag": l3_task_dag is not None,
                "l4_passed": l4_passed,
                "l4_policy_check": l4_policy_check,
                "l5_passed": l5_passed,
                "l5_execution_record": l5_execution_record,
                "status": "✅ 通過" if all_passed else "❌ 失敗",
                "error": None,
            }

            _pdf_to_md_test_results.append(result)
            return result

        except Exception as e:
            print("\n[錯誤]")
            print(f"  ❌ 測試執行失敗: {e}")
            import traceback

            traceback.print_exc()

            error_result = {
                "scenario_id": scenario_id,
                "category": scenario["category"],
                "complexity": complexity,
                "description": description,
                "user_input": user_input,
                "expected_task_type": expected_task_type,
                "expected_agent": expected_agent,
                "actual_task_type": None,
                "actual_intent_type": None,
                "actual_agents": [],
                "task_type_match": False,
                "agent_match": False,
                "called_document_editing_agent": False,
                "all_passed": False,
                "confidence": 0.0,
                "router_confidence": None,
                "latency_ms": None,
                "l1_passed": False,
                "l2_passed": False,
                "l3_passed": False,
                "l4_passed": False,
                "l5_passed": False,
                "status": "❌ 錯誤",
                "error": str(e),
            }

            _pdf_to_md_test_results.append(error_result)
            raise


def save_test_results() -> Path:
    """保存測試結果到 JSON 文件"""
    global _test_results

    output_dir = Path(__file__).parent / "test_reports"
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"md_editor_v4_test_results_{timestamp}.json"

    total = len(_test_results)
    passed = sum(1 for r in _test_results if r.get("all_passed", False))
    failed = total - passed
    pass_rate = (passed / total * 100) if total > 0 else 0

    # 計算 L1-L5 層級通過率
    l1_passed = sum(1 for r in _test_results if r.get("l1_passed", False))
    l2_passed = sum(1 for r in _test_results if r.get("l2_passed", False))
    l3_passed = sum(1 for r in _test_results if r.get("l3_passed", False))
    l4_passed = sum(1 for r in _test_results if r.get("l4_passed", False))
    l5_passed = sum(1 for r in _test_results if r.get("l5_passed", False))

    # 計算性能指標
    latencies = [r.get("latency_ms", 0) for r in _test_results if r.get("latency_ms")]
    avg_latency = sum(latencies) / len(latencies) if latencies else 0
    p95_latency = sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0

    report = {
        "execution_date": datetime.now().strftime("%Y-%m-%d"),
        "execution_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "executor": "Daniel Chung",
        "test_environment": "本地開發環境",
        "system_version": "v4.0",
        "summary": {
            "total_scenarios": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": f"{pass_rate:.2f}%",
            "l1_pass_rate": f"{(l1_passed / total * 100) if total > 0 else 0:.2f}%",
            "l2_pass_rate": f"{(l2_passed / total * 100) if total > 0 else 0:.2f}%",
            "l3_pass_rate": f"{(l3_passed / total * 100) if total > 0 else 0:.2f}%",
            "l4_pass_rate": f"{(l4_passed / total * 100) if total > 0 else 0:.2f}%",
            "l5_pass_rate": f"{(l5_passed / total * 100) if total > 0 else 0:.2f}%",
            "avg_latency_ms": f"{avg_latency:.2f}",
            "p95_latency_ms": f"{p95_latency:.2f}",
        },
        "results": _test_results,
    }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    return output_file


def save_xls_test_results() -> Path:
    """保存 xls-editor 測試結果到 JSON 文件"""
    global _xls_test_results

    output_dir = Path(__file__).parent / "test_reports"
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"xls_editor_v4_test_results_{timestamp}.json"

    total = len(_xls_test_results)
    passed = sum(1 for r in _xls_test_results if r.get("all_passed", False))
    failed = total - passed
    pass_rate = (passed / total * 100) if total > 0 else 0

    # 計算 L1-L5 層級通過率
    l1_passed = sum(1 for r in _xls_test_results if r.get("l1_passed", False))
    l2_passed = sum(1 for r in _xls_test_results if r.get("l2_passed", False))
    l3_passed = sum(1 for r in _xls_test_results if r.get("l3_passed", False))
    l4_passed = sum(1 for r in _xls_test_results if r.get("l4_passed", False))
    l5_passed = sum(1 for r in _xls_test_results if r.get("l5_passed", False))

    # 計算性能指標
    latencies = [r.get("latency_ms", 0) for r in _xls_test_results if r.get("latency_ms")]
    avg_latency = sum(latencies) / len(latencies) if latencies else 0
    p95_latency = sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0

    report = {
        "execution_date": datetime.now().strftime("%Y-%m-%d"),
        "execution_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "executor": "Daniel Chung",
        "test_environment": "本地開發環境",
        "system_version": "v4.0",
        "summary": {
            "total_scenarios": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": f"{pass_rate:.2f}%",
            "l1_pass_rate": f"{(l1_passed / total * 100) if total > 0 else 0:.2f}%",
            "l2_pass_rate": f"{(l2_passed / total * 100) if total > 0 else 0:.2f}%",
            "l3_pass_rate": f"{(l3_passed / total * 100) if total > 0 else 0:.2f}%",
            "l4_pass_rate": f"{(l4_passed / total * 100) if total > 0 else 0:.2f}%",
            "l5_pass_rate": f"{(l5_passed / total * 100) if total > 0 else 0:.2f}%",
            "avg_latency_ms": f"{avg_latency:.2f}",
            "p95_latency_ms": f"{p95_latency:.2f}",
        },
        "results": _xls_test_results,
    }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    return output_file


def save_md_to_pdf_test_results() -> Path:
    """保存 md-to-pdf 測試結果到 JSON 文件"""
    global _md_to_pdf_test_results

    output_dir = Path(__file__).parent / "test_reports"
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"md_to_pdf_v4_test_results_{timestamp}.json"

    total = len(_md_to_pdf_test_results)
    passed = sum(1 for r in _md_to_pdf_test_results if r.get("all_passed", False))
    failed = total - passed
    pass_rate = (passed / total * 100) if total > 0 else 0

    l1_passed = sum(1 for r in _md_to_pdf_test_results if r.get("l1_passed", False))
    l2_passed = sum(1 for r in _md_to_pdf_test_results if r.get("l2_passed", False))
    l3_passed = sum(1 for r in _md_to_pdf_test_results if r.get("l3_passed", False))
    l4_passed = sum(1 for r in _md_to_pdf_test_results if r.get("l4_passed", False))
    l5_passed = sum(1 for r in _md_to_pdf_test_results if r.get("l5_passed", False))

    latencies = [r.get("latency_ms", 0) for r in _md_to_pdf_test_results if r.get("latency_ms")]
    avg_latency = sum(latencies) / len(latencies) if latencies else 0
    p95_latency = sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0

    report = {
        "execution_date": datetime.now().strftime("%Y-%m-%d"),
        "execution_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "executor": "Daniel Chung",
        "test_environment": "本地開發環境",
        "system_version": "v4.0",
        "summary": {
            "total_scenarios": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": f"{pass_rate:.2f}%",
            "l1_pass_rate": f"{(l1_passed / total * 100) if total > 0 else 0:.2f}%",
            "l2_pass_rate": f"{(l2_passed / total * 100) if total > 0 else 0:.2f}%",
            "l3_pass_rate": f"{(l3_passed / total * 100) if total > 0 else 0:.2f}%",
            "l4_pass_rate": f"{(l4_passed / total * 100) if total > 0 else 0:.2f}%",
            "l5_pass_rate": f"{(l5_passed / total * 100) if total > 0 else 0:.2f}%",
            "avg_latency_ms": f"{avg_latency:.2f}",
            "p95_latency_ms": f"{p95_latency:.2f}",
        },
        "results": _md_to_pdf_test_results,
    }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    return output_file


def save_xls_to_pdf_test_results() -> Path:
    """保存 xls-to-pdf 測試結果到 JSON 文件"""
    global _xls_to_pdf_test_results

    output_dir = Path(__file__).parent / "test_reports"
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"xls_to_pdf_v4_test_results_{timestamp}.json"

    total = len(_xls_to_pdf_test_results)
    passed = sum(1 for r in _xls_to_pdf_test_results if r.get("all_passed", False))
    failed = total - passed
    pass_rate = (passed / total * 100) if total > 0 else 0

    l1_passed = sum(1 for r in _xls_to_pdf_test_results if r.get("l1_passed", False))
    l2_passed = sum(1 for r in _xls_to_pdf_test_results if r.get("l2_passed", False))
    l3_passed = sum(1 for r in _xls_to_pdf_test_results if r.get("l3_passed", False))
    l4_passed = sum(1 for r in _xls_to_pdf_test_results if r.get("l4_passed", False))
    l5_passed = sum(1 for r in _xls_to_pdf_test_results if r.get("l5_passed", False))

    latencies = [r.get("latency_ms", 0) for r in _xls_to_pdf_test_results if r.get("latency_ms")]
    avg_latency = sum(latencies) / len(latencies) if latencies else 0
    p95_latency = sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0

    report = {
        "execution_date": datetime.now().strftime("%Y-%m-%d"),
        "execution_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "executor": "Daniel Chung",
        "test_environment": "本地開發環境",
        "system_version": "v4.0",
        "summary": {
            "total_scenarios": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": f"{pass_rate:.2f}%",
            "l1_pass_rate": f"{(l1_passed / total * 100) if total > 0 else 0:.2f}%",
            "l2_pass_rate": f"{(l2_passed / total * 100) if total > 0 else 0:.2f}%",
            "l3_pass_rate": f"{(l3_passed / total * 100) if total > 0 else 0:.2f}%",
            "l4_pass_rate": f"{(l4_passed / total * 100) if total > 0 else 0:.2f}%",
            "l5_pass_rate": f"{(l5_passed / total * 100) if total > 0 else 0:.2f}%",
            "avg_latency_ms": f"{avg_latency:.2f}",
            "p95_latency_ms": f"{p95_latency:.2f}",
        },
        "results": _xls_to_pdf_test_results,
    }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    return output_file


def save_pdf_to_md_test_results() -> Path:
    """保存 pdf-to-md 測試結果到 JSON 文件"""
    global _pdf_to_md_test_results

    output_dir = Path(__file__).parent / "test_reports"
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"pdf_to_md_v4_test_results_{timestamp}.json"

    total = len(_pdf_to_md_test_results)
    passed = sum(1 for r in _pdf_to_md_test_results if r.get("all_passed", False))
    failed = total - passed
    pass_rate = (passed / total * 100) if total > 0 else 0

    l1_passed = sum(1 for r in _pdf_to_md_test_results if r.get("l1_passed", False))
    l2_passed = sum(1 for r in _pdf_to_md_test_results if r.get("l2_passed", False))
    l3_passed = sum(1 for r in _pdf_to_md_test_results if r.get("l3_passed", False))
    l4_passed = sum(1 for r in _pdf_to_md_test_results if r.get("l4_passed", False))
    l5_passed = sum(1 for r in _pdf_to_md_test_results if r.get("l5_passed", False))

    latencies = [r.get("latency_ms", 0) for r in _pdf_to_md_test_results if r.get("latency_ms")]
    avg_latency = sum(latencies) / len(latencies) if latencies else 0
    p95_latency = sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0

    report = {
        "execution_date": datetime.now().strftime("%Y-%m-%d"),
        "execution_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "executor": "Daniel Chung",
        "test_environment": "本地開發環境",
        "system_version": "v4.0",
        "summary": {
            "total_scenarios": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": f"{pass_rate:.2f}%",
            "l1_pass_rate": f"{(l1_passed / total * 100) if total > 0 else 0:.2f}%",
            "l2_pass_rate": f"{(l2_passed / total * 100) if total > 0 else 0:.2f}%",
            "l3_pass_rate": f"{(l3_passed / total * 100) if total > 0 else 0:.2f}%",
            "l4_pass_rate": f"{(l4_passed / total * 100) if total > 0 else 0:.2f}%",
            "l5_pass_rate": f"{(l5_passed / total * 100) if total > 0 else 0:.2f}%",
            "avg_latency_ms": f"{avg_latency:.2f}",
            "p95_latency_ms": f"{p95_latency:.2f}",
        },
        "results": _pdf_to_md_test_results,
    }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    return output_file


# pytest hook: 在所有測試完成後保存結果
def pytest_sessionfinish(session, exitstatus):
    """pytest 會話結束時保存測試結果"""
    global _test_results, _xls_test_results, _md_to_pdf_test_results, _xls_to_pdf_test_results, _pdf_to_md_test_results
    if _test_results:
        try:
            output_file = save_test_results()
            print(f"\n{'='*80}")
            print(f"md-editor 測試結果已保存至: {output_file}")
            print(f"{'='*80}\n")
        except Exception as e:
            print(f"\n保存 md-editor 測試結果時發生錯誤: {e}")
    if _xls_test_results:
        try:
            output_file = save_xls_test_results()
            print(f"\n{'='*80}")
            print(f"xls-editor 測試結果已保存至: {output_file}")
            print(f"{'='*80}\n")
        except Exception as e:
            print(f"\n保存 xls-editor 測試結果時發生錯誤: {e}")
    if _md_to_pdf_test_results:
        try:
            output_file = save_md_to_pdf_test_results()
            print(f"\n{'='*80}")
            print(f"md-to-pdf 測試結果已保存至: {output_file}")
            print(f"{'='*80}\n")
        except Exception as e:
            print(f"\n保存 md-to-pdf 測試結果時發生錯誤: {e}")
    if _xls_to_pdf_test_results:
        try:
            output_file = save_xls_to_pdf_test_results()
            print(f"\n{'='*80}")
            print(f"xls-to-pdf 測試結果已保存至: {output_file}")
            print(f"{'='*80}\n")
        except Exception as e:
            print(f"\n保存 xls-to-pdf 測試結果時發生錯誤: {e}")
    if _pdf_to_md_test_results:
        try:
            output_file = save_pdf_to_md_test_results()
            print(f"\n{'='*80}")
            print(f"pdf-to-md 測試結果已保存至: {output_file}")
            print(f"{'='*80}\n")
        except Exception as e:
            print(f"\n保存 pdf-to-md 測試結果時發生錯誤: {e}")


if __name__ == "__main__":
    import sys

    # 檢查命令行參數，決定運行哪個測試
    test_category = None
    if len(sys.argv) > 1:
        test_category = sys.argv[1]

    # 清空結果列表
    _test_results.clear()
    _xls_test_results.clear()
    _md_to_pdf_test_results.clear()

    # 運行測試
    if test_category == "xls-editor":
        # 只運行 xls-editor 測試
        exit_code = pytest.main([__file__, "-v", "--tb=short", "-s", "-k", "test_xls_editor_routing_v4"])
        test_results = _xls_test_results
        save_func = save_xls_test_results
        category_name = "xls-editor"
    elif test_category == "md-editor":
        # 只運行 md-editor 測試
        exit_code = pytest.main([__file__, "-v", "--tb=short", "-s", "-k", "test_md_editor_routing_v4"])
        test_results = _test_results
        save_func = save_test_results
        category_name = "md-editor"
    elif test_category == "md-to-pdf":
        # 只運行 md-to-pdf 測試
        exit_code = pytest.main([__file__, "-v", "--tb=short", "-s", "-k", "test_md_to_pdf_routing_v4"])
        test_results = _md_to_pdf_test_results
        save_func = save_md_to_pdf_test_results
        category_name = "md-to-pdf"
    else:
        # 運行所有測試
        exit_code = pytest.main([__file__, "-v", "--tb=short", "-s"])
        # 保存所有結果
        if _test_results:
            save_test_results()
        if _xls_test_results:
            save_xls_test_results()
        if _md_to_pdf_test_results:
            save_md_to_pdf_test_results()
        # 打印所有摘要
        if _test_results:
            total = len(_test_results)
            passed = sum(1 for r in _test_results if r.get("all_passed", False))
            print(f"\n{'='*80}")
            print("md-editor 測試摘要")
            print(f"{'='*80}")
            print(f"總場景數: {total}")
            print(f"通過: {passed}")
            print(f"失敗: {total - passed}")
            print(f"通過率: {(passed / total * 100) if total > 0 else 0:.2f}%")
        if _xls_test_results:
            total = len(_xls_test_results)
            passed = sum(1 for r in _xls_test_results if r.get("all_passed", False))
            print(f"\n{'='*80}")
            print("xls-editor 測試摘要")
            print(f"{'='*80}")
            print(f"總場景數: {total}")
            print(f"通過: {passed}")
            print(f"失敗: {total - passed}")
            print(f"通過率: {(passed / total * 100) if total > 0 else 0:.2f}%")
        if _md_to_pdf_test_results:
            total = len(_md_to_pdf_test_results)
            passed = sum(1 for r in _md_to_pdf_test_results if r.get("all_passed", False))
            print(f"\n{'='*80}")
            print("md-to-pdf 測試摘要")
            print(f"{'='*80}")
            print(f"總場景數: {total}")
            print(f"通過: {passed}")
            print(f"失敗: {total - passed}")
            print(f"通過率: {(passed / total * 100) if total > 0 else 0:.2f}%")
        sys.exit(exit_code)

    # 保存結果（單個類別測試）
    if test_results:
        output_file = save_func()
        print(f"\n{category_name} 測試結果已保存至: {output_file}")

        # 打印摘要
        total = len(test_results)
        passed = sum(1 for r in test_results if r.get("all_passed", False))
        failed = total - passed
        pass_rate = (passed / total * 100) if total > 0 else 0

        l1_passed = sum(1 for r in test_results if r.get("l1_passed", False))
        l2_passed = sum(1 for r in test_results if r.get("l2_passed", False))
        l3_passed = sum(1 for r in test_results if r.get("l3_passed", False))
        l4_passed = sum(1 for r in test_results if r.get("l4_passed", False))
        l5_passed = sum(1 for r in test_results if r.get("l5_passed", False))

        latencies = [r.get("latency_ms", 0) for r in test_results if r.get("latency_ms")]
        avg_latency = sum(latencies) / len(latencies) if latencies else 0
        p95_latency = sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0

        print(f"\n{'='*80}")
        print(f"{category_name} 測試摘要")
        print(f"{'='*80}")
        print(f"總場景數: {total}")
        print(f"通過: {passed}")
        print(f"失敗: {failed}")
        print(f"通過率: {pass_rate:.2f}%")
        print(f"\nL1-L5 層級通過率:")
        print(f"  L1 語義理解: {(l1_passed / total * 100) if total > 0 else 0:.2f}% ({l1_passed}/{total})")
        print(f"  L2 Intent DSL: {(l2_passed / total * 100) if total > 0 else 0:.2f}% ({l2_passed}/{total})")
        print(f"  L3 Capability: {(l3_passed / total * 100) if total > 0 else 0:.2f}% ({l3_passed}/{total})")
        print(f"  L4 Policy: {(l4_passed / total * 100) if total > 0 else 0:.2f}% ({l4_passed}/{total})")
        print(f"  L5 執行記錄: {(l5_passed / total * 100) if total > 0 else 0:.2f}% ({l5_passed}/{total})")
        print(f"\n性能指標:")
        print(f"  平均響應時間: {avg_latency:.2f}ms")
        print(f"  P95 響應時間: {p95_latency:.2f}ms")
        print(f"{'='*80}\n")

    sys.exit(exit_code)
