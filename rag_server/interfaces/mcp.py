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
    _ensure_services()  # 确保服务已启动
    result = _rag_pipeline.query(query, stream=stream)  # 执行查询
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
    # 预加载 chromadb/numpy（主线程）：
    # anyio 用工作线程执行 tool，若首次导入发生在工作线程，
    # 会撞上 Python 导入锁 + Windows C 扩展初始化，导致死锁。
    # 主线程预先导入后，工作线程直接复用已加载模块，不再碰导入锁。
    try:
        import chromadb  # noqa: F401
        import numpy  # noqa: F401
        logger.info("chromadb/numpy 预加载完成")
    except Exception as e:
        logger.warning(f"预加载 chromadb/numpy 失败（将继续启动）: {e}")

    # 预初始化服务（同样在主线程完成，避免首次查询在工作线程初始化触发导入）
    try:
        _ensure_services()
        # 触发 ChromaStore._ensure_client()，在主线程把 chromadb 客户端建好
        if _rag_pipeline is not None and _rag_pipeline._retriever is None:
            _rag_pipeline._ensure_services()
        logger.info("RAG 服务预初始化完成")
    except Exception as e:
        logger.warning(f"RAG 服务预初始化失败（将延迟到首次查询）: {e}")

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

    await server.run_stdio_async()  # 启动服务