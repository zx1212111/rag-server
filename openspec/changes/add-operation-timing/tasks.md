## 1. 工具模块

- [x] 1.1 创建 `rag_server/utils/` 目录和 `rag_server/utils/__init__.py`
- [x] 1.2 创建 `rag_server/utils/timer.py`：实现 `@timeit` 装饰器和 `Timer` 上下文管理器

## 2. Ingestion 链路埋点

- [x] 2.1 在 `rag_server/loaders/pdf.py` 的 `load()` 方法上加 `@timeit`
- [x] 2.2 在 `rag_server/loaders/markdown.py` 的 `load()` 方法上加 `@timeit`
- [x] 2.3 在 `rag_server/loaders/image.py` 的 `load()` 方法上加 `@timeit`
- [x] 2.4 在 `rag_server/text/cleaner.py` 的 `clean()` 方法上加 `@timeit`（3 个 cleaner 实现）
- [x] 2.5 在 `rag_server/text/splitter.py` 的 `split()` 方法上加 `@timeit`
- [x] 2.6 在 `rag_server/stores/chroma.py` 的 `add()`、`add_batch()` 和 `search()` 方法上加 `@timeit`
- [x] 2.7 在 `rag_server/pipeline/ingestion.py` 的 `run()` 方法上加 `@timeit`

## 3. Query 链路埋点

- [x] 3.1 在 `rag_server/retrieval/bm25.py` 的 `search()` 方法上加 `@timeit`
- [x] 3.2 在 `rag_server/retrieval/fusion.py` 的 `fuse()` 方法上加 `@timeit`
- [x] 3.3 在 `rag_server/retrieval/stitcher.py` 的 `stitch()` 方法上加 `@timeit`
- [x] 3.4 在 `rag_server/llm/openai.py` 和 `rag_server/llm/anthropic.py` 的 `chat()` 方法上加 `@timeit`
- [x] 3.5 在 `rag_server/embedding/openai.py` 和 `rag_server/embedding/dashscope.py` 的 `embed()` 方法上加 `@timeit`
- [x] 3.6 在 `rag_server/pipeline/rag_pipeline.py` 的 `query()` 方法上加 `@timeit`

## 4. 验证

- [x] 4.1 运行 `python -m rag_server stats` 确认无导入错误
- [x] 4.2 运行 `python -m rag_server stats` 正常输出（无需 ingest 测试）

## 5. 流水线耗时测试

- [x] 5.1 安装 `pytest-asyncio`（使 async 测试可执行）
- [x] 5.2 创建 `tests/test_timing.py`：跑一次完整流程，收集所有 `[timing]` 日志，输出耗时报告
- [x] 5.3 验证 `pytest tests/test_timing.py -v` 通过（4/4, 2.07s）