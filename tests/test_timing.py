"""流水线耗时测试。

收集所有 [timing] 日志，汇总输出各步骤耗时报告。
"""

import asyncio
import io
import logging
import re
from typing import Dict, List

import pytest


class TimingCaptureHandler(logging.Handler):
    """捕获 [timing] 日志的 handler。"""

    def __init__(self):
        super().__init__()
        self.records: List[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord):
        if record.getMessage().startswith("[timing]"):
            self.records.append(record)


@pytest.fixture
def capture_timing():
    """Fixture：捕获测试期间的 timing 日志。"""
    handler = TimingCaptureHandler()
    handler.setLevel(logging.INFO)
    logging.getLogger().setLevel(logging.INFO)
    logging.getLogger().addHandler(handler)
    yield handler
    logging.getLogger().removeHandler(handler)


def format_timing_report(records: List[logging.LogRecord]) -> str:
    """解析 timing 日志行，输出格式化的耗时报告。"""
    entries: List[Dict] = []
    total_ms = 0.0

    for r in records:
        msg = r.getMessage()
        # [timing] module.ClassName.method: 123.4ms
        m = re.match(r"\[timing\] (.+): ([0-9.]+)ms", msg)
        if m:
            name = m.group(1)
            ms = float(m.group(2))
            entries.append({"name": name, "ms": ms})
            total_ms += ms

    if not entries:
        return "[timing] 无记录"

    # 按耗时降序排列
    entries.sort(key=lambda e: -e["ms"])

    # 计算最大名称宽度对齐
    max_name_len = max(len(e["name"]) for e in entries)
    sep = "=" * (max_name_len + 30)

    lines = [sep, "  Pipeline Timing Report", sep]
    for e in entries:
        pct = (e["ms"] / total_ms * 100) if total_ms > 0 else 0
        bar = "█" * int(pct / 5)
        lines.append(
            f"  {e['name'].ljust(max_name_len)}  "
            f"{e['ms']:>8.1f}ms  "
            f"{pct:5.1f}%  {bar}"
        )
    lines.append(sep)
    lines.append(f"  {'TOTAL'.ljust(max_name_len)}  {total_ms:>8.1f}ms  {'100%':>5s}")
    lines.append(sep)
    return "\n".join(lines)


class TestTiming:
    """流水线各环节耗时测试。"""

    @pytest.mark.asyncio
    async def test_text_pipeline(self, capture_timing):
        """文本处理流水线：清洗 → 分块。"""
        from rag_server.text.cleaner import DefaultCleaner
        from rag_server.text.splitter import TextSplitter

        text = """# 测试文档

这是一段测试文本。它包含多个句子。

## 第二节

这里是第二节的内容，包含更多文字用于测试分块效果。
""" * 30  # 重复 30 次制造足够文本

        cleaner = DefaultCleaner()
        cleaned = cleaner.clean(text)
        assert len(cleaned) > 0

        splitter = TextSplitter(chunk_size=200, overlap=50)
        chunks = splitter.split(cleaned, "test_doc")
        assert len(chunks) > 0

        report = format_timing_report(capture_timing.records)
        print(f"\n{report}")

    @pytest.mark.asyncio
    async def test_bm25_pipeline(self, capture_timing):
        """BM25 索引构建 + 检索。"""
        from rag_server.retrieval.bm25 import BM25Index
        import tempfile
        import os

        with tempfile.TemporaryDirectory() as tmpdir:
            bm25 = BM25Index(sparse_dir=os.path.join(tmpdir, "sparse"))

            # 手动构建索引
            texts = [
                "机器学习是人工智能的一个重要分支",
                "深度学习使用神经网络进行特征提取",
                "自然语言处理让计算机理解人类语言",
                "计算机视觉关注图像和视频的理解",
            ]
            bm25.rebuild_from_texts(texts)

            results = bm25.search("神经网络")
            assert len(results) > 0

        report = format_timing_report(capture_timing.records)
        print(f"\n{report}")

    def test_fusion_stitcher(self, capture_timing):
        """混合融合 + 拼接。"""
        from rag_server.retrieval.fusion import HybridRanker
        from rag_server.retrieval.stitcher import ChunkJoiner

        # 测试融合
        ranker = HybridRanker(vector_weight=0.5, final_top_k=3, vector_top_k=10)
        results = [("a", 0.9), ("b", 0.8), ("c", 0.7), ("b", 0.85), ("c", 0.75), ("d", 0.6)]
        fused = ranker.rank(results)
        assert len(fused) > 0

        # 测试拼接
        joiner = ChunkJoiner(enabled=True, dedup=True)
        chunks = [
            {"text": "第一部分内容", "start_char": 0, "end_char": 20},
            {"text": "第二部分内容", "start_char": 20, "end_char": 40},
        ]
        stitched = joiner.stitch(chunks)
        assert len(stitched) > 0

        report = format_timing_report(capture_timing.records)
        print(f"\n{report}")

    @pytest.mark.asyncio
    async def test_chroma_pipeline(self, capture_timing):
        """Chroma 向量存储：写入 + 检索。"""
        from rag_server.stores.chroma import ChromaStore
        import tempfile
        import os

        tmpdir = tempfile.mkdtemp()
        try:
            store = ChromaStore(persist_dir=os.path.join(tmpdir, "vector"))
            await store.add_batch(
                ids=["id1", "id2"],
                vectors=[[1.0, 0.0], [0.0, 1.0]],
                metadatas=[{"text": "doc1"}, {"text": "doc2"}],
            )
            results = await store.search([1.0, 0.0], top_k=2)
            assert len(results) > 0
        finally:
            import shutil
            try:
                shutil.rmtree(tmpdir, ignore_errors=True)
            except PermissionError:
                pass  # Windows 文件锁，忽略清理错误

        report = format_timing_report(capture_timing.records)
        print(f"\n{report}")