"""检索器单元测试（mock 外部依赖）。"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from rag_server.retrieval.hybrid import HybridRetriever


@pytest.fixture
def mock_components():
    """创建 mock 的 vector_store, bm25, embedding。"""
    with patch("rag_server.retrieval.hybrid.ChromaStore") as mock_vs, \
         patch("rag_server.retrieval.hybrid.BM25Index") as mock_bm25, \
         patch("rag_server.retrieval.hybrid.Factory.create") as mock_factory:

        mock_store = MagicMock()
        mock_store.search = AsyncMock(return_value=[("vec1", 0.9), ("vec2", 0.8)])
        mock_vs.return_value = mock_store

        mock_bm = MagicMock()
        mock_bm.search.return_value = [("bm1", 0.85), ("bm2", 0.7)]
        mock_bm25.return_value = mock_bm

        mock_emb = AsyncMock()
        mock_emb.embed = AsyncMock(return_value=[[0.1, 0.2, 0.3]])
        mock_factory.return_value = mock_emb

        yield mock_store, mock_bm, mock_emb


@pytest.mark.asyncio
async def test_hybrid_retriever_basic(mock_components):
    """基本混合检索应返回合并结果。"""
    retriever = HybridRetriever(
        vector_dir="/tmp/vec", sparse_dir="/tmp/sparse",
        embedding_provider="openai",
    )
    results = await retriever.retrieve("测试查询", top_k=5)
    assert len(results) > 0
    assert all(isinstance(r, tuple) and len(r) == 2 for r in results)


@pytest.mark.asyncio
async def test_hybrid_retriever_empty(mock_components):
    """无结果时应返回空列表。"""
    mock_store, mock_bm, _ = mock_components
    mock_store.search = AsyncMock(return_value=[])
    mock_bm.search.return_value = []

    retriever = HybridRetriever()
    results = await retriever.retrieve("无结果查询")
    assert results == []


@pytest.mark.asyncio
async def test_hybrid_retriever_vector_only(mock_components):
    """仅向量结果应正常工作。"""
    mock_store, mock_bm, _ = mock_components
    mock_bm.search.return_value = []

    retriever = HybridRetriever()
    results = await retriever.retrieve("查询")
    assert len(results) > 0


@pytest.mark.asyncio
async def test_hybrid_retriever_bm25_only(mock_components):
    """仅 BM25 结果应正常工作。"""
    mock_store, mock_bm, _ = mock_components
    mock_store.search = AsyncMock(return_value=[])
    mock_bm.search.return_value = [("bm1", 0.9)]

    retriever = HybridRetriever()
    results = await retriever.retrieve("查询")
    assert len(results) > 0