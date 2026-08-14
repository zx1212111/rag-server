"""分块器单元测试。"""

import pytest

from rag_server.text.splitter import TextSplitter
from rag_server.text.chunk import Chunk


class TestTextSplitter:
    """测试 TextSplitter 分块功能。"""

    def setup_method(self):
        self.splitter = TextSplitter(chunk_size=500, overlap=100)

    def test_simple_split(self):
        """简单文本应被分成至少一个 chunk。"""
        chunks = self.splitter.split("这是一段简单的文本。", doc_id="test")
        assert len(chunks) > 0
        assert isinstance(chunks[0], Chunk)

    def test_chunk_id_unique(self):
        """每个 chunk 应有唯一 ID。"""
        chunks = self.splitter.split("第一段。\n\n第二段。\n\n第三段。", doc_id="test")
        ids = [c.id for c in chunks]
        assert len(set(ids)) == len(ids)

    def test_chunk_index_sequential(self):
        """chunk_index 应从 0 开始连续递增。"""
        chunks = self.splitter.split("段落一。\n\n段落二。\n\n段落三。", doc_id="test")
        for i, c in enumerate(chunks):
            assert c.chunk_index == i

    def test_doc_id_preserved(self):
        """所有 chunk 的 doc_id 应与传入的一致。"""
        chunks = self.splitter.split("内容一。\n\n内容二。", doc_id="my_doc")
        assert all(c.doc_id == "my_doc" for c in chunks)

    def test_chunk_content_not_empty(self):
        """每个 chunk 的内容不应为空。"""
        chunks = self.splitter.split("有效内容。\n\n更多内容。\n\n还有一些。", doc_id="test")
        assert all(len(c.content) > 0 for c in chunks)

    def test_position_tracking(self):
        """start_char / end_char 应准确标记位置。"""
        text = "Hello World。"
        chunks = self.splitter.split(text, doc_id="test")
        assert len(chunks) == 1
        assert chunks[0].start_char == 0
        assert chunks[0].end_char == len(text)

    def test_chunk_size_respected(self):
        """长文本应被切分成不超过 chunk_size 的块。"""
        text = "句子。" * 200  # 600 chars, 无段落换行
        small = TextSplitter(chunk_size=100, stride=80)
        chunks = small.split(text, doc_id="test")
        for c in chunks:
            assert len(c.content) <= 100