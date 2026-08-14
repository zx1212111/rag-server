"""Batch ingestion timing benchmark.

Standalone script - does not modify source code.
Run: python tests/benchmark_ingestion.py
"""

import asyncio
import logging
import sys
import time

# Windows GBK 终端兼容
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# 配置日志，显示 timing 信息
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
    force=True,
)

from rag_server.config import load_config
from rag_server.pipeline.ingestion import IngestionPipeline
from rag_server.stores.index_store import IndexStore


async def main():
    config = load_config()
    index_store = IndexStore(config.data.index_path)

    print("=" * 60)
    print("Batch Ingestion Timing Report")
    print(f"Data root: {config.data.root}")
    print("=" * 60)

    # 跑导入管线（@timeit 会自动输出每步耗时）
    pipeline = IngestionPipeline(config)
    start = time.perf_counter()
    result = await pipeline.run()
    elapsed_ms = (time.perf_counter() - start) * 1000

    print("-" * 60)
    print(f"[TOTAL] IngestionPipeline: {elapsed_ms:.1f}ms")
    print(result)

    # 统计
    chunks = index_store.count_chunks()
    files = index_store.count_unique_docs()
    print(f"\nFiles: {files}, Chunks: {chunks}")


if __name__ == "__main__":
    asyncio.run(main())