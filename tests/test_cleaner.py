"""清洗器单元测试。"""

import pytest

from rag_server.text.cleaner import DefaultCleaner


class TestDefaultCleaner:
    """测试 DefaultCleaner 清洗功能。"""

    def setup_method(self):
        self.cleaner = DefaultCleaner()

    def test_remove_extra_spaces(self):
        """多余空格应被合并。"""
        result = self.cleaner.clean("这是   一段  文本。")
        assert result == "这是 一段 文本。"

    def test_remove_extra_newlines(self):
        """多余空行应被合并。"""
        result = self.cleaner.clean("第一段\n\n\n\n第二段")
        assert result == "第一段\n\n第二段"

    def test_strip_whitespace(self):
        """首尾空白应被去除。"""
        assert self.cleaner.clean("  你好世界  ") == "你好世界"

    def test_empty_input(self):
        """空输入应返回空字符串。"""
        assert self.cleaner.clean("") == ""
        assert self.cleaner.clean("   ") == ""

    def test_normal_text_unchanged(self):
        """正常文本不应被破坏。"""
        text = "这是一段正常的文本。它包含多个句子！"
        assert self.cleaner.clean(text) == text

    def test_mixed_whitespace(self):
        """混合空格和换行。"""
        result = self.cleaner.clean("标题  \n\n\n  内容  ")
        assert "标题" in result
        assert "内容" in result