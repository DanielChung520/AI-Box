# 代碼功能說明: 文件編輯 Agent 語義路由測試腳本
# 創建日期: 2026-01-11
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-11

"""文件編輯 Agent 語義路由測試腳本

測試 5 類 Agent 的語義路由能力：
1. md-editor（Markdown 編輯器）- 20 個場景
2. xls-editor（Excel 編輯器）- 20 個場景
3. md-to-pdf（Markdown 轉 PDF）- 20 個場景
4. xls-to-pdf（Excel 轉 PDF）- 20 個場景
5. pdf-to-md（PDF 轉 Markdown）- 20 個場景

驗證系統是否能根據語義正確調用不同的 Agent。
完整場景定義請參考：docs/系统设计文档/核心组件/Agent平台/archive/testing/文件編輯Agent語義路由測試劇本-v2.md
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

from agents.services.orchestrator.orchestrator import AgentOrchestrator
from agents.task_analyzer.models import TaskAnalysisRequest

# 測試結果收集器（用於收集測試結果）
_test_results: List[Dict[str, Any]] = []
_test_results_file: Optional[Path] = None

# Agent ID 定義
MD_EDITOR_AGENT_ID = "md-editor"
XLS_EDITOR_AGENT_ID = "xls-editor"
MD_TO_PDF_AGENT_ID = "md-to-pdf"
XLS_TO_PDF_AGENT_ID = "xls-to-pdf"
PDF_TO_MD_AGENT_ID = "pdf-to-md"

# 測試場景定義（100 個場景）
TEST_SCENARIOS = [
    # 類別 1：md-editor（Markdown 編輯器）- 20 個場景
    {
        "scenario_id": "MD-001",
        "category": "md-editor",
        "user_input": "編輯文件 README.md",
        "expected_task_type": "execution",
        "expected_agent": MD_EDITOR_AGENT_ID,
        "complexity": "簡單",
    },
    {
        "scenario_id": "MD-002",
        "category": "md-editor",
        "user_input": "修改 docs/guide.md 文件中的第一章節",
        "expected_task_type": "execution",
        "expected_agent": MD_EDITOR_AGENT_ID,
        "complexity": "中等",
    },
    {
        "scenario_id": "MD-003",
        "category": "md-editor",
        "user_input": "在 README.md 中添加安裝說明",
        "expected_task_type": "execution",
        "expected_agent": MD_EDITOR_AGENT_ID,
        "complexity": "中等",
    },
    {
        "scenario_id": "MD-004",
        "category": "md-editor",
        "user_input": "更新 CHANGELOG.md 文件",
        "expected_task_type": "execution",
        "expected_agent": MD_EDITOR_AGENT_ID,
        "complexity": "簡單",
    },
    {
        "scenario_id": "MD-005",
        "category": "md-editor",
        "user_input": "刪除 docs/api.md 中的過時文檔",
        "expected_task_type": "execution",
        "expected_agent": MD_EDITOR_AGENT_ID,
        "complexity": "中等",
    },
    {
        "scenario_id": "MD-006",
        "category": "md-editor",
        "user_input": "將 README.md 中的 '舊版本' 替換為 '新版本'",
        "expected_task_type": "execution",
        "expected_agent": MD_EDITOR_AGENT_ID,
        "complexity": "中等",
    },
    {
        "scenario_id": "MD-007",
        "category": "md-editor",
        "user_input": "重寫 docs/guide.md 中的使用說明章節",
        "expected_task_type": "execution",
        "expected_agent": MD_EDITOR_AGENT_ID,
        "complexity": "中等",
    },
    {
        "scenario_id": "MD-008",
        "category": "md-editor",
        "user_input": "在 README.md 的開頭插入版本信息",
        "expected_task_type": "execution",
        "expected_agent": MD_EDITOR_AGENT_ID,
        "complexity": "中等",
    },
    {
        "scenario_id": "MD-009",
        "category": "md-editor",
        "user_input": "格式化整個 README.md 文件",
        "expected_task_type": "execution",
        "expected_agent": MD_EDITOR_AGENT_ID,
        "complexity": "簡單",
    },
    {
        "scenario_id": "MD-010",
        "category": "md-editor",
        "user_input": "整理 docs/guide.md 的章節結構",
        "expected_task_type": "execution",
        "expected_agent": MD_EDITOR_AGENT_ID,
        "complexity": "中等",
    },
    {
        "scenario_id": "MD-011",
        "category": "md-editor",
        "user_input": "創建一個新的 Markdown 文件 CONTRIBUTING.md",
        "expected_task_type": "execution",
        "expected_agent": MD_EDITOR_AGENT_ID,
        "complexity": "簡單",
    },
    {
        "scenario_id": "MD-012",
        "category": "md-editor",
        "user_input": "幫我產生一份 API 文檔 api.md",
        "expected_task_type": "execution",
        "expected_agent": MD_EDITOR_AGENT_ID,
        "complexity": "中等",
    },
    {
        "scenario_id": "MD-013",
        "category": "md-editor",
        "user_input": "在 README.md 中添加功能對照表",
        "expected_task_type": "execution",
        "expected_agent": MD_EDITOR_AGENT_ID,
        "complexity": "中等",
    },
    {
        "scenario_id": "MD-014",
        "category": "md-editor",
        "user_input": "更新 docs/links.md 中的所有外部鏈接",
        "expected_task_type": "execution",
        "expected_agent": MD_EDITOR_AGENT_ID,
        "complexity": "中等",
    },
    {
        "scenario_id": "MD-015",
        "category": "md-editor",
        "user_input": "在 README.md 中添加安裝代碼示例",
        "expected_task_type": "execution",
        "expected_agent": MD_EDITOR_AGENT_ID,
        "complexity": "中等",
    },
    {
        "scenario_id": "MD-016",
        "category": "md-editor",
        "user_input": "將 docs/guide.md 的主標題改為 '用戶指南'",
        "expected_task_type": "execution",
        "expected_agent": MD_EDITOR_AGENT_ID,
        "complexity": "簡單",
    },
    {
        "scenario_id": "MD-017",
        "category": "md-editor",
        "user_input": "在 README.md 中添加項目截圖",
        "expected_task_type": "execution",
        "expected_agent": MD_EDITOR_AGENT_ID,
        "complexity": "中等",
    },
    {
        "scenario_id": "MD-018",
        "category": "md-editor",
        "user_input": "優化 docs/api.md 的 Markdown 格式",
        "expected_task_type": "execution",
        "expected_agent": MD_EDITOR_AGENT_ID,
        "complexity": "中等",
    },
    {
        "scenario_id": "MD-019",
        "category": "md-editor",
        "user_input": "在 README.md 開頭添加目錄",
        "expected_task_type": "execution",
        "expected_agent": MD_EDITOR_AGENT_ID,
        "complexity": "中等",
    },
    {
        "scenario_id": "MD-020",
        "category": "md-editor",
        "user_input": "重組 docs/guide.md 的內容結構",
        "expected_task_type": "execution",
        "expected_agent": MD_EDITOR_AGENT_ID,
        "complexity": "複雜",
    },
    # 類別 2：xls-editor（Excel 編輯器）- 20 個場景
    {
        "scenario_id": "XLS-001",
        "category": "xls-editor",
        "user_input": "編輯文件 data.xlsx",
        "expected_task_type": "execution",
        "expected_agent": XLS_EDITOR_AGENT_ID,
        "complexity": "簡單",
    },
    {
        "scenario_id": "XLS-002",
        "category": "xls-editor",
        "user_input": "修改 data.xlsx 中 Sheet1 的 A1 單元格值為 100",
        "expected_task_type": "execution",
        "expected_agent": XLS_EDITOR_AGENT_ID,
        "complexity": "簡單",
    },
    {
        "scenario_id": "XLS-003",
        "category": "xls-editor",
        "user_input": "在 data.xlsx 的 Sheet1 中添加一行數據",
        "expected_task_type": "execution",
        "expected_agent": XLS_EDITOR_AGENT_ID,
        "complexity": "中等",
    },
    {
        "scenario_id": "XLS-004",
        "category": "xls-editor",
        "user_input": "更新 data.xlsx 中 B10 單元格的公式為 =SUM(A1:A9)",
        "expected_task_type": "execution",
        "expected_agent": XLS_EDITOR_AGENT_ID,
        "complexity": "中等",
    },
    {
        "scenario_id": "XLS-005",
        "category": "xls-editor",
        "user_input": "刪除 data.xlsx 中 Sheet1 的第 5 行",
        "expected_task_type": "execution",
        "expected_agent": XLS_EDITOR_AGENT_ID,
        "complexity": "簡單",
    },
    {
        "scenario_id": "XLS-006",
        "category": "xls-editor",
        "user_input": "在 data.xlsx 的 Sheet1 中 B 列前插入一列",
        "expected_task_type": "execution",
        "expected_agent": XLS_EDITOR_AGENT_ID,
        "complexity": "中等",
    },
    {
        "scenario_id": "XLS-007",
        "category": "xls-editor",
        "user_input": "將 data.xlsx 中 A1 單元格設置為粗體和紅色",
        "expected_task_type": "execution",
        "expected_agent": XLS_EDITOR_AGENT_ID,
        "complexity": "中等",
    },
    {
        "scenario_id": "XLS-008",
        "category": "xls-editor",
        "user_input": "在 data.xlsx 的 Sheet1 中填充 A1 到 A10 的序號",
        "expected_task_type": "execution",
        "expected_agent": XLS_EDITOR_AGENT_ID,
        "complexity": "中等",
    },
    {
        "scenario_id": "XLS-009",
        "category": "xls-editor",
        "user_input": "在 data.xlsx 中創建一個新的工作表 '統計'",
        "expected_task_type": "execution",
        "expected_agent": XLS_EDITOR_AGENT_ID,
        "complexity": "簡單",
    },
    {
        "scenario_id": "XLS-010",
        "category": "xls-editor",
        "user_input": "將 data.xlsx 中的 Sheet1 重命名為 '數據'",
        "expected_task_type": "execution",
        "expected_agent": XLS_EDITOR_AGENT_ID,
        "complexity": "簡單",
    },
    {
        "scenario_id": "XLS-011",
        "category": "xls-editor",
        "user_input": "將 data.xlsx 中 C 列的格式設置為貨幣格式",
        "expected_task_type": "execution",
        "expected_agent": XLS_EDITOR_AGENT_ID,
        "complexity": "中等",
    },
    {
        "scenario_id": "XLS-012",
        "category": "xls-editor",
        "user_input": "在 data.xlsx 的 Sheet1 中為 A 列添加下拉列表驗證",
        "expected_task_type": "execution",
        "expected_agent": XLS_EDITOR_AGENT_ID,
        "complexity": "複雜",
    },
    {
        "scenario_id": "XLS-013",
        "category": "xls-editor",
        "user_input": "將 data.xlsx 中 A1 到 C1 的單元格合併",
        "expected_task_type": "execution",
        "expected_agent": XLS_EDITOR_AGENT_ID,
        "complexity": "簡單",
    },
    {
        "scenario_id": "XLS-014",
        "category": "xls-editor",
        "user_input": "將 data.xlsx 中 A 列的寬度設置為 20",
        "expected_task_type": "execution",
        "expected_agent": XLS_EDITOR_AGENT_ID,
        "complexity": "簡單",
    },
    {
        "scenario_id": "XLS-015",
        "category": "xls-editor",
        "user_input": "在 data.xlsx 的 Sheet1 中凍結第一行",
        "expected_task_type": "execution",
        "expected_agent": XLS_EDITOR_AGENT_ID,
        "complexity": "中等",
    },
    {
        "scenario_id": "XLS-016",
        "category": "xls-editor",
        "user_input": "在 data.xlsx 的 Sheet1 中為第一行添加自動篩選",
        "expected_task_type": "execution",
        "expected_agent": XLS_EDITOR_AGENT_ID,
        "complexity": "中等",
    },
    {
        "scenario_id": "XLS-017",
        "category": "xls-editor",
        "user_input": "在 data.xlsx 中複製 Sheet1 並命名為 '備份'",
        "expected_task_type": "execution",
        "expected_agent": XLS_EDITOR_AGENT_ID,
        "complexity": "中等",
    },
    {
        "scenario_id": "XLS-018",
        "category": "xls-editor",
        "user_input": "刪除 data.xlsx 中的 Sheet2 工作表",
        "expected_task_type": "execution",
        "expected_agent": XLS_EDITOR_AGENT_ID,
        "complexity": "簡單",
    },
    {
        "scenario_id": "XLS-019",
        "category": "xls-editor",
        "user_input": "將 data.xlsx 中 Sheet1 的打印區域設置為 A1:Z100",
        "expected_task_type": "execution",
        "expected_agent": XLS_EDITOR_AGENT_ID,
        "complexity": "中等",
    },
    {
        "scenario_id": "XLS-020",
        "category": "xls-editor",
        "user_input": "創建一個新的 Excel 文件 report.xlsx",
        "expected_task_type": "execution",
        "expected_agent": XLS_EDITOR_AGENT_ID,
        "complexity": "簡單",
    },
    # 類別 3：md-to-pdf（Markdown 轉 PDF）- 20 個場景
    {
        "scenario_id": "MD2PDF-001",
        "category": "md-to-pdf",
        "user_input": "將 README.md 轉換為 PDF",
        "expected_task_type": "execution",
        "expected_agent": MD_TO_PDF_AGENT_ID,
        "complexity": "簡單",
    },
    {
        "scenario_id": "MD2PDF-002",
        "category": "md-to-pdf",
        "user_input": "幫我把 docs/guide.md 轉成 PDF 文件",
        "expected_task_type": "execution",
        "expected_agent": MD_TO_PDF_AGENT_ID,
        "complexity": "簡單",
    },
    {
        "scenario_id": "MD2PDF-003",
        "category": "md-to-pdf",
        "user_input": "生成 README.md 的 PDF 版本",
        "expected_task_type": "execution",
        "expected_agent": MD_TO_PDF_AGENT_ID,
        "complexity": "簡單",
    },
    {
        "scenario_id": "MD2PDF-004",
        "category": "md-to-pdf",
        "user_input": "將 docs/api.md 導出為 PDF 文件",
        "expected_task_type": "execution",
        "expected_agent": MD_TO_PDF_AGENT_ID,
        "complexity": "簡單",
    },
    {
        "scenario_id": "MD2PDF-005",
        "category": "md-to-pdf",
        "user_input": "將 CHANGELOG.md 轉換為 PDF 文檔",
        "expected_task_type": "execution",
        "expected_agent": MD_TO_PDF_AGENT_ID,
        "complexity": "簡單",
    },
    {
        "scenario_id": "MD2PDF-006",
        "category": "md-to-pdf",
        "user_input": "把 README.md 製作成 PDF 文件",
        "expected_task_type": "execution",
        "expected_agent": MD_TO_PDF_AGENT_ID,
        "complexity": "簡單",
    },
    {
        "scenario_id": "MD2PDF-007",
        "category": "md-to-pdf",
        "user_input": "將 docs/guide.md 轉為 PDF，頁面大小設為 A4",
        "expected_task_type": "execution",
        "expected_agent": MD_TO_PDF_AGENT_ID,
        "complexity": "中等",
    },
    {
        "scenario_id": "MD2PDF-008",
        "category": "md-to-pdf",
        "user_input": "將 README.md 轉為 PDF，並添加頁眉和頁腳",
        "expected_task_type": "execution",
        "expected_agent": MD_TO_PDF_AGENT_ID,
        "complexity": "中等",
    },
    {
        "scenario_id": "MD2PDF-009",
        "category": "md-to-pdf",
        "user_input": "將 docs/guide.md 轉為 PDF，並自動生成目錄",
        "expected_task_type": "execution",
        "expected_agent": MD_TO_PDF_AGENT_ID,
        "complexity": "中等",
    },
    {
        "scenario_id": "MD2PDF-010",
        "category": "md-to-pdf",
        "user_input": "將 README.md 轉為 PDF，使用學術模板",
        "expected_task_type": "execution",
        "expected_agent": MD_TO_PDF_AGENT_ID,
        "complexity": "中等",
    },
    {
        "scenario_id": "MD2PDF-011",
        "category": "md-to-pdf",
        "user_input": "將 docs/ 目錄下的所有 Markdown 文件合併轉為一個 PDF",
        "expected_task_type": "execution",
        "expected_agent": MD_TO_PDF_AGENT_ID,
        "complexity": "複雜",
    },
    {
        "scenario_id": "MD2PDF-012",
        "category": "md-to-pdf",
        "user_input": "將 README.md 轉為 PDF，字體設為 Times New Roman",
        "expected_task_type": "execution",
        "expected_agent": MD_TO_PDF_AGENT_ID,
        "complexity": "中等",
    },
    {
        "scenario_id": "MD2PDF-013",
        "category": "md-to-pdf",
        "user_input": "將 docs/guide.md 轉為 PDF，邊距設為 2cm",
        "expected_task_type": "execution",
        "expected_agent": MD_TO_PDF_AGENT_ID,
        "complexity": "中等",
    },
    {
        "scenario_id": "MD2PDF-014",
        "category": "md-to-pdf",
        "user_input": "將 README.md 轉為 PDF，並啟用代碼高亮",
        "expected_task_type": "execution",
        "expected_agent": MD_TO_PDF_AGENT_ID,
        "complexity": "中等",
    },
    {
        "scenario_id": "MD2PDF-015",
        "category": "md-to-pdf",
        "user_input": "將 docs/guide.md 轉為 PDF，並渲染 Mermaid 圖表",
        "expected_task_type": "execution",
        "expected_agent": MD_TO_PDF_AGENT_ID,
        "complexity": "中等",
    },
    {
        "scenario_id": "MD2PDF-016",
        "category": "md-to-pdf",
        "user_input": "將 README.md 轉為 PDF，並添加頁碼",
        "expected_task_type": "execution",
        "expected_agent": MD_TO_PDF_AGENT_ID,
        "complexity": "簡單",
    },
    {
        "scenario_id": "MD2PDF-017",
        "category": "md-to-pdf",
        "user_input": "將 docs/guide.md 轉為 PDF，並添加封面頁",
        "expected_task_type": "execution",
        "expected_agent": MD_TO_PDF_AGENT_ID,
        "complexity": "中等",
    },
    {
        "scenario_id": "MD2PDF-018",
        "category": "md-to-pdf",
        "user_input": "將 README.md 轉為 PDF，並添加水印 '草稿'",
        "expected_task_type": "execution",
        "expected_agent": MD_TO_PDF_AGENT_ID,
        "complexity": "複雜",
    },
    {
        "scenario_id": "MD2PDF-019",
        "category": "md-to-pdf",
        "user_input": "將 docs/guide.md 轉為 PDF，使用雙欄布局",
        "expected_task_type": "execution",
        "expected_agent": MD_TO_PDF_AGENT_ID,
        "complexity": "複雜",
    },
    {
        "scenario_id": "MD2PDF-020",
        "category": "md-to-pdf",
        "user_input": "將 README.md 轉為 PDF，頁面方向設為橫向",
        "expected_task_type": "execution",
        "expected_agent": MD_TO_PDF_AGENT_ID,
        "complexity": "中等",
    },
    # 類別 4：xls-to-pdf（Excel 轉 PDF）- 20 個場景
    {
        "scenario_id": "XLS2PDF-001",
        "category": "xls-to-pdf",
        "user_input": "將 data.xlsx 轉換為 PDF",
        "expected_task_type": "execution",
        "expected_agent": XLS_TO_PDF_AGENT_ID,
        "complexity": "簡單",
    },
    {
        "scenario_id": "XLS2PDF-002",
        "category": "xls-to-pdf",
        "user_input": "幫我把 report.xlsx 轉成 PDF 文件",
        "expected_task_type": "execution",
        "expected_agent": XLS_TO_PDF_AGENT_ID,
        "complexity": "簡單",
    },
    {
        "scenario_id": "XLS2PDF-003",
        "category": "xls-to-pdf",
        "user_input": "生成 data.xlsx 的 PDF 版本",
        "expected_task_type": "execution",
        "expected_agent": XLS_TO_PDF_AGENT_ID,
        "complexity": "簡單",
    },
    {
        "scenario_id": "XLS2PDF-004",
        "category": "xls-to-pdf",
        "user_input": "將 report.xlsx 導出為 PDF 文件",
        "expected_task_type": "execution",
        "expected_agent": XLS_TO_PDF_AGENT_ID,
        "complexity": "簡單",
    },
    {
        "scenario_id": "XLS2PDF-005",
        "category": "xls-to-pdf",
        "user_input": "將 data.xlsx 轉換為 PDF 文檔",
        "expected_task_type": "execution",
        "expected_agent": XLS_TO_PDF_AGENT_ID,
        "complexity": "簡單",
    },
    {
        "scenario_id": "XLS2PDF-006",
        "category": "xls-to-pdf",
        "user_input": "把 report.xlsx 製作成 PDF 文件",
        "expected_task_type": "execution",
        "expected_agent": XLS_TO_PDF_AGENT_ID,
        "complexity": "簡單",
    },
    {
        "scenario_id": "XLS2PDF-007",
        "category": "xls-to-pdf",
        "user_input": "將 data.xlsx 轉為 PDF，頁面大小設為 A4",
        "expected_task_type": "execution",
        "expected_agent": XLS_TO_PDF_AGENT_ID,
        "complexity": "中等",
    },
    {
        "scenario_id": "XLS2PDF-008",
        "category": "xls-to-pdf",
        "user_input": "將 report.xlsx 轉為 PDF，頁面方向設為橫向",
        "expected_task_type": "execution",
        "expected_agent": XLS_TO_PDF_AGENT_ID,
        "complexity": "中等",
    },
    {
        "scenario_id": "XLS2PDF-009",
        "category": "xls-to-pdf",
        "user_input": "將 data.xlsx 轉為 PDF，縮放設為適合頁面",
        "expected_task_type": "execution",
        "expected_agent": XLS_TO_PDF_AGENT_ID,
        "complexity": "中等",
    },
    {
        "scenario_id": "XLS2PDF-010",
        "category": "xls-to-pdf",
        "user_input": "將 report.xlsx 轉為 PDF，邊距設為 1cm",
        "expected_task_type": "execution",
        "expected_agent": XLS_TO_PDF_AGENT_ID,
        "complexity": "中等",
    },
    {
        "scenario_id": "XLS2PDF-011",
        "category": "xls-to-pdf",
        "user_input": "將 data.xlsx 轉為 PDF，打印區域設為 A1:Z100",
        "expected_task_type": "execution",
        "expected_agent": XLS_TO_PDF_AGENT_ID,
        "complexity": "中等",
    },
    {
        "scenario_id": "XLS2PDF-012",
        "category": "xls-to-pdf",
        "user_input": "將 report.xlsx 轉為 PDF，並顯示網格線",
        "expected_task_type": "execution",
        "expected_agent": XLS_TO_PDF_AGENT_ID,
        "complexity": "簡單",
    },
    {
        "scenario_id": "XLS2PDF-013",
        "category": "xls-to-pdf",
        "user_input": "將 data.xlsx 轉為 PDF，並顯示行列標題",
        "expected_task_type": "execution",
        "expected_agent": XLS_TO_PDF_AGENT_ID,
        "complexity": "簡單",
    },
    {
        "scenario_id": "XLS2PDF-014",
        "category": "xls-to-pdf",
        "user_input": "將 report.xlsx 轉為 PDF，並添加頁眉和頁腳",
        "expected_task_type": "execution",
        "expected_agent": XLS_TO_PDF_AGENT_ID,
        "complexity": "中等",
    },
    {
        "scenario_id": "XLS2PDF-015",
        "category": "xls-to-pdf",
        "user_input": "將 data.xlsx 的所有工作表轉為一個 PDF",
        "expected_task_type": "execution",
        "expected_agent": XLS_TO_PDF_AGENT_ID,
        "complexity": "中等",
    },
    {
        "scenario_id": "XLS2PDF-016",
        "category": "xls-to-pdf",
        "user_input": "將 data.xlsx 的 Sheet1 工作表轉為 PDF",
        "expected_task_type": "execution",
        "expected_agent": XLS_TO_PDF_AGENT_ID,
        "complexity": "簡單",
    },
    {
        "scenario_id": "XLS2PDF-017",
        "category": "xls-to-pdf",
        "user_input": "將 report.xlsx 轉為 PDF，並保留所有圖表",
        "expected_task_type": "execution",
        "expected_agent": XLS_TO_PDF_AGENT_ID,
        "complexity": "中等",
    },
    {
        "scenario_id": "XLS2PDF-018",
        "category": "xls-to-pdf",
        "user_input": "將 data.xlsx 轉為 PDF，質量設為高質量",
        "expected_task_type": "execution",
        "expected_agent": XLS_TO_PDF_AGENT_ID,
        "complexity": "中等",
    },
    {
        "scenario_id": "XLS2PDF-019",
        "category": "xls-to-pdf",
        "user_input": "將 report.xlsx 轉為 PDF，使用彩色模式",
        "expected_task_type": "execution",
        "expected_agent": XLS_TO_PDF_AGENT_ID,
        "complexity": "簡單",
    },
    {
        "scenario_id": "XLS2PDF-020",
        "category": "xls-to-pdf",
        "user_input": "將 data.xlsx 轉為 PDF，每個工作表分頁",
        "expected_task_type": "execution",
        "expected_agent": XLS_TO_PDF_AGENT_ID,
        "complexity": "中等",
    },
    # 類別 5：pdf-to-md（PDF 轉 Markdown）- 20 個場景
    {
        "scenario_id": "PDF2MD-001",
        "category": "pdf-to-md",
        "user_input": "將 document.pdf 轉換為 Markdown",
        "expected_task_type": "execution",
        "expected_agent": PDF_TO_MD_AGENT_ID,
        "complexity": "簡單",
    },
    {
        "scenario_id": "PDF2MD-002",
        "category": "pdf-to-md",
        "user_input": "幫我把 report.pdf 轉成 Markdown 文件",
        "expected_task_type": "execution",
        "expected_agent": PDF_TO_MD_AGENT_ID,
        "complexity": "簡單",
    },
    {
        "scenario_id": "PDF2MD-003",
        "category": "pdf-to-md",
        "user_input": "生成 document.pdf 的 Markdown 版本",
        "expected_task_type": "execution",
        "expected_agent": PDF_TO_MD_AGENT_ID,
        "complexity": "簡單",
    },
    {
        "scenario_id": "PDF2MD-004",
        "category": "pdf-to-md",
        "user_input": "將 report.pdf 導出為 Markdown 文件",
        "expected_task_type": "execution",
        "expected_agent": PDF_TO_MD_AGENT_ID,
        "complexity": "簡單",
    },
    {
        "scenario_id": "PDF2MD-005",
        "category": "pdf-to-md",
        "user_input": "將 document.pdf 轉換為 Markdown 文檔",
        "expected_task_type": "execution",
        "expected_agent": PDF_TO_MD_AGENT_ID,
        "complexity": "簡單",
    },
    {
        "scenario_id": "PDF2MD-006",
        "category": "pdf-to-md",
        "user_input": "把 report.pdf 提取為 Markdown 文件",
        "expected_task_type": "execution",
        "expected_agent": PDF_TO_MD_AGENT_ID,
        "complexity": "簡單",
    },
    {
        "scenario_id": "PDF2MD-007",
        "category": "pdf-to-md",
        "user_input": "將 document.pdf 轉為 Markdown，並識別表格",
        "expected_task_type": "execution",
        "expected_agent": PDF_TO_MD_AGENT_ID,
        "complexity": "中等",
    },
    {
        "scenario_id": "PDF2MD-008",
        "category": "pdf-to-md",
        "user_input": "將 report.pdf 轉為 Markdown，並提取所有圖片",
        "expected_task_type": "execution",
        "expected_agent": PDF_TO_MD_AGENT_ID,
        "complexity": "中等",
    },
    {
        "scenario_id": "PDF2MD-009",
        "category": "pdf-to-md",
        "user_input": "將 document.pdf 轉為 Markdown，並自動識別標題結構",
        "expected_task_type": "execution",
        "expected_agent": PDF_TO_MD_AGENT_ID,
        "complexity": "中等",
    },
    {
        "scenario_id": "PDF2MD-010",
        "category": "pdf-to-md",
        "user_input": "將 report.pdf 轉為 Markdown，並識別列表結構",
        "expected_task_type": "execution",
        "expected_agent": PDF_TO_MD_AGENT_ID,
        "complexity": "中等",
    },
    {
        "scenario_id": "PDF2MD-011",
        "category": "pdf-to-md",
        "user_input": "將 document.pdf 轉為 Markdown，使用 OCR 識別文字",
        "expected_task_type": "execution",
        "expected_agent": PDF_TO_MD_AGENT_ID,
        "complexity": "複雜",
    },
    {
        "scenario_id": "PDF2MD-012",
        "category": "pdf-to-md",
        "user_input": "將 report.pdf 轉為 Markdown，並保留原始格式",
        "expected_task_type": "execution",
        "expected_agent": PDF_TO_MD_AGENT_ID,
        "complexity": "中等",
    },
    {
        "scenario_id": "PDF2MD-013",
        "category": "pdf-to-md",
        "user_input": "將 document.pdf 轉為 Markdown，並識別頁面布局",
        "expected_task_type": "execution",
        "expected_agent": PDF_TO_MD_AGENT_ID,
        "complexity": "複雜",
    },
    {
        "scenario_id": "PDF2MD-014",
        "category": "pdf-to-md",
        "user_input": "將 report.pdf 轉為 Markdown，並提取文檔元數據",
        "expected_task_type": "execution",
        "expected_agent": PDF_TO_MD_AGENT_ID,
        "complexity": "中等",
    },
    {
        "scenario_id": "PDF2MD-015",
        "category": "pdf-to-md",
        "user_input": "將 document.pdf 轉為 Markdown，並識別代碼塊",
        "expected_task_type": "execution",
        "expected_agent": PDF_TO_MD_AGENT_ID,
        "complexity": "中等",
    },
    {
        "scenario_id": "PDF2MD-016",
        "category": "pdf-to-md",
        "user_input": "將 report.pdf 轉為 Markdown，並識別所有鏈接",
        "expected_task_type": "execution",
        "expected_agent": PDF_TO_MD_AGENT_ID,
        "complexity": "中等",
    },
    {
        "scenario_id": "PDF2MD-017",
        "category": "pdf-to-md",
        "user_input": "將 document.pdf 轉為 Markdown，OCR 語言設為中文和英文",
        "expected_task_type": "execution",
        "expected_agent": PDF_TO_MD_AGENT_ID,
        "complexity": "中等",
    },
    {
        "scenario_id": "PDF2MD-018",
        "category": "pdf-to-md",
        "user_input": "將 report.pdf 的第 1 到 10 頁轉為 Markdown",
        "expected_task_type": "execution",
        "expected_agent": PDF_TO_MD_AGENT_ID,
        "complexity": "中等",
    },
    {
        "scenario_id": "PDF2MD-019",
        "category": "pdf-to-md",
        "user_input": "將 document.pdf 轉為 Markdown，並識別數學公式",
        "expected_task_type": "execution",
        "expected_agent": PDF_TO_MD_AGENT_ID,
        "complexity": "複雜",
    },
    {
        "scenario_id": "PDF2MD-020",
        "category": "pdf-to-md",
        "user_input": "將 report.pdf 轉為 Markdown，並識別多欄布局",
        "expected_task_type": "execution",
        "expected_agent": PDF_TO_MD_AGENT_ID,
        "complexity": "複雜",
    },
]


class TestFileEditingAgentRouting:
    """文件編輯 Agent 語義路由測試類"""

    @pytest.fixture(scope="session", autouse=True)
    def setup_test_results_collection(self):
        """設置測試結果收集（測試會話開始時）"""
        global _test_results, _test_results_file

        # 清空結果列表
        _test_results.clear()

        # 設置結果文件路徑
        output_dir = Path(__file__).parent / "test_reports"
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        _test_results_file = output_dir / f"test_results_{timestamp}.json"

        yield

        # 測試會話結束時保存結果
        if _test_results:
            try:
                output_file = save_test_results(_test_results_file)
                print(f"\n{'='*80}")
                print(f"測試結果已保存至: {output_file}")
                print(f"總場景數: {len(_test_results)}")
                passed = sum(1 for r in _test_results if r.get("all_passed", False))
                failed = len(_test_results) - passed
                print(f"通過: {passed}, 失敗: {failed}")
                print(f"{'='*80}\n")
            except Exception as e:
                print(f"警告：保存測試結果失敗: {e}")

    @pytest.fixture
    def orchestrator(self):
        """創建 Orchestrator 實例"""
        return AgentOrchestrator()

    @pytest.mark.asyncio
    @pytest.mark.parametrize("scenario", TEST_SCENARIOS)
    async def test_agent_routing(self, orchestrator, scenario):
        """測試 Agent 語義路由"""
        global _test_results, _test_results_file

        scenario_id = scenario["scenario_id"]
        user_input = scenario["user_input"]
        expected_task_type = scenario.get("expected_task_type")
        expected_agent = scenario.get("expected_agent")
        complexity = scenario.get("complexity", "未知")

        print(f"\n{'='*80}")
        print(f"測試場景: {scenario_id}")
        print(f"類別: {scenario['category']}")
        print(f"複雜度: {complexity}")
        print(f"用戶輸入: {user_input}")
        print(f"預期 Agent: {expected_agent}")
        print(f"{'='*80}")

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
                else:
                    print("\n[Agent 註冊] 已註冊內建 Agent（返回 None）")
            except Exception as e:
                print(f"\n[Agent 註冊警告] 註冊內建 Agent 時發生錯誤: {e}")
                import traceback

                traceback.print_exc()

            analysis_request = TaskAnalysisRequest(task=user_input)
            task_analyzer = orchestrator._get_task_analyzer()
            analysis_result = await task_analyzer.analyze(analysis_request)

            print("\n[意圖解析結果]")
            print(f"  任務類型: {analysis_result.task_type.value}")
            # 提取 RouterDecision 中的 intent_type
            intent_type = None
            if analysis_result.router_decision:
                intent_type = analysis_result.router_decision.intent_type
                print(f"  意圖類型: {intent_type}")
                print(f"  複雜度: {analysis_result.router_decision.complexity}")
                print(f"  需要 Agent: {analysis_result.router_decision.needs_agent}")
                print(f"  需要工具: {analysis_result.router_decision.needs_tools}")
                print(f"  風險等級: {analysis_result.router_decision.risk_level}")
            print(f"  工作流類型: {analysis_result.workflow_type.value}")
            print(f"  置信度: {analysis_result.confidence:.2f}")
            print(f"  需要 Agent: {analysis_result.requires_agent}")
            print(f"  建議的 Agent: {analysis_result.suggested_agents}")

            # 驗證任務類型
            task_type_match = False
            if expected_task_type:
                task_type_match = analysis_result.task_type.value == expected_task_type
                status_icon = "✅" if task_type_match else "❌"
                print("\n[驗證結果]")
                print(
                    f"  {status_icon} 任務類型: 預期 {expected_task_type}, 實際 {analysis_result.task_type.value}"
                )

            # 驗證意圖類型（如果 RouterDecision 存在）
            intent_type_match = None
            if analysis_result.router_decision:
                intent_type = analysis_result.router_decision.intent_type
                # 對於文件編輯任務，intent_type 應該為 execution
                if expected_task_type == "execution":
                    intent_type_match = intent_type == "execution"
                    status_icon = "✅" if intent_type_match else "❌"
                    print(f"  {status_icon} 意圖類型: 預期 execution, 實際 {intent_type}")
                    if not intent_type_match:
                        print(f"    ⚠️  意圖類型不匹配！RouterLLM 將文件編輯任務識別為 {intent_type}")
                        print(f"    Router 置信度: {analysis_result.router_decision.confidence:.2f}")
                        print("    Router 決策詳情:")
                        print(f"      - needs_agent: {analysis_result.router_decision.needs_agent}")
                        print(f"      - needs_tools: {analysis_result.router_decision.needs_tools}")
                        print(f"      - complexity: {analysis_result.router_decision.complexity}")
                        print(f"      - risk_level: {analysis_result.router_decision.risk_level}")

            # 驗證 Agent 調用
            agent_match = False
            if expected_agent:
                agent_match = expected_agent in analysis_result.suggested_agents
                status_icon = "✅" if agent_match else "❌"
                print(
                    f"  {status_icon} Agent 調用: 預期 {expected_agent}, 實際 {analysis_result.suggested_agents}"
                )

            # 總結
            all_passed = task_type_match and agent_match
            print("\n[測試總結]")
            if all_passed:
                print("  ✅ 所有驗證點通過")
            else:
                print("  ❌ 部分驗證點未通過")
                if not task_type_match:
                    print("    - 任務類型不匹配")
                if not agent_match:
                    print("    - Agent 調用不匹配（這是關鍵驗證點）")

            # 構建結果
            result = {
                "scenario_id": scenario_id,
                "category": scenario["category"],
                "complexity": complexity,
                "user_input": user_input,
                "expected_task_type": expected_task_type,
                "expected_agent": expected_agent,
                "actual_task_type": analysis_result.task_type.value,
                "actual_intent_type": (
                    analysis_result.router_decision.intent_type
                    if analysis_result.router_decision
                    else None
                ),
                "actual_complexity": (
                    analysis_result.router_decision.complexity
                    if analysis_result.router_decision
                    else None
                ),
                "actual_needs_agent": (
                    analysis_result.router_decision.needs_agent
                    if analysis_result.router_decision
                    else None
                ),
                "actual_needs_tools": (
                    analysis_result.router_decision.needs_tools
                    if analysis_result.router_decision
                    else None
                ),
                "actual_risk_level": (
                    analysis_result.router_decision.risk_level
                    if analysis_result.router_decision
                    else None
                ),
                "actual_agents": analysis_result.suggested_agents,
                "task_type_match": task_type_match,
                "agent_match": agent_match,
                "all_passed": all_passed,
                "confidence": analysis_result.confidence,
                "router_confidence": (
                    analysis_result.router_decision.confidence
                    if analysis_result.router_decision
                    else None
                ),
                "status": "✅ 通過" if all_passed else "❌ 失敗",
                "error": None,
            }

            # 保存結果到全局列表（用於後續報告生成）
            _test_results.append(result)

            # 如果設置了結果文件路徑，追加結果到文件
            if _test_results_file:
                try:
                    # 讀取現有結果（如果存在）
                    existing_results = []
                    if _test_results_file.exists():
                        with open(_test_results_file, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            existing_results = data.get("results", [])

                    # 更新結果
                    existing_results.append(result)

                    # 寫回文件
                    with open(_test_results_file, "w", encoding="utf-8") as f:
                        json.dump({"results": existing_results}, f, ensure_ascii=False, indent=2)
                except Exception as e:
                    print(f"警告：保存測試結果失敗: {e}")

            # 返回結果用於後續報告生成
            return result

        except Exception as e:
            print("\n[錯誤]")
            print(f"  ❌ 測試執行失敗: {e}")
            import traceback

            traceback.print_exc()

            # 保存錯誤結果
            error_result = {
                "scenario_id": scenario_id,
                "category": scenario["category"],
                "complexity": complexity,
                "user_input": user_input,
                "expected_task_type": expected_task_type,
                "expected_agent": expected_agent,
                "actual_task_type": None,
                "actual_intent_type": None,
                "actual_complexity": None,
                "actual_needs_agent": None,
                "actual_needs_tools": None,
                "actual_risk_level": None,
                "actual_agents": [],
                "task_type_match": False,
                "agent_match": False,
                "all_passed": False,
                "confidence": 0.0,
                "router_confidence": None,
                "status": "❌ 錯誤",
                "error": str(e),
            }

            _test_results.append(error_result)

            # 如果設置了結果文件路徑，追加錯誤結果到文件
            if _test_results_file:
                try:
                    existing_results = []
                    if _test_results_file.exists():
                        with open(_test_results_file, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            existing_results = data.get("results", [])

                    existing_results.append(error_result)

                    with open(_test_results_file, "w", encoding="utf-8") as f:
                        json.dump({"results": existing_results}, f, ensure_ascii=False, indent=2)
                except Exception:
                    pass

            raise

        print(f"\n{'='*80}\n")


def generate_test_summary():
    """生成測試摘要報告"""
    print(f"\n{'='*80}")
    print("文件編輯 Agent 語義路由測試摘要")
    print(f"{'='*80}")
    print(f"總場景數: {len(TEST_SCENARIOS)}")
    print("測試類別:")
    categories = {}
    for scenario in TEST_SCENARIOS:
        cat = scenario["category"]
        categories[cat] = categories.get(cat, 0) + 1
    for cat, count in categories.items():
        print(f"  - {cat}: {count} 個場景")
    print(f"{'='*80}\n")


def save_test_results(output_file: Optional[Path] = None) -> Path:
    """保存測試結果到 JSON 文件"""
    global _test_results, _test_results_file

    if output_file is None:
        output_dir = Path(__file__).parent / "test_reports"
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"test_results_{timestamp}.json"

    total = len(_test_results)
    passed = sum(1 for r in _test_results if r.get("all_passed", False))
    failed = total - passed
    pass_rate = (passed / total * 100) if total > 0 else 0

    report = {
        "execution_date": datetime.now().strftime("%Y-%m-%d"),
        "execution_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "executor": "Daniel Chung",
        "test_environment": "本地開發環境",
        "system_version": "v3.2",
        "summary": {
            "total_scenarios": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": f"{pass_rate:.2f}%",
        },
        "results": _test_results,
    }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    return output_file


if __name__ == "__main__":
    generate_test_summary()

    # 設置結果文件路徑
    output_dir = Path(__file__).parent / "test_reports"
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    _test_results_file = output_dir / f"test_results_{timestamp}.json"

    # 清空結果列表
    _test_results.clear()

    # 運行測試
    pytest.main([__file__, "-v", "--tb=short", "-s"])

    # 保存結果
    if _test_results:
        output_file = save_test_results()
        print(f"\n測試結果已保存至: {output_file}")
