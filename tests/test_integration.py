"""全链路集成测试。

验证 ingest → query → 返回结果的完整流程。
"""

import asyncio
import os
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def test_config():
    """创建临时测试配置和数据目录。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        os.environ["DATA_ROOT"] = tmpdir
        os.environ["LLM_API_KEY"] = "test-key"

        from rag_server.config import load_config
        config = load_config()
        config.data.root = tmpdir
        config.data.__post_init__()

        # 创建 input 目录
        Path(config.data.input_dir).mkdir(parents=True, exist_ok=True)
        yield config


@pytest.mark.asyncio
async def test_splitter_basic():
    """测试文本分块器。"""
    from rag_server.text.splitter import TextSplitter
    from rag_server.text.chunk import Chunk

    splitter = TextSplitter(chunk_size=500, overlap=100)
    text = """## 第一章

这是第一段内容。包含多个句子。这里还有内容。

## 第二章

这是第二段内容。同样包含一些句子。
"""
    chunks = splitter.split(text, doc_id="test_doc")
    assert len(chunks) > 0
    assert all(isinstance(c, Chunk) for c in chunks)
    assert chunks[0].doc_id == "test_doc"


@pytest.mark.asyncio
async def test_cleaner_default():
    """测试默认清洗器。"""
    from rag_server.text.cleaner import DefaultCleaner
    cleaner = DefaultCleaner()
    result = cleaner.clean("  这是   一段  文本。\n\n\n\n另一段。  ")
    assert "这是" in result
    assert "一段" in result


@pytest.mark.asyncio
async def test_index_store_rw():
    """测试 IndexStore 读写。"""
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        index_path = Path(tmpdir) / "index.json"
        from rag_server.stores.index_store import IndexStore
        store = IndexStore(str(index_path))
        store.add("chunk_1", "测试文本", doc_id="doc1")
        assert store.count_chunks() == 1
        entry = store.get("chunk_1")
        assert entry is not None
        assert entry["text"] == "测试文本"


@pytest.mark.asyncio
async def test_ingestion_flow(test_config):
    """测试导入流程（无外部依赖）。"""
    # 创建一个测试 MD 文件
    input_file = Path(test_config.data.input_dir) / "test.md"
    input_file.write_text("# 测试文档\n\n这是测试内容。", encoding="utf-8")

    from rag_server.pipeline.ingestion import IngestionPipeline
    pipeline = IngestionPipeline(test_config)
    result = await pipeline.run()
    assert "成功 1" in result or "1 个" in result