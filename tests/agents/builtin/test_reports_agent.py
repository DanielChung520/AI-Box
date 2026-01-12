# 代碼功能說明: Reports Agent 單元測試
# 創建日期: 2026-01-08
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-08

"""Reports Agent 單元測試

測試報告生成器的核心功能：HTML/JSON/PDF 報告生成和報告存儲。
"""

from datetime import datetime

import pytest

from agents.services.processing.report_generator import DisplayType, ReportGenerator
from agents.services.processing.report_storage import ReportStorageService


class TestReportGenerator:
    """Report Generator 測試類"""

    @pytest.fixture
    def report_generator(self):
        """創建 ReportGenerator 實例"""
        return ReportGenerator()

    @pytest.fixture
    def sample_aggregated_results(self):
        """創建示例聚合結果"""
        return {
            "task_id": "test-task-001",
            "aggregated_at": datetime.now().isoformat(),
            "summary": {
                "total_count": 3,
                "success_count": 2,
                "failure_count": 1,
                "success_rate": 0.67,
            },
            "results": [
                {"agent_id": "agent-1", "status": "success", "result": "Result 1"},
                {"agent_id": "agent-2", "status": "success", "result": "Result 2"},
                {"agent_id": "agent-3", "status": "failed", "error": "Error message"},
            ],
            "output_files": ["/files/output1.txt", "/files/output2.txt"],
        }

    @pytest.mark.asyncio
    async def test_generate_html_report(self, report_generator, sample_aggregated_results):
        """測試生成 HTML 報告"""
        result = await report_generator.generate_report(
            aggregated_results=sample_aggregated_results,
            report_title="測試報告",
            format="html",
        )

        assert result["report_id"] is not None
        assert result["title"] == "測試報告"
        assert "html_content" in result
        assert "執行摘要" in result["html_content"]

    @pytest.mark.asyncio
    async def test_generate_structured_json(self, report_generator, sample_aggregated_results):
        """測試生成結構化 JSON 報告"""
        result = await report_generator.generate_structured_json(
            report_id="test-report-001",
            title="測試報告",
            generated_at=datetime.now().isoformat(),
            task_id="test-task-001",
            aggregated_results=sample_aggregated_results,
            report_content={"detailed_content": "測試內容"},
            display_type=DisplayType.INLINE,
        )

        assert result["report_id"] == "test-report-001"
        assert result["display_type"] == "inline"
        assert "inline_data" in result
        assert "summary" in result["inline_data"]

    @pytest.mark.asyncio
    async def test_generate_structured_json_link(self, report_generator, sample_aggregated_results):
        """測試生成結構化 JSON 報告（link 模式）"""
        result = await report_generator.generate_structured_json(
            report_id="test-report-002",
            title="測試報告",
            generated_at=datetime.now().isoformat(),
            task_id="test-task-001",
            aggregated_results=sample_aggregated_results,
            report_content={"detailed_content": "測試內容"},
            display_type=DisplayType.LINK,
        )

        assert result["display_type"] == "link"
        assert "link_data" in result
        assert result["link_data"].startswith("/api/reports/")

    @pytest.mark.asyncio
    async def test_generate_pdf_report(self, report_generator, sample_aggregated_results):
        """測試生成 PDF 報告"""
        try:
            result = await report_generator.generate_pdf(
                report_id="test-report-003",
                title="測試報告",
                generated_at=datetime.now().isoformat(),
                task_id="test-task-001",
                aggregated_results=sample_aggregated_results,
                report_content={"detailed_content": "測試內容"},
            )

            assert result["report_id"] == "test-report-003"
            assert "pdf_content" in result
            assert "pdf_size" in result
            assert result["pdf_size"] > 0
        except RuntimeError as e:
            if "reportlab" in str(e).lower():
                pytest.skip("reportlab library is not available")
            else:
                raise

    def test_display_type_enum(self):
        """測試 DisplayType 枚舉"""
        assert DisplayType.INLINE.value == "inline"
        assert DisplayType.LINK.value == "link"


class TestReportStorageService:
    """Report Storage Service 測試類"""

    @pytest.fixture
    def storage_service(self):
        """創建 ReportStorageService 實例"""
        # 使用測試數據庫客戶端（如果有的話）
        return ReportStorageService()

    @pytest.fixture
    def sample_report_data(self):
        """創建示例報告數據"""
        return {
            "title": "測試報告",
            "html_content": "<html>測試內容</html>",
            "summary": {"total_count": 3, "success_count": 2},
        }

    def test_save_report(self, storage_service, sample_report_data):
        """測試保存報告"""
        report_id = "test-report-001"
        key = storage_service.save_report(
            report_id=report_id,
            report_data=sample_report_data,
            user_id="test-user-001",
            task_id="test-task-001",
        )

        assert key is not None
        assert key.startswith(f"{report_id}_v")

    def test_get_report(self, storage_service, sample_report_data):
        """測試獲取報告"""
        report_id = "test-report-002"
        storage_service.save_report(
            report_id=report_id,
            report_data=sample_report_data,
        )

        report = storage_service.get_report(report_id)
        assert report is not None
        assert report["report_id"] == report_id
        assert report["title"] == "測試報告"

    def test_list_reports(self, storage_service, sample_report_data):
        """測試列出報告"""
        # 創建多個報告
        for i in range(3):
            storage_service.save_report(
                report_id=f"test-report-{i:03d}",
                report_data=sample_report_data,
                user_id="test-user-001",
            )

        reports = storage_service.list_reports(user_id="test-user-001", limit=10)
        assert len(reports) >= 3

    def test_update_report(self, storage_service, sample_report_data):
        """測試更新報告（創建新版本）"""
        report_id = "test-report-003"
        storage_service.save_report(
            report_id=report_id,
            report_data=sample_report_data,
        )

        # 更新報告
        updated_data = {**sample_report_data, "title": "更新後的報告"}
        storage_service.update_report(report_id, updated_data)

        # 獲取最新版本
        latest = storage_service.get_report(report_id)
        assert latest is not None
        assert latest["version"] == 2
        assert latest["title"] == "更新後的報告"

    def test_delete_report(self, storage_service, sample_report_data):
        """測試刪除報告"""
        report_id = "test-report-004"
        storage_service.save_report(
            report_id=report_id,
            report_data=sample_report_data,
        )

        # 刪除報告
        deleted = storage_service.delete_report(report_id)
        assert deleted is True

        # 驗證報告已刪除
        report = storage_service.get_report(report_id)
        assert report is None
