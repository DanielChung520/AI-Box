# 代碼功能說明: Report Generator 報告生成器
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

"""Report Generator - 使用 LLM 整理 Agent 產出並生成 HTML 報告"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


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
    ) -> Dict[str, Any]:
        """
        生成最終報告

        Args:
            aggregated_results: 聚合結果（來自 ResultAggregator）
            report_title: 報告標題（可選）
            include_output_files: 是否包含產出物文件鏈接

        Returns:
            報告數據字典，包含 HTML 內容和元數據
        """
        try:
            # 構建報告內容
            report_content = await self._generate_report_content(aggregated_results, report_title)

            # 生成 HTML 報告
            html_content = self._generate_html_report(
                report_content, aggregated_results, include_output_files
            )

            report_data = {
                "report_id": f"report-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "title": report_title or "Agent 執行報告",
                "generated_at": datetime.now().isoformat(),
                "task_id": aggregated_results.get("task_id"),
                "html_content": html_content,
                "summary": aggregated_results.get("summary", {}),
                "output_files": (
                    aggregated_results.get("output_files", []) if include_output_files else []
                ),
            }

            self._logger.info(f"Generated report: {report_data['report_id']}")
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
