## Context

当前代码全链路没有任何耗时记录，排查性能瓶颈只能靠猜或手动加 print。需要统一的计时工具，在关键路径埋点，输出结构化日志。

核心约束：
- 零外部依赖（只用 Python 标准库 `time` + `logging`）
- 对异步方法友好（所有关键路径都是 `async def`）
- 不影响业务逻辑，一行装饰器即可开启/关闭

## Goals / Non-Goals

**Goals:**
- 提供 `@timeit` 装饰器，自动记录函数耗时并输出 `[timing]` 日志
- 提供 `Timer` 上下文管理器，用于代码块级别的计时
- 覆盖 ingestion 全链路（加载 → 清洗 → 分块 → 嵌入 → 写入 → BM25 重建）
- 覆盖 query 全链路（嵌入 → 向量检索 → BM25 检索 → 融合 → 组装 → LLM 生成）
- 日志包含操作名、耗时毫秒、以及可选的上下文字段（文件名、chunk 数等）

**Non-Goals:**
- 不做聚合统计（平均耗时、P99 等）
- 不对外暴露（不计入 MCP 工具或 CLI 输出）
- 不引入 OpenTelemetry 等外部依赖

## Decisions

### 1. 工具位置：`rag_server/utils/timer.py`

新建 `rag_server/utils/` 包，`timer.py` 作为其中第一个工具模块。

**Rationale**: 顶层应该放核心模块（`config.py`、`registry.py`），工具类归入 `utils/` 包统一管理。以后 token 计数、重试逻辑等也可放此处。

### 2. 计时工具设计

两套 API，适应不同场景：

#### 装饰器 `@timeit` — 用于整个方法的计时

```python
@timeit
async def search(self, query, top_k=20):
    ...
```

自动记录方法名，输出：`[timing] ChromaStore.search: 234ms`

#### 上下文管理器 `Timer` — 用于代码块级别的计时

```python
async with Timer("bm25.rebuild") as t:
    self.bm25 = BM25Index(...)
    self.bm25.build(all_texts)
```

输出：`[timing] bm25.rebuild: 567ms`

#### 带额外信息的计时

```python
@timeit
async def load(self, path: str) -> LoadResult:
    ...

# 输出: [timing] PDFLoader.load: 1234ms [path=年报.pdf]
```

装饰器自动从参数中提取有意义的上下文信息（如文件名）。

### 3. 埋点位置

#### Ingestion 链路

| 文件 | 方法 | 计时名 |
|------|------|--------|
| `loaders/pdf.py` | `load()` | `PDFLoader.load` |
| `loaders/markdown.py` | `load()` | `MarkdownLoader.load` |
| `loaders/image.py` | `load()` | `ImageLoader.load` |
| `text/cleaner.py` | `clean()` | `clean` |
| `text/splitter.py` | `split()` | `split` |
| `stores/chroma.py` | `add()` | `ChromaStore.add` |
| `pipeline/ingestion.py` | `_process_file()` | `ingestion.process_file` |
| `pipeline/ingestion.py` | `_rebuild_bm25()` | `ingestion.rebuild_bm25` |
| `pipeline/ingestion.py` | `run()` | `ingestion.run` |

#### Query 链路

| 文件 | 方法 | 计时名 |
|------|------|--------|
| `providers/embedding.py` | `embed()` | `embedding` |
| `stores/chroma.py` | `search()` | `ChromaStore.search` |
| `retrieval/bm25.py` | `search()` | `BM25Index.search` |
| `retrieval/fusion.py` | `fuse()` | `HybridFusion.fuse` |
| `retrieval/stitcher.py` | `stitch()` | `ChunkStitcher.stitch` |
| `pipeline/rag_pipeline.py` | `query()` | `RAGPipeline.query` |
| `pipeline/rag_pipeline.py` | 内部 LLM 调用 | `LLM.chat` |

### 4. 不侵入业务逻辑

装饰器不修改函数的返回值，不改变函数的签名。在被计时函数内部无法感知是否被计时。移除时只需删掉 `@timeit` 一行。

## Risks / Trade-offs

| 风险 | 缓解措施 |
|------|---------|
| 装饰器增加了极微小的调用开销（纳秒级） | 仅对 async 函数可用；不影响业务逻辑性能基准 |
| 日志输出过多 | `[timing]` 前缀方便 grep 过滤 |
| 异步函数的异常传播 | 装饰器使用 try/finally 确保异常正常抛出 |