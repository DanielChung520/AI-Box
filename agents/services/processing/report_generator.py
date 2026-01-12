# 代碼功能說明: Report Generator 報告生成器
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-08

"""Report Generator - 使用 LLM 整理 Agent 產出並生成 HTML/JSON/PDF 報告"""

import base64
import io
import logging
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class DisplayType(str, Enum):
    """顯示類型枚舉"""

    INLINE = "inline"
    LINK = "link"


class StructuredReportResponse(BaseModel):
    """結構化報告響應模型"""

    report_id: str = Field(..., description="報告 ID")
    title: str = Field(..., description="報告標題")
    generated_at: str = Field(..., description="生成時間")
    task_id: Optional[str] = Field(None, description="任務 ID")
    display_type: DisplayType = Field(DisplayType.INLINE, description="顯示類型")
    inline_data: Optional[Dict[str, Any]] = Field(None, description="內嵌數據（當 display_type=inline 時）")
    link_data: Optional[str] = Field(None, description="鏈接數據（當 display_type=link 時）")
    summary: Dict[str, Any] = Field(default_factory=dict, description="執行摘要")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元數據")


class PDFReportResponse(BaseModel):
    """PDF 報告響應模型"""

    report_id: str = Field(..., description="報告 ID")
    title: str = Field(..., description="報告標題")
    generated_at: str = Field(..., description="生成時間")
    pdf_content: bytes = Field(..., description="PDF 內容（base64 編碼）")
    pdf_size: int = Field(..., description="PDF 文件大小（字節）")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元數據")


class ReportMetadata(BaseModel):
    """報告元數據模型"""

    report_id: str = Field(..., description="報告 ID")
    title: str = Field(..., description="報告標題")
    format: str = Field(..., description="報告格式（html/json/pdf）")
    generated_at: str = Field(..., description="生成時間")
    task_id: Optional[str] = Field(None, description="任務 ID")
    user_id: Optional[str] = Field(None, description="用戶 ID")
    size: int = Field(0, description="報告大小（字節）")
    version: int = Field(1, description="報告版本")


class ReportGenerator:
    """報告生成器 - 使用 LLM 整理 Agent 產出並生成 HTML 報告"""

    def __init__(self, llm_manager: Optional[Any] = None):
        """
        初始化報告生成器

        Args:
            llm_manager: LLM 管理器實例（可選，用於調用 LLM）
        """
        self._llm_manager = llm_manager
        self._logger = logger

    async def generate_report(
        self,
        aggregated_results: Dict[str, Any],
        report_title: Optional[str] = None,
        include_output_files: bool = True,
        format: str = "html",
    ) -> Dict[str, Any]:
        """
        生成最終報告

        Args:
            aggregated_results: 聚合結果（來自 ResultAggregator）
            report_title: 報告標題（可選）
            include_output_files: 是否包含產出物文件鏈接
            format: 報告格式（html/json/pdf），默認 html

        Returns:
            報告數據字典，包含報告內容和元數據
        """
        try:
            # 構建報告內容
            report_content = await self._generate_report_content(aggregated_results, report_title)

            report_id = f"report-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            title = report_title or "Agent 執行報告"
            generated_at = datetime.now().isoformat()
            task_id = aggregated_results.get("task_id")

            # 根據格式生成報告
            if format == "json":
                return await self.generate_structured_json(
                    report_id=report_id,
                    title=title,
                    generated_at=generated_at,
                    task_id=task_id,
                    aggregated_results=aggregated_results,
                    report_content=report_content,
                    include_output_files=include_output_files,
                )
            elif format == "pdf":
                return await self.generate_pdf(
                    report_id=report_id,
                    title=title,
                    generated_at=generated_at,
                    task_id=task_id,
                    aggregated_results=aggregated_results,
                    report_content=report_content,
                    include_output_files=include_output_files,
                )
            else:
                # 默認生成 HTML
                html_content = self._generate_html_report(
                    report_content, aggregated_results, include_output_files
                )

                report_data = {
                    "report_id": report_id,
                    "title": title,
                    "generated_at": generated_at,
                    "task_id": task_id,
                    "html_content": html_content,
                    "summary": aggregated_results.get("summary", {}),
                    "output_files": (
                        aggregated_results.get("output_files", []) if include_output_files else []
                    ),
                }

                self._logger.info(f"Generated HTML report: {report_data['report_id']}")
                return report_data

        except Exception as e:
            self._logger.error(f"Failed to generate report: {e}")
            raise

    async def _generate_report_content(
        self, aggregated_results: Dict[str, Any], title: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        使用 LLM 整理報告內容

        Args:
            aggregated_results: 聚合結果
            title: 報告標題

        Returns:
            整理後的報告內容
        """
        # 如果沒有 LLM 管理器，使用簡單的文本整理
        if not self._llm_manager:
            return self._simple_report_content(aggregated_results, title)

        try:
            # 構建 LLM 提示詞
            prompt = self._build_report_prompt(aggregated_results, title)

            # 調用 LLM 整理報告
            result = await self._llm_manager.generate(
                prompt,
                temperature=0.7,
                max_tokens=4000,
            )

            # 提取 LLM 生成的內容
            content = result.get("text") or result.get("content", "")

            return {
                "title": title or "Agent 執行報告",
                "summary": self._extract_summary_from_llm(content),
                "detailed_content": content,
            }

        except Exception as e:
            self._logger.warning(f"LLM report generation failed: {e}, using simple format")
            return self._simple_report_content(aggregated_results, title)

    def _simple_report_content(
        self, aggregated_results: Dict[str, Any], title: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        簡單的報告內容整理（不使用 LLM）

        Args:
            aggregated_results: 聚合結果
            title: 報告標題

        Returns:
            簡單的報告內容
        """
        summary = aggregated_results.get("summary", {})
        results = aggregated_results.get("results", [])

        content_parts = []

        # 執行摘要
        content_parts.append("## 執行摘要\n\n")
        content_parts.append(f"- 總 Agent 數量: {summary.get('total_count', 0)}\n")
        content_parts.append(f"- 成功數量: {summary.get('success_count', 0)}\n")
        content_parts.append(f"- 失敗數量: {summary.get('failure_count', 0)}\n")
        content_parts.append(f"- 成功率: {summary.get('success_rate', 0.0) * 100:.1f}%\n")

        # 詳細結果
        content_parts.append("\n## 詳細結果\n\n")
        for idx, result in enumerate(results, 1):
            agent_id = result.get("agent_id", "unknown")
            status = result.get("status", "unknown")
            content_parts.append(f"### Agent {idx}: {agent_id}\n\n")
            content_parts.append(f"- 狀態: {status}\n")
            if result.get("result"):
                content_parts.append(f"- 結果: {str(result['result'])[:200]}...\n")
            if result.get("error"):
                content_parts.append(f"- 錯誤: {result['error']}\n")
            content_parts.append("\n")

        return {
            "title": title or "Agent 執行報告",
            "summary": summary,
            "detailed_content": "".join(content_parts),
        }

    def _build_report_prompt(
        self, aggregated_results: Dict[str, Any], title: Optional[str] = None
    ) -> str:
        """
        構建 LLM 報告整理提示詞

        Args:
            aggregated_results: 聚合結果
            title: 報告標題

        Returns:
            LLM 提示詞
        """
        results_json = str(aggregated_results)

        prompt = f"""請整理以下 Agent 執行結果，生成一份清晰的執行報告。

任務信息：
- 任務 ID: {aggregated_results.get('task_id', 'N/A')}
- 聚合時間: {aggregated_results.get('aggregated_at', 'N/A')}

執行結果：
{results_json}

請按照以下結構整理報告：
1. 執行摘要（總體情況、成功率等）
2. 各 Agent 執行詳情
3. 關鍵發現和結論
4. 建議和後續行動

請使用 Markdown 格式輸出。"""

        if title:
            prompt = f"報告標題: {title}\n\n" + prompt

        return prompt

    def _extract_summary_from_llm(self, content: str) -> Dict[str, Any]:
        """
        從 LLM 生成的內容中提取摘要（簡單實現）

        Args:
            content: LLM 生成的內容

        Returns:
            摘要字典
        """
        # 簡單的摘要提取（可以後續改進）
        return {
            "content_length": len(content),
            "has_summary": "##" in content or "#" in content,
        }

    def _generate_html_report(
        self,
        report_content: Dict[str, Any],
        aggregated_results: Dict[str, Any],
        include_output_files: bool = True,
    ) -> str:
        """
        生成 HTML 格式的報告

        Args:
            report_content: 報告內容
            aggregated_results: 聚合結果
            include_output_files: 是否包含產出物文件鏈接

        Returns:
            HTML 內容字符串
        """
        title = report_content.get("title", "Agent 執行報告")
        detailed_content = report_content.get("detailed_content", "")
        summary = report_content.get("summary", {})
        output_files = aggregated_results.get("output_files", [])
        generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 將 Markdown 轉換為 HTML（簡單實現，可以後續使用專業庫）
        html_content = self._markdown_to_html(detailed_content)

        # 構建完整的 HTML 文檔
        html = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            background-color: white;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            padding: 30px;
        }}
        h1 {{
            color: #333;
            border-bottom: 3px solid #4CAF50;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #555;
            margin-top: 30px;
            border-bottom: 2px solid #e0e0e0;
            padding-bottom: 5px;
        }}
        h3 {{
            color: #666;
            margin-top: 20px;
        }}
        .summary-box {{
            background-color: #f9f9f9;
            border-left: 4px solid #4CAF50;
            padding: 15px;
            margin: 20px 0;
        }}
        .output-files {{
            margin-top: 30px;
            padding: 15px;
            background-color: #e3f2fd;
            border-radius: 4px;
        }}
        .file-link {{
            display: inline-block;
            margin: 5px 10px 5px 0;
            padding: 8px 15px;
            background-color: #2196F3;
            color: white;
            text-decoration: none;
            border-radius: 4px;
        }}
        .file-link:hover {{
            background-color: #1976D2;
        }}
        .metadata {{
            color: #888;
            font-size: 0.9em;
            margin-top: 20px;
            padding-top: 20px;
            border-top: 1px solid #e0e0e0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{title}</h1>

        <div class="summary-box">
            <h2>執行摘要</h2>
            <ul>
                <li>總 Agent 數量: {summary.get('total_count', 0)}</li>
                <li>成功數量: {summary.get('success_count', 0)}</li>
                <li>失敗數量: {summary.get('failure_count', 0)}</li>
                <li>成功率: {summary.get('success_rate', 0.0) * 100:.1f}%</li>
            </ul>
        </div>

        <div class="content">
            {html_content}
        </div>

        {self._generate_output_files_section(output_files) if include_output_files and output_files else ''}

        <div class="metadata">
            <p>報告生成時間: {generated_at}</p>
            <p>任務 ID: {aggregated_results.get('task_id', 'N/A')}</p>
        </div>
    </div>
</body>
</html>"""

        return html

    def _markdown_to_html(self, markdown: str) -> str:
        """
        將 Markdown 轉換為 HTML（簡單實現）

        Args:
            markdown: Markdown 文本

        Returns:
            HTML 文本
        """
        # 簡單的 Markdown 到 HTML 轉換
        html = markdown

        # 轉換標題
        html = html.replace("### ", "<h3>").replace("\n", "</h3>\n", 1)
        html = html.replace("## ", "<h2>").replace("\n", "</h2>\n", 1)
        html = html.replace("# ", "<h1>").replace("\n", "</h1>\n", 1)

        # 轉換列表項
        lines = html.split("\n")
        in_list = False
        result = []
        for line in lines:
            if line.strip().startswith("- "):
                if not in_list:
                    result.append("<ul>")
                    in_list = True
                result.append(f"<li>{line.strip()[2:]}</li>")
            else:
                if in_list:
                    result.append("</ul>")
                    in_list = False
                result.append(line)

        if in_list:
            result.append("</ul>")

        return "\n".join(result)

    def _generate_output_files_section(self, output_files: List[str]) -> str:
        """
        生成產出物文件區段

        Args:
            output_files: 文件 URL 列表

        Returns:
            HTML 字符串
        """
        if not output_files:
            return ""

        files_html = '<div class="output-files">\n<h3>產出物文件</h3>\n'
        for file_url in output_files:
            file_name = file_url.split("/")[-1]
            files_html += (
                f'<a href="{file_url}" class="file-link" target="_blank">{file_name}</a>\n'
            )
        files_html += "</div>"

        return files_html

    async def generate_structured_json(
        self,
        report_id: str,
        title: str,
        generated_at: str,
        task_id: Optional[str],
        aggregated_results: Dict[str, Any],
        report_content: Dict[str, Any],
        include_output_files: bool = True,
        display_type: DisplayType = DisplayType.INLINE,
    ) -> Dict[str, Any]:
        """
        生成結構化 JSON 報告

        Args:
            report_id: 報告 ID
            title: 報告標題
            generated_at: 生成時間
            task_id: 任務 ID
            aggregated_results: 聚合結果
            report_content: 報告內容
            include_output_files: 是否包含產出物文件
            display_type: 顯示類型（inline/link）

        Returns:
            結構化 JSON 報告數據
        """
        summary = aggregated_results.get("summary", {})
        results = aggregated_results.get("results", [])

        # 構建內嵌數據
        inline_data: Dict[str, Any] = {
            "summary": summary,
            "results": results,
            "detailed_content": report_content.get("detailed_content", ""),
        }

        if include_output_files:
            inline_data["output_files"] = aggregated_results.get("output_files", [])

        # 構建響應
        response_data: Dict[str, Any] = {
            "report_id": report_id,
            "title": title,
            "generated_at": generated_at,
            "task_id": task_id,
            "display_type": display_type.value,
            "summary": summary,
            "metadata": {
                "format": "json",
                "version": "1.0",
            },
        }

        if display_type == DisplayType.INLINE:
            response_data["inline_data"] = inline_data
        else:
            # 如果 display_type 是 link，則生成鏈接（這裡簡化處理，實際應該存儲到存儲服務）
            response_data["link_data"] = f"/api/reports/{report_id}"

        self._logger.info(f"Generated structured JSON report: {report_id}")
        return response_data

    async def generate_pdf(
        self,
        report_id: str,
        title: str,
        generated_at: str,
        task_id: Optional[str],
        aggregated_results: Dict[str, Any],
        report_content: Dict[str, Any],
        include_output_files: bool = True,
    ) -> Dict[str, Any]:
        """
        生成 PDF 報告

        Args:
            report_id: 報告 ID
            title: 報告標題
            generated_at: 生成時間
            task_id: 任務 ID
            aggregated_results: 聚合結果
            report_content: 報告內容
            include_output_files: 是否包含產出物文件

        Returns:
            PDF 報告數據（包含 base64 編碼的 PDF 內容）

        Raises:
            RuntimeError: 如果 reportlab 不可用
        """
        if not REPORTLAB_AVAILABLE:
            raise RuntimeError(
                "reportlab library is not available. Please install it: pip install reportlab"
            )

        # 創建 PDF 緩衝區
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []

        # 標題
        title_style = styles["Title"]
        title_para = Paragraph(title, title_style)
        story.append(title_para)
        story.append(Spacer(1, 0.2 * inch))

        # 元數據
        metadata_text = f"<b>生成時間:</b> {generated_at}<br/>"
        if task_id:
            metadata_text += f"<b>任務 ID:</b> {task_id}<br/>"
        metadata_para = Paragraph(metadata_text, styles["Normal"])
        story.append(metadata_para)
        story.append(Spacer(1, 0.2 * inch))

        # 執行摘要
        summary = aggregated_results.get("summary", {})
        summary_data = [
            ["項目", "數值"],
            ["總 Agent 數量", str(summary.get("total_count", 0))],
            ["成功數量", str(summary.get("success_count", 0))],
            ["失敗數量", str(summary.get("failure_count", 0))],
            [
                "成功率",
                f"{summary.get('success_rate', 0.0) * 100:.1f}%",
            ],
        ]

        summary_table = Table(summary_data, colWidths=[3 * inch, 2 * inch])
        summary_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 12),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ]
            )
        )
        story.append(Paragraph("<b>執行摘要</b>", styles["Heading2"]))
        story.append(Spacer(1, 0.1 * inch))
        story.append(summary_table)
        story.append(Spacer(1, 0.3 * inch))

        # 詳細內容
        detailed_content = report_content.get("detailed_content", "")
        if detailed_content:
            story.append(Paragraph("<b>詳細結果</b>", styles["Heading2"]))
            story.append(Spacer(1, 0.1 * inch))
            # 簡單處理 Markdown 內容（轉換為純文本段落）
            for line in detailed_content.split("\n"):
                line = line.strip()
                if line and not line.startswith("#"):
                    # 移除 Markdown 標記
                    line = line.replace("##", "").replace("###", "").replace("-", "•")
                    if line:
                        para = Paragraph(line, styles["Normal"])
                        story.append(para)
            story.append(Spacer(1, 0.3 * inch))

        # 產出物文件
        if include_output_files:
            output_files = aggregated_results.get("output_files", [])
            if output_files:
                story.append(Paragraph("<b>產出物文件</b>", styles["Heading2"]))
                story.append(Spacer(1, 0.1 * inch))
                for file_url in output_files:
                    file_name = file_url.split("/")[-1]
                    file_para = Paragraph(f"• {file_name}", styles["Normal"])
                    story.append(file_para)
                story.append(Spacer(1, 0.3 * inch))

        # 構建 PDF
        doc.build(story)
        pdf_bytes = buffer.getvalue()
        buffer.close()

        # Base64 編碼
        pdf_base64 = base64.b64encode(pdf_bytes).decode("utf-8")

        response_data = {
            "report_id": report_id,
            "title": title,
            "generated_at": generated_at,
            "pdf_content": pdf_base64,
            "pdf_size": len(pdf_bytes),
            "metadata": {
                "format": "pdf",
                "version": "1.0",
                "task_id": task_id,
            },
        }

        self._logger.info(f"Generated PDF report: {report_id} ({len(pdf_bytes)} bytes)")
        return response_data
