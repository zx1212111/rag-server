"""CLI 命令行接口。

命令：
    rag-server               MCP Server 模式
    rag-server ingest        手动触发文件处理
    rag-server query "..."   查询问答
    rag-server stats         查看知识库状态
    rag-server clean         清空所有数据
"""

import asyncio
import os
import shutil
import sys


def clean_data(data_root: str):
    """清空 data 目录下的所有索引和缓存数据，保留目录结构。"""
    dirs_to_clean = ["docs", "assets", "processed", "sparse", "vector"]
    for d in dirs_to_clean:
        path = os.path.join(data_root, d)
        if os.path.exists(path):
            shutil.rmtree(path)
            os.makedirs(path, exist_ok=True)

    index_path = os.path.join(data_root, "index.json")
    if os.path.exists(index_path):
        os.remove(index_path)

    print("[OK] 所有数据已清空")


def cli_main():
    """CLI 入口。"""
    args = sys.argv[1:]
    if not args:
        print("用法: rag-server <ingest|query|stats|clean>")
        print("提示: query 仅查询，不会自动导入文件，请先运行 ingest")
        return

    command = args[0]

    if command == "ingest":
        asyncio.run(_run_ingest())
    elif command == "query":
        query_text = " ".join(args[1:])
        if not query_text:
            print("请提供问题: rag-server query \"你的问题\"")
            return
        asyncio.run(_run_query(query_text))
    elif command == "stats":
        asyncio.run(_run_stats())
    elif command == "clean":
        asyncio.run(_run_clean())
    else:
        print(f"未知命令: {command}")
        print("可用命令: ingest, query, stats, clean")


async def _run_ingest():
    from rag_server.config import load_config
    from rag_server.pipeline.ingestion import IngestionPipeline

    config = load_config()
    pipeline = IngestionPipeline(config)
    result = await pipeline.run()
    print(result)


async def _run_query(query: str, stream: bool = True):
    from rag_server.config import load_config
    from rag_server.pipeline.query import QueryPipeline

    config = load_config()
    pipeline = QueryPipeline(config)

    result = pipeline.query(query, stream=stream)
    async for chunk in result:
        print(chunk, end="", flush=True)
    print()


async def _run_stats():
    from rag_server.config import load_config
    from rag_server.stores.index_store import IndexStore

    config = load_config()
    index = IndexStore(config.data.index_path)
    files = index.count_unique_docs()
    chunks = index.count_chunks()
    print(f"已处理文件: {files}")
    print(f"总 chunk 数: {chunks}")


async def _run_clean():
    from rag_server.config import load_config

    config = load_config()
    clean_data(config.data.root)


if __name__ == "__main__":
    cli_main()