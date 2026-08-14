"""向量化器单元测试（mock 外部依赖）。"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from rag_server.text.chunk import Chunk


@pytest.fixture
def mock_deps():
    """mock IndexStore, ChromaStore, Embedding。"""
    with patch("rag_server.stores.vectorizer.IndexStore") as mock_idx, \
         patch("rag_server.stores.vectorizer.ChromaStore") as mock_cs, \
         patch("rag_server.stores.vectorizer.Factory.create") as mock_factory:

        mock_idx.return_value = MagicMock()

        mock_store = MagicMock()
        mock_store.add_batch = AsyncMock()
        mock_cs.return_value = mock_store

        mock_emb = MagicMock()
        mock_emb.embed = AsyncMock(return_value=[[0.1], [0.2], [0.3]])
        mock_factory.return_value = mock_emb

        yield mock_idx, mock_store, mock_emb


@pytest.mark.asyncio
async def test_chroma_vectorizer_basic(mock_deps):
    """基本向量化应正确调用各组件。"""
    mock_idx, mock_store, _ = mock_deps

    from rag_server.stores.vectorizer import ChromaIndexer
    vectorizer = ChromaIndexer(
        index_path="/tmp/index.json",
        vector_dir="/tmp/vector",
        embedding_provider="openai",
    )

    chunks = [
        Chunk(id="c1", doc_id="d1", chunk_index=0, content="chunk1",
              start_char=0, end_char=10),
        Chunk(id="c2", doc_id="d1", chunk_index=1, content="chunk2",
              start_char=11, end_char=20),
        Chunk(id="c3", doc_id="d1", chunk_index=2, content="chunk3",
              start_char=21, end_char=30),
    ]

    await vectorizer.index(chunks)

    # 验证 IndexStore.add_batch 被调用
    assert mock_idx.return_value.add_batch.call_count == 1

    # 验证 Embedding.embed 被调用
    mock_emb = mock_deps[2]
    mock_emb.embed.assert_called_once()

    # 验证 ChromaStore.add_batch 被调用
    mock_store.add_batch.assert_called_once()


@pytest.mark.asyncio
async def test_chroma_vectorizer_empty(mock_deps):
    """空 chunks 列表不应出错。"""
    mock_idx, mock_store, mock_emb = mock_deps

    from rag_server.stores.vectorizer import ChromaIndexer
    vectorizer = ChromaIndexer()

    await vectorizer.index([])

    # embed 被调用（传空列表返回空），add_batch 也被调用
    mock_emb.embed.assert_called_once_with([])
    mock_store.add_batch.assert_called_once()