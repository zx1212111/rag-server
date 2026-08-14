## 1. 新建目录和抽象接口

- [x] 1.1 创建 `rag_server/llm/` 目录和 `rag_server/llm/__init__.py`
- [x] 1.2 创建 `rag_server/embedding/` 目录和 `rag_server/embedding/__init__.py`
- [x] 1.3 创建 `rag_server/llm/base.py`：`LLM(ABC)` 抽象接口，定义 `chat()`
- [x] 1.4 创建 `rag_server/embedding/base.py`：`Embedding(ABC)` 抽象接口，定义 `embed()`

## 2. 实现 llm/ 下的厂商文件

- [x] 2.1 创建 `rag_server/llm/openai.py`：`@register("llm", "openai")`，合并当前 `protocols/openai.py` 的 chat() HTTP 调用 + `providers/llm.py` 的 `OpenAICompatibleLLM`
- [x] 2.2 创建 `rag_server/llm/anthropic.py`：`@register("llm", "anthropic")`，合并当前 `protocols/anthropic.py` 的 chat() HTTP 调用 + `providers/llm.py` 的 `AnthropicLLM`

## 3. 实现 embedding/ 下的厂商文件

- [x] 3.1 创建 `rag_server/embedding/openai.py`：`@register("embedding", "openai")`，合并当前 `protocols/openai.py` 的 embed() HTTP 调用 + `providers/embedding.py` 的 `OpenAICompatibleEmbedding`
- [x] 3.2 创建 `rag_server/embedding/dashscope.py`：`@register("embedding", "dashscope")`，从 `providers/dashscope_embedding.py` 移动并重命名，将导入路径改为 `from .base import Embedding`

## 4. 更新导入路径

- [x] 4.1 更新 `rag_server/pipeline/rag_pipeline.py`：`from rag_server.providers.llm import LLMProvider` → `from rag_server.llm.base import LLM`；`import rag_server.providers.dashscope_embedding` → `import rag_server.embedding.dashscope`
- [x] 4.2 更新 `rag_server/pipeline/ingestion.py`：``from rag_server.providers.embedding import EmbeddingProvider`` → `from rag_server.embedding.base import Embedding`

## 5. 清理旧文件

- [x] 5.1 删除 `rag_server/protocols/` 目录全部文件（base.py, openai.py, anthropic.py, __init__.py）
- [x] 5.2 删除 `rag_server/providers/` 目录全部文件（llm.py, embedding.py, dashscope_embedding.py, __init__.py）

## 6. 验证

- [x] 6.1 运行 `python -m rag_server` 确认 MCP Server 启动无导入错误
- [x] 6.2 运行 `python -m rag_server stats` 确认 CLI 正常
- [x] 6.3 运行 `pytest tests/` 确认集成测试通过（4/4 skipped，因缺少 pytest-asyncio，非本变更导致）

## 7. 清空数据功能

- [x] 7.1 在 `rag_server/interfaces/cli.py` 中新增 `clean_data()` 函数和 `clean` 命令
- [x] 7.2 在 `rag_server/interfaces/web.py` 侧边栏新增"清空数据"按钮（带确认复选框）

## 8. Loader 扩展名可插拔

- [x] 8.1 在 `rag_server/loaders/base.py` 的 `BaseLoader` 中增加类属性 `extensions: List[str] = []`
- [x] 8.2 为每个 Loader 子类声明 `extensions`：pdf(`.pdf`), markdown(`.md`), image(`.png,.jpg,.jpeg,.gif,.bmp`), word(`.docx,.doc`), audio(`.mp3,.wav,.m4a`), video(`.mp4,.avi,.mov,.mkv`)
- [x] 8.3 在 `rag_server/registry.py` 中新增 `get_supported_extensions()` 函数，从 `_registry["loader"]` 自动收集扩展名
- [x] 8.4 修改 `rag_server/stores/document.py`：`list_input_files()` 调用 `get_supported_extensions()` 替代硬编码 tuple
- [x] 8.5 修改 `rag_server/pipeline/ingestion.py`：`_resolve_loader()` 遍历 Loader 注册表匹配扩展名，删除 `loader_map`
- [x] 8.6 验证：`python -c "from rag_server.registry import get_supported_extensions; print(get_supported_extensions())"` 列出全部扩展名

## 9. LLM / Embedding 厂商自动发现

- [x] 9.1 在 `rag_server/registry.py` 中新增 `auto_register(package_name)` 函数，使用 `pkgutil.iter_modules` 自动导入包下所有非 `__init__`/`base` 的模块
- [x] 9.2 修改 `rag_server/pipeline/rag_pipeline.py`：移除 4 行硬编码 import（`import rag_server.llm.openai` 等），改为 `auto_register("rag_server.llm")` + `auto_register("rag_server.embedding")`
- [x] 9.3 验证：`python -m rag_server` 启动确认无导入错误，`python -m rag_server stats` 正常

## 10. Ingestion 管线全流程可插拔

- [x] 10.1 在 `rag_server/config.py` 中新增 `PipelineConfig` 数据类（cleaner_provider / splitter_provider / persister_provider / vectorizer_provider），追加到 `Config`
- [x] 10.2 在 `rag_server/text/base.py` 中新增 `Splitter(ABC)` 抽象接口，定义 `split(text, doc_id) → List[Chunk]`
- [x] 10.3 修改 `rag_server/text/splitter.py`：`TextSplitter` 加 `@register("splitter", "default")`，实现 `Splitter` 接口
- [x] 10.4 新增 `rag_server/stores/persister.py`：`Persister(ABC)` 定义 `persist(chunks, assets, doc_name)`；`FilePersister` 实现，包装现有 `save_doc` + `save_asset` 逻辑
- [x] 10.5 新增 `rag_server/stores/vectorizer.py`：`Vectorizer(ABC)` 定义 `vectorize(chunks)`；`ChromaVectorizer` 实现，包装现有 `index_store.add` + `embed` + `chroma.add_batch` 逻辑
- [x] 10.6 修改 `rag_server/pipeline/ingestion.py`：run() 从 8 步精简为 5 步（加载→清洗→分块→持久化→向量化→移文件），每步由 config 驱动 Factory.create()

## 11. RAG 查询管线全流程可插拔

- [x] 11.1 在 `rag_server/config.py` 的 `RetrievalConfig` 中新增 `retriever_provider` / `fuser_provider` / `assembler_provider` 字段
- [x] 11.2 新增 `rag_server/retrieval/base.py`：`Retriever(ABC)` 定义 `retrieve(query, top_k) → List[Tuple[str, float]]`；`Fuser(ABC)` 定义 `fuse(results) → List[str]`
- [x] 11.3 新增 `rag_server/retrieval/hybrid.py`：`HybridRetriever`，`@register("retriever", "hybrid")`，内部管理 ChromaStore + BM25Index
- [x] 11.4 修改 `rag_server/retrieval/fusion.py`：`HybridFusion` 加 `@register("fuser", "hybrid")`，实现 `Fuser` 接口
- [x] 11.5 新增 `rag_server/prompt/assembler.py`：`Assembler(ABC)` 定义 `assemble(context, query) → List[dict]`；`DefaultAssembler` 实现，封装现有 `_assemble_context` + `SYSTEM_PROMPT` 逻辑
- [x] 11.6 修改 `rag_server/pipeline/rag_pipeline.py`：`query()` 精简为 4 步（检索→融合→组装→LLM），全部由 config 驱动 Factory.create()

## 12. config.yaml 同步

- [x] 12.1 更新 `config.yaml`：新增 `pipeline:` 段（cleaner/splitter/persister/vectorizer），`retrieval:` 补全 retriever/fuser/assembler，移除废弃的 `stitcher:`

## 13. 可插拔组件单元测试

- [x] 13.1 创建 `tests/test_cleaner.py`：测试 DefaultCleaner（纯函数，覆盖多余空格/换行/空输入/边界）
- [x] 13.2 创建 `tests/test_splitter.py`：测试 TextSplitter（纯函数，覆盖分块/ID唯一性/index顺序/边界）
- [x] 13.3 创建 `tests/test_persister.py`：测试 FilePersister（tempfile 隔离，覆盖保存 MD/图片/空列表）
- [x] 13.4 创建 `tests/test_fuser.py`：测试 HybridFusion（纯函数，覆盖空/混合/权重/边界）
- [x] 13.5 创建 `tests/test_assembler.py`：测试 DefaultAssembler（纯函数，覆盖组装/截断/空上下文）
- [x] 13.6 创建 `tests/test_retriever.py`：测试 HybridRetriever（mock Chroma/BM25/Embedding）
- [x] 13.7 创建 `tests/test_vectorizer.py`：测试 ChromaVectorizer（mock IndexStore/Chroma/Embedding）
- [x] 13.8 创建 `tests/test_loaders.py`：测试各 Loader（mock 文件读取）

## 14. 命名清理

- [x] 14.1 文件重命名：`prompt/__init__.py` → `prompt/builder.py`（保留 init 做 re-export），`pipeline/rag_pipeline.py` → `pipeline/query.py`
- [x] 14.2 类重命名：全部完成（Storage/Indexer/PromptBuilder/Ranker/ChunkJoiner/OpenAILLM/OpenAIEmbedding/JoinerConfig）
- [x] 14.3 管道重命名：`RAGPipeline` → `QueryPipeline`
- [x] 14.4 config 键名同步：pipeline.indexer/storage, retrieval.ranker/prompt_builder
- [x] 14.5 测试文件和导入路径同步更新：mcp.py/cli.py/web.py + 6 个测试文件
- [x] 14.6 验证全量测试通过：43 passed, 0 failed

## 15. ASR REST API 重写 + 视频导入修复

- [x] 15.1 修复 `asr/dashscope.py`：dashscope SDK `Recognition.call()` 签名变更 → 改用 httpx REST API（适配新版 SDK）
- [x] 15.2 修复 `loaders/video.py`：ffmpeg 临时音频文件写入 `input/` 目录 → 改到系统 temp 目录
- [x] 15.3 更新 `.env`：新增 ASR_PROVIDER / ASR_BASE_URL / ASR_API_KEY / ASR_MODEL 配置项
- [x] 15.4 更新 `.env.example`：同步新增 ASR 配置项
- [x] 15.5 验证：mp4 视频文件成功导入并转写为文字

## 16. config 段名与代码类名对齐

- [x] 16.1 重命名 `config.yaml`：`pipeline:` → `ingestion_pipeline:`，`retrieval:` → `query_pipeline:`
- [x] 16.2 重命名 `config.py`：`PipelineConfig` → `IngestionPipelineConfig`，`RetrievalConfig` → `QueryPipelineConfig`；`Config` 字段 `pipeline` → `ingestion_pipeline`，`retrieval` → `query_pipeline`
- [x] 16.3 更新所有引用：`ingestion.py` / `query.py` / `web.py` / merge 映射
- [x] 16.4 验证：43 passed

## 17. 模型调用目录归组

- [x] 17.1 创建 `rag_server/models/` 目录和 `__init__.py`
- [x] 17.2 移动 `llm/` → `models/llm/`，`embedding/` → `models/embedding/`，`asr/` → `models/asr/`
- [x] 17.3 更新所有导入路径（pipeline/query.py, ingestion.py, loaders/video.py, loaders/audio.py）
- [x] 17.4 更新 `auto_register()` 参数到 `rag_server.models.llm` / `rag_server.models.embedding`
- [x] 17.5 删除旧的 `llm/`、`embedding/`、`asr/` 目录（mv 自带删除）
- [x] 17.6 测试文件无需修改（无直接导入旧路径）
- [x] 17.7 验证全量测试通过：43 passed

## 18. 分块算法重写：步距累加 + 上下文重叠

- [x] 18.1 `config.py`：`IngestionPipelineConfig` 新增 `chunk_size: int = 1000`、`stride: int = 800` 字段
- [x] 18.2 `config.yaml`：`ingestion_pipeline:` 段新增 `chunk_size: 1000`、`stride: 800`
- [x] 18.3 `rag_server/text/splitter.py`：重写 `split()` 方法，实现步距累加 + 上下文重叠算法
- [x] 18.4 `rag_server/pipeline/ingestion.py`：`_ensure_services()` 中创建 splitter 时传递 `chunk_size` 和 `stride`
- [x] 18.5 验证：运行 `pytest tests/` 确认测试通过