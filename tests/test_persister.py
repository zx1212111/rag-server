"""持久化器单元测试。"""

import pytest
from pathlib import Path
import tempfile

from rag_server.text.chunk import Chunk


@pytest.mark.asyncio
async def test_file_persister_save():
    """FileStorage 应正确保存 MD 和图片资产。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        from rag_server.stores.persister import FileStorage
        persister = FileStorage(data_root=tmpdir)

        chunks = [
            Chunk(id="c1", doc_id="doc1", chunk_index=0,
                  content="第一段内容", start_char=0, end_char=20),
            Chunk(id="c2", doc_id="doc1", chunk_index=1,
                  content="第二段内容", start_char=21, end_char=40),
        ]
        assets = [{"filename": "img1.png", "data": b"fake_png_data"}]

        await persister.persist(chunks, assets, doc_name="test_doc")

        md_path = Path(tmpdir) / "docs" / "test_doc.md"
        assert md_path.exists()
        content = md_path.read_text(encoding="utf-8")
        assert "第一段内容" in content
        assert "第二段内容" in content

        asset_path = Path(tmpdir) / "assets" / "test_doc" / "img1.png"
        assert asset_path.exists()
        assert asset_path.read_bytes() == b"fake_png_data"


@pytest.mark.asyncio
async def test_file_persister_no_assets():
    """无图片资产时不应出错。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        from rag_server.stores.persister import FileStorage
        persister = FileStorage(data_root=tmpdir)
        chunks = [Chunk(id="c1", doc_id="doc1", chunk_index=0,
                        content="仅文本", start_char=0, end_char=10)]
        await persister.persist(chunks, [], doc_name="no_asset_doc")
        assert (Path(tmpdir) / "docs" / "no_asset_doc.md").exists()


@pytest.mark.asyncio
async def test_file_persister_empty_chunks():
    """空 chunks 列表不应出错。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        from rag_server.stores.persister import FileStorage
        persister = FileStorage(data_root=tmpdir)
        await persister.persist([], [], doc_name="empty_doc")
        assert (Path(tmpdir) / "docs" / "empty_doc.md").exists()