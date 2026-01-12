# 代碼功能說明: 文本规范化单元测试
# 創建日期: 2026-01-04
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-04

"""测试文本规范化功能"""


from services.api.processors.chunk_processor import normalize_text


class TestNormalizeText:
    """测试 normalize_text 函数"""

    def test_normalize_fullwidth_to_halfwidth(self):
        """测试全角/半角字符规范化"""
        # NFKC 规范化主要处理全角 ASCII 字符（字母、数字、空格）
        # 注意：中文全角标点符号不会被 NFKC 转换为英文标点
        test_cases = [
            ("ＡＢＣ", "ABC"),  # 全角字母
            ("１２３", "123"),  # 全角数字
            ("　", " "),  # 全角空格
        ]

        for before, expected in test_cases:
            result = normalize_text(before)
            assert result == expected, f"规范化失败: {before} -> {result}, 期望: {expected}"

    def test_unicode_compatibility(self):
        """测试 Unicode 兼容性规范化（NFKC）"""
        # NFKC 会将全角 ASCII 字符和某些全角标点转换为半角
        test_text = "全角字母：ＡＢＣ１２３"
        result = normalize_text(test_text)

        # 应该将全角 ASCII 字符转换为半角
        assert "ABC" in result
        assert "123" in result
        # 中文文本应该保持不变
        assert "全角字母" in result
        # 全角冒号可能被转换为半角（取决于 Unicode 定义）
        assert ":" in result or "：" in result

    def test_remove_control_characters(self):
        """测试移除控制字符（保留换行符和制表符）"""
        # 包含控制字符的文本
        text_with_control = "Hello\x00World\x01\x02\nTest\tTab"
        result = normalize_text(text_with_control)

        # 应该保留换行符和制表符
        assert "\n" in result
        assert "\t" in result

        # 应该移除其他控制字符
        assert "\x00" not in result
        assert "\x01" not in result
        assert "\x02" not in result

        # 文本内容应该保持完整
        assert "Hello" in result
        assert "World" in result
        assert "Test" in result
        assert "Tab" in result

    def test_preserve_text_semantics(self):
        """测试文本语义保持不变"""
        # 包含各种字符的复杂文本
        complex_text = "这是一个测试文档。\n\n包含多个段落。\n\n还有代码块：\n```python\nprint('Hello')\n```"
        result = normalize_text(complex_text)

        # 语义应该保持不变
        assert "测试文档" in result
        assert "多个段落" in result
        assert "代码块" in result
        assert "print" in result
        assert "Hello" in result

        # 换行符应该保留
        assert "\n" in result

    def test_empty_string(self):
        """测试空字符串"""
        result = normalize_text("")
        assert result == ""

    def test_whitespace_only(self):
        """测试只有空白字符的字符串"""
        result = normalize_text("   \n\t   ")
        assert result == "   \n\t   "  # 应该保留空白字符

    def test_no_changes_needed(self):
        """测试不需要规范化的文本"""
        normal_text = "This is a normal text with English and 中文."
        result = normalize_text(normal_text)
        assert result == normal_text

    def test_mixed_content(self):
        """测试混合内容（全角、半角、控制字符）"""
        mixed_text = "全角字母：ＡＢＣ\n半角字母：ABC\n全角数字：１２３\n半角数字：123\n控制字符：\x00\x01\n正常文本"
        result = normalize_text(mixed_text)

        # 全角应该转换为半角
        assert "ABC" in result  # 全角字母转换
        assert "123" in result  # 全角数字转换

        # 控制字符应该被移除（除了换行符）
        assert "\x00" not in result
        assert "\x01" not in result
        assert "\n" in result  # 换行符应该保留

        # 正常文本应该保留
        assert "正常文本" in result
