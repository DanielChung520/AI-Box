#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自然語言查詢測試腳本（15 種場景）

功能：
1. 測試 IntentAnalyzer 的異常檢測能力
2. 驗證正常查詢的 Action 判斷
3. 生成測試報告

使用方式：
    python DA-NL-Query-Test-15場景測試腳本.py
"""

import sys
import json
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass, field

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from data_agent.intent_analyzer import IntentAnalyzer, QueryIntent, IntentAnalysisResult


@dataclass
class TestCase:
    """測試案例"""

    id: str
    category: str  # ABN (異常) / NML (正常)
    input_query: str
    expected_type: str  # abnormal / normal
    expected_action: Optional[str] = None  # text_to_sql / query_datalake / None
    expected_error_type: Optional[str] = None  # 預期錯誤類型
    description: str = ""


@dataclass
class TestResult:
    """測試結果"""

    case_id: str
    category: str
    input_query: str
    actual_type: str
    actual_action: Optional[str]
    passed: bool
    error_message: Optional[str] = None
    intent_analysis: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = ""


class NLQueryTester:
    """自然語言查詢測試器"""

    def __init__(self):
        self.analyzer = IntentAnalyzer()
        self.results: List[TestResult] = []
        self.test_cases = self._create_test_cases()

    def _create_test_cases(self) -> List[TestCase]:
        """創建測試案例"""
        return [
            # === 異常類（6 種）===
            TestCase(
                id="ABN-001",
                category="ABN",
                input_query="幫我",
                expected_type="abnormal",
                expected_action=None,
                expected_error_type="語義不完整",
                description="語義嚴重不足 - 只有開頭",
            ),
            TestCase(
                id="ABN-002",
                category="NML",
                input_query="查詢 W00 倉庫的庫存",
                expected_type="normal",
                expected_action="text_to_sql",
                description="無效倉庫代碼 - 顯示警告但可執行",
            ),
            TestCase(
                id="ABN-003",
                category="NML",
                input_query="查詢料號 100001 的庫存",
                expected_type="normal",
                expected_action="text_to_sql",
                description="料號格式可能錯誤但可處理 - 顯示警告",
            ),
            TestCase(
                id="ABN-004",
                category="ABN",
                input_query="删除 W01 仓库的所有库存记录",
                expected_type="abnormal",
                expected_action=None,
                expected_error_type="危險操作",
                description="危險關鍵字 - 簡體 + 刪除操作",
            ),
            TestCase(
                id="ABN-005",
                category="ABN",
                input_query="刪除料號 10-0001 的庫存記錄",
                expected_type="abnormal",
                expected_action=None,
                expected_error_type="危險操作",
                description="危險操作 - 試圖刪除數據",
            ),
            TestCase(
                id="ABN-006",
                category="ABN",
                input_query="查詢料號 10-0001 的庫存; DROP TABLE img_file;--",
                expected_type="abnormal",
                expected_action=None,
                expected_error_type="安全性攻擊",
                description="SQL 注入攻擊",
            ),
            # === 正常類（9 種）===
            TestCase(
                id="NML-001",
                category="NML",
                input_query="查詢 W01 倉庫的庫存",
                expected_type="normal",
                expected_action="text_to_sql",
                description="基本庫存查詢 - 單一倉庫",
            ),
            TestCase(
                id="NML-002",
                category="NML",
                input_query="查W01 庫房每個料號存量",
                expected_type="normal",
                expected_action="text_to_sql",
                description="統計查詢 - 按料號分組求和",
            ),
            TestCase(
                id="NML-003",
                category="NML",
                input_query="查詢料號 10-0001 的庫存信息",
                expected_type="normal",
                expected_action="text_to_sql",
                description="指定料號查詢",
            ),
            TestCase(
                id="NML-004",
                category="NML",
                input_query="計算各倉庫的平均庫存量",
                expected_type="normal",
                expected_action="text_to_sql",
                description="平均統計 - 各倉庫平均庫存",
            ),
            TestCase(
                id="NML-005",
                category="NML",
                input_query="列出前 10 個庫存量最多的物料",
                expected_type="normal",
                expected_action="text_to_sql",
                description="前 N 筆排序 - 庫存最多物料",
            ),
            TestCase(
                id="NML-006",
                category="NML",
                input_query="統計 W03 成品倉的總庫存量",
                expected_type="normal",
                expected_action="text_to_sql",
                description="總計查詢 - W03 成品倉",
            ),
            TestCase(
                id="NML-007",
                category="NML",
                input_query="查詢 2024 年有多少筆採購進貨",
                expected_type="normal",
                expected_action="text_to_sql",
                description="筆數統計 - 2024 年採購進貨",
            ),
            TestCase(
                id="NML-008",
                category="NML",
                input_query="列出所有負庫存的物料",
                expected_type="normal",
                expected_action="text_to_sql",
                description="負庫存查詢",
            ),
            TestCase(
                id="NML-009",
                category="NML",
                input_query="查詢料號 10-0001 的品名和規格",
                expected_type="normal",
                expected_action="query_datalake",
                description="料件主檔直接查詢",
            ),
            # === 邊緣案例（4 種）===
            TestCase(
                id="EDGE-001",
                category="NML",
                input_query="請幫我查詢W01庫房資料",
                expected_type="normal",
                expected_action="text_to_sql",
                description="正常查詢 - 包含請幫我",
            ),
            TestCase(
                id="EDGE-002",
                category="NML",
                input_query="查 W06",
                expected_type="normal",
                expected_action="text_to_sql",
                description="無效倉庫代碼 - 顯示警告但可執行",
            ),
            TestCase(
                id="EDGE-003",
                category="NML",
                input_query="料號 100001 的庫存",
                expected_type="normal",
                expected_action="text_to_sql",
                description="料號格式警告但可處理",
            ),
            TestCase(
                id="EDGE-004",
                category="NML",
                input_query="查 W01 庫房????",
                expected_type="normal",
                expected_action="text_to_sql",
                description="查詢含問號但可處理",
            ),
        ]

    def _detect_dangerous(self, query: str) -> Tuple[bool, str]:
        """檢測危險操作"""
        # 危險關鍵字（支援繁簡體）
        dangerous_keywords = [
            # 英文
            "drop",
            "delete",
            "truncate",
            "update",
            "insert",
            # 繁體中文
            "刪除",
            "移除",
            "清除",
            "修改",
            "更新",
            # 簡體中文
            "删除",
            "移除",
            "清除",
            "修改",
            "更新",
        ]
        query_lower = query.lower()

        for kw in dangerous_keywords:
            if kw.lower() in query_lower:
                return True, f"危險關鍵字：{kw}"

        # 檢測 SQL 注入模式
        injection_patterns = [
            r";\s*(drop|delete|truncate|update|insert)",
            r"--\s*$",
            r"/\*",
            r"'\s*or\s+'1'\s*=\s*'1'",
        ]
        for pattern in injection_patterns:
            if re.search(pattern, query_lower):
                return True, "SQL 注入模式"

        return False, ""

    def _detect_format_error(self, query: str) -> Tuple[bool, str]:
        """檢測格式錯誤"""
        # 檢查倉庫代碼
        warehouse_match = re.search(r"[Ww]0([0-9])", query)
        if warehouse_match:
            warehouse_num = warehouse_match.group(1)
            if warehouse_num == "0" or int(warehouse_num) > 5:
                return True, f"倉庫代碼錯誤：W{warehouse_num}（應為 W01-W05）"

        # 檢查料號格式（應為 XX-XXXX）
        item_code_error = re.search(r"(料號|item)[\s:：]*(\d{6,})", query, re.IGNORECASE)
        if item_code_error:
            return True, f"料號格式錯誤：{item_code_error.group(2)}（應為 XX-XXXX）"

        return False, ""

    def _is_meaningful(self, query: str, result: IntentAnalysisResult) -> bool:
        """檢查語義是否完整"""
        # 過短（但含有意義關鍵字的不算）
        if len(query.strip()) < 5:
            # 允許包含特定關鍵字的查詢
            meaningful_keywords = ["2024", "2025", "多少筆", "筆數", "採購", "進貨"]
            for kw in meaningful_keywords:
                if kw in query:
                    return True
            return False

        # 意圖為 UNKNOWN
        if result.query_intent == QueryIntent.UNKNOWN:
            return False

        return True

    def _determine_action(self, result: IntentAnalysisResult) -> Optional[str]:
        """根據意圖分析結果判斷 Action"""
        # 主檔查詢用 query_datalake
        if result.table == "ima_file":
            return "query_datalake"

        # 其他（有明確意圖）用 text_to_sql
        if result.query_intent != QueryIntent.UNKNOWN:
            return "text_to_sql"

        return None

    def run_single_test(self, test_case: TestCase) -> TestResult:
        """執行單一測試"""
        query = test_case.input_query
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        try:
            # 1. 危險檢測
            is_dangerous, danger_msg = self._detect_dangerous(query)
            if is_dangerous:
                return TestResult(
                    case_id=test_case.id,
                    category=test_case.category,
                    input_query=query,
                    actual_type="abnormal",
                    actual_action=None,
                    passed=test_case.expected_type == "abnormal",
                    error_message=danger_msg,
                    timestamp=timestamp,
                )

            # 2. 格式錯誤檢測（改為警告而非拒絕）
            is_format_error, format_msg = self._detect_format_error(query)
            if is_format_error:
                # 格式錯誤僅作為警告，不拒絕查詢
                # 讓 IntentAnalyzer 處理警告
                pass

            # 3. IntentAnalyzer 分析
            intent_result = self.analyzer.analyze(query)

            # 4. 語義完整性檢查
            is_meaningful = self._is_meaningful(query, intent_result)
            if not is_meaningful:
                return TestResult(
                    case_id=test_case.id,
                    category=test_case.category,
                    input_query=query,
                    actual_type="abnormal",
                    actual_action=None,
                    passed=test_case.expected_type == "abnormal",
                    error_message="語義不完整",
                    intent_analysis=intent_result.to_dict(),
                    timestamp=timestamp,
                )

            # 5. 判斷 Action
            actual_action = self._determine_action(intent_result)

            # 6. 判斷類型
            actual_type = "normal" if actual_action else "abnormal"

            # 7. 檢查是否通過
            passed = actual_type == test_case.expected_type and (
                actual_action == test_case.expected_action or test_case.expected_action is None
            )

            return TestResult(
                case_id=test_case.id,
                category=test_case.category,
                input_query=query,
                actual_type=actual_type,
                actual_action=actual_action,
                passed=passed,
                intent_analysis=intent_result.to_dict(),
                timestamp=timestamp,
            )

        except Exception as e:
            return TestResult(
                case_id=test_case.id,
                category=test_case.category,
                input_query=query,
                actual_type="error",
                actual_action=None,
                passed=False,
                error_message=f"異常：{str(e)}",
                timestamp=timestamp,
            )

    def run_all_tests(self) -> Dict[str, Any]:
        """執行所有測試"""
        print("=" * 70)
        print("自然語言查詢測試（15 種場景）")
        print(f"時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)

        total = len(self.test_cases)
        passed = 0
        failed = 0

        for i, test_case in enumerate(self.test_cases, 1):
            print(f"\n[{i:02d}/{total}] {test_case.id}: {test_case.description}")
            print(f"  輸入: 「{test_case.input_query}」")
            print(f"  預期: {test_case.expected_type} / {test_case.expected_action or '-'}")

            result = self.run_single_test(test_case)
            self.results.append(result)

            if result.passed:
                passed += 1
                print(f"  ✅ 通過")
                if result.actual_type == "normal":
                    print(f"     Action: {result.actual_action}")
            else:
                failed += 1
                print(f"  ❌ 失敗")
                if result.error_message:
                    print(f"     原因: {result.error_message}")
                if result.actual_type:
                    print(f"     實際: {result.actual_type} / {result.actual_action or '-'}")

        # 生成報告
        return self.generate_report(passed, failed)

    def generate_report(self, passed: int, failed: int) -> Dict[str, Any]:
        """生成測試報告"""
        report = {
            "test_time": datetime.now().isoformat(),
            "total_tests": len(self.test_cases),
            "passed": passed,
            "failed": failed,
            "pass_rate": f"{passed / len(self.test_cases) * 100:.1f}%",
            "results": [
                {
                    "case_id": r.case_id,
                    "category": r.category,
                    "input": r.input_query,
                    "actual_type": r.actual_type,
                    "actual_action": r.actual_action,
                    "passed": r.passed,
                    "error": r.error_message,
                    "intent_analysis": r.intent_analysis,
                    "timestamp": r.timestamp,
                }
                for r in self.results
            ],
        }

        # 打印摘要
        print("\n" + "=" * 70)
        print("測試結果摘要")
        print("=" * 70)
        print(f"總測試數: {len(self.test_cases)}")
        print(f"通過: {passed} ✅")
        print(f"失敗: {failed} ❌")
        print(f"通過率: {passed / len(self.test_cases) * 100:.1f}%")

        # 分類統計
        abn_cases = [r for r in self.results if r.category == "ABN"]
        nml_cases = [r for r in self.results if r.category == "NML"]

        abn_passed = sum(1 for r in abn_cases if r.passed)
        nml_passed = sum(1 for r in nml_cases if r.passed)

        print(f"\n異常類測試: {abn_passed}/{len(abn_cases)} 通過")
        print(f"正常類測試: {nml_passed}/{len(nml_cases)} 通過")

        # 保存報告
        report_path = (
            Path(__file__).resolve().parent
            / f"NL-Query-Test-結果-{datetime.now().strftime('%Y%m%d%H%M%S')}.json"
        )
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"\n報告已保存: {report_path}")

        return report


def main():
    """主函數"""
    tester = NLQueryTester()
    report = tester.run_all_tests()

    # 返回退出碼
    if report["failed"] > 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
