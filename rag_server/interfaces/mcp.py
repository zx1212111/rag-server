"""MCP 协议服务。

暴露三个工具：
- rag_query: 问答查询
- ingest_documents: 手动触发文件处理
- get_stats: 查询知识库状态
"""

import logging

from mcp.server.fastmcp import FastMCP

from rag_server.config import load_config
from rag_server.pipeline.ingestion import IngestionPipeline
from rag_server.pipeline.query import QueryPipeline
from rag_server.stores.index_store import IndexStore

logger = logging.getLogger(__name__)

# 全局单例
_config = None
_rag_pipeline = None
_ingestion = None
_index_store = None


def _ensure_services():
    '''确保服务已启动'''
    global _config, _rag_pipeline, _ingestion, _index_store
    if _config is None:
        _config = load_config()
        _index_store = IndexStore(_config.data.index_path)
        _rag_pipeline = QueryPipeline(_config)
        _ingestion = IngestionPipeline(_config)


async def handle_rag_query(query: str, stream: bool = True) -> str:
    """处理 RAG 查询。仅查询，不触发数据导入。"""
    _ensure_services()
    result = _rag_pipeline.query(query, stream=stream)
    answer_parts = []
    async for chunk in result:
        answer_parts.append(chunk)
    return "".join(answer_parts)


async def handle_ingest() -> str:
    """手动触发文件处理。"""
    _ensure_services()
    return await _ingestion.run()


async def handle_stats() -> dict:
    """查询知识库状态。"""
    _ensure_services()
    return {
        "files": _index_store.count_unique_docs(),
        "chunks": _index_store.count_chunks(),
    }


async def mcp_main():
    """启动 MCP Server（stdio 模式）。"""
    server = FastMCP("rag-server")  # 创建 MCP 服务

    @server.tool()
    async def rag_query(query: str, stream: bool = True) -> str:
        """基于知识库回答问题。"""
        return await handle_rag_query(query, stream)

    @server.tool()
    async def ingest_documents() -> str:
        """手动触发文件处理工作流。"""
        return await handle_ingest()

    @server.tool()
    async def get_stats() -> dict:
        """查询知识库状态：已处理文件数和总 chunk 数。"""
        return await handle_stats()

    await server.run_stdio_async()