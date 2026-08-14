"""Prompt 组装器单元测试。"""

import pytest

from rag_server.prompt import DefaultPromptBuilder


class TestDefaultPromptBuilder:
    """测试 DefaultPromptBuilder Prompt 组装功能。"""

    def setup_method(self):
        self.assembler = DefaultPromptBuilder(max_chars=1000)

    @pytest.mark.asyncio
    async def test_assemble_basic(self):
        """基本组装应生成包含 context 和 query 的 system prompt。"""
        messages = await self.assembler.build("这是文档内容。", "这是什么？")
        assert len(messages) == 1
        assert messages[0]["role"] == "system"
        assert "这是文档内容" in messages[0]["content"]
        assert "这是什么" in messages[0]["content"]

    @pytest.mark.asyncio
    async def test_assemble_empty_context(self):
        """空 context 不应报错。"""
        messages = await self.assembler.build("", "问题？")
        assert len(messages) == 1

    @pytest.mark.asyncio
    async def test_assemble_truncation(self):
        """超长 context 应截断。"""
        small = DefaultPromptBuilder(max_chars=50)
        long_context = "第一句。" + "很长的一句话没有标点" * 20 + "结束。"
        messages = await small.build(long_context, "问题？")
        assert "问题" in messages[0]["content"]

    @pytest.mark.asyncio
    async def test_assemble_no_placeholders(self):
        """占位符不应残留。"""
        messages = await self.assembler.build("测试内容。", "测试问题？")
        content = messages[0]["content"]
        assert "{coNtext}" not in content
        assert "{query}" not in content