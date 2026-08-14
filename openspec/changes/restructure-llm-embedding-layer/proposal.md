## Why

当前 `rag_server/` 下 `protocols/` 和 `providers/` 两个包分层过细：协议层仅封装 HTTP 通信，能力层是薄适配层。实际每个厂商只需一个文件，两层分离导致文件数翻倍、理解成本高、新增厂商需加两个文件。

目标是将 AI 能力层的目录结构按**能力（LLM / Embedding）分目录、按厂商分文件**重组，让结构更直观、可插拔、易扩展。

## What Changes

- **删除** `rag_server/protocols/` 目录（base.py, openai.py, anthropic.py）
- **删除** `rag_server/providers/` 目录（llm.py, embedding.py, dashscope_embedding.py）
- **新增** `rag_server/llm/` 目录：
  - `base.py` — `LLM(ABC)` 抽象接口，定义 `chat()` 方法
  - `openai.py` — OpenAI LLM 实现（原 OpenAIProtocol + OpenAICompatibleLLM 合并）
  - `anthropic.py` — Anthropic LLM 实现（原 AnthropicProtocol + AnthropicLLM 合并）
- **新增** `rag_server/embedding/` 目录：
  - `base.py` — `Embedding(ABC)` 抽象接口，定义 `embed()` 方法
  - `openai.py` — OpenAI Embedding 实现（原 OpenAIProtocol.embed + OpenAICompatibleEmbedding 合并）
  - `dashscope.py` — DashScope Embedding 实现（原名 dashscope_embedding.py，内容不变）
- **更新** `rag_server/registry.py`：注册路径从 `providers.llm` / `providers.embedding` 改为 `llm.openai` / `embedding.openai` 等
- **更新** 所有引用这些模块的导入路径（`__main__.py`、`pipeline/rag_pipeline.py` 等）
- **删除** `rag_server/protocols/__init__.py`、`rag_server/providers/__init__.py`

**BREAKING**: 内部导入路径变更，但外部接口（MCP 工具、CLI 命令、配置格式）不变。

- **修改** `rag_server/loaders/base.py`：`BaseLoader` 增加类属性 `extensions: List[str]`，子类声明自己支持的文件扩展名
- **修改** `rag_server/loaders/pdf.py`、`markdown.py`、`image.py`、`word.py`、`audio.py`、`video.py`：每个 Loader 添加 `extensions = [".pdf"]` 等声明
- **新增** 扩展名收集函数（`registry.py` 或 `loaders/__init__.py`）：`get_supported_extensions()`，从注册表自动收集所有 Loader 的扩展名
- **修改** `rag_server/stores/document.py`：`list_input_files()` 改为调用 `get_supported_extensions()`，不再硬编码扩展名列表
- **修改** `rag_server/pipeline/ingestion.py`：`_resolve_loader()` 改为遍历 Loader 注册表匹配扩展名，移除硬编码的 `loader_map`
- **新增** Capability：文件格式支持可插拔，新增格式只需加 Loader 文件声明 `extensions`，无需改其他代码
- **新增** `rag_server/registry.py`：`auto_register(package_name)` 自动导入包下所有模块触发 `@register`
- **修改** `rag_server/pipeline/rag_pipeline.py`：移除 4 行硬编码 import，改为调用 `auto_register()`
- **新增** Capability：LLM / Embedding 厂商自动发现，新增厂商只需在对应目录下加文件 + `@register`
- **新增** `rag_server/text/base.py`：`Splitter(ABC)` 抽象接口
- **修改** `rag_server/text/splitter.py`：`TextSplitter` 加 `@register("splitter", "default")`，实现 `Splitter`
- **新增** `rag_server/stores/persister.py`：`Persister(ABC)` + `FilePersister`（合并保存 MD + 保存图片）
- **新增** `rag_server/stores/vectorizer.py`：`Vectorizer(ABC)` + `ChromaVectorizer`（合并构建索引 + 嵌入 + Chroma）
- **修改** `rag_server/config.py`：新增 `PipelineConfig` 数据类（cleaner/splitter/persister/vectorizer provider），追加到 `Config`
- **修改** `rag_server/pipeline/ingestion.py`：`run()` 每步改为 Factory.create() + config 驱动，不再硬编码
- **新增** `rag_server/retrieval/base.py`：`Retriever(ABC)` + `Fuser(ABC)` 抽象接口
- **新增** `rag_server/retrieval/hybrid.py`：`HybridRetriever`，`@register("retriever", "hybrid")`，封装双路检索
- **修改** `rag_server/retrieval/fusion.py`：`HybridFusion` 加 `@register("fuser", "hybrid")`，实现 `Fuser`
- **新增** `rag_server/prompt/assembler.py`：`Assembler(ABC)` + `DefaultAssembler`，封装 Prompt 模板和裁剪策略
- **修改** `rag_server/config.py`：`RetrievalConfig` 新增 retriever/fuser/assembler provider 字段
- **修改** `rag_server/pipeline/rag_pipeline.py`：`query()` 精简为 4 步，全部由 config 驱动
- **修改** `config.yaml`：新增 `pipeline:` 段（cleaner/splitter/persister/vectorizer），`retrieval:` 新增 retriever/fuser/assembler，移除已废弃的 `stitcher:`
- **新增** 测试文件：对每个可插拔组件编写独立单元测试（cleaner / splitter / persister / fuser / assembler / retriever / loaders / vectorizer）
- **重命名** 多个文件、类名，使命名清晰一致（详见设计文档 14. 命名清理）
- **修复** `asr/dashscope.py`：SDK `Recognition.call()` API 变更 → 改为 httpx REST API
- **修复** `loaders/video.py`：ffmpeg 临时文件写入 input/ 目录导致重复处理 → 改到系统 temp 目录
- **更新** `.env` / `.env.example`：新增 ASR_PROVIDER / ASR_BASE_URL / ASR_API_KEY / ASR_MODEL
- **重命名** `config.yaml` 段名：`pipeline:` → `ingestion_pipeline:`，`retrieval:` → `query_pipeline:`，与代码类名一致
- **重命名** `config.py`：`PipelineConfig` → `IngestionPipelineConfig`，`RetrievalConfig` → `QueryPipelineConfig`
- **目录重组**：`llm/`、`embedding/`、`asr/` 移入 `models/` 父目录，纯物理归组，不改接口
- **重写分块算法**：从"段落独立成块"改为"步距累加 + 上下文重叠"；`chunk_size` 和 `stride` 由 config 控制，`overlap` 自动计算；解决标题类短文本成为独立小 chunk 的问题

## Capabilities

### New Capabilities

无。本 change 为纯重构，不引入新能力。

### New Capabilities（追加）

- **文件加载器可插拔**：新增文件格式只需创建 Loader 类并声明 `extensions`，无需修改 `document.py` 或 `ingestion.py` 的硬编码映射
- **LLM / Embedding 厂商自动发现**：新增厂商只需在 `llm/` 或 `embedding/` 下加文件 + `@register`，无需手动维护导入语句
- **Ingestion 管线全流程可插拔**：清洗/分块/持久化/向量化每步均有抽象接口 + 注册 + 工厂，由 config 驱动
- **RAG 查询管线全流程可插拔**：检索/融合/Prompt 组装每步均有抽象接口 + 注册 + 工厂，由 config 驱动

### Modified Capabilities（追加）

- **加载器系统**：从硬编码扩展名映射改为基于注册表的自动发现，行为不变，可扩展性提升
- **AI 能力层注册机制**：`rag_pipeline.py` 中 4 行硬编码 import 改为 `auto_register()` 自动扫描，新增厂商不再需要改此文件
- **Ingestion 管线**：从 8 步硬编码精简为 5 步 config 驱动，新增存储后端或向量库只需加文件 + 注册
- **RAG 查询管线**：从 5 步硬编码精简为 4 步 config 驱动（检索→融合→组装→LLM），每步可独立替换

## Impact

- **删除** `rag_server/protocols/`（4 文件）、`rag_server/providers/`（4 文件）
- **新增** `rag_server/llm/`、`rag_server/embedding/`（各 3-4 文件）、`rag_server/prompt/`（1 文件）
- **新增** `rag_server/text/base.py`、`rag_server/stores/persister.py`、`rag_server/stores/vectorizer.py`、`rag_server/retrieval/base.py`、`rag_server/retrieval/hybrid.py`
- **净新增**约 5 个文件（抽象接口 + 默认实现）
- **外部不感知**：MCP 工具、CLI 命令不变
- **配置 YAML 更新**：新增 `pipeline:` 段，`retrieval:` 新增 retriever/fuser/assembler 字段，移除已废弃的 `stitcher:`；后续命名清理会同步更新键名
- **命名清理**：`pipeline/rag_pipeline.py` → `pipeline/query.py`，`Persister`→`Storage`，`Vectorizer`→`Indexer`，`Assembler`→`PromptBuilder`，`Fuser`→`Ranker` 等（详见 design.md 14）
- Registry key 不变（仍为 `("llm", "openai")` / `("embedding", "dashscope")` 等）
- `pyproject.toml` 不变（依赖不变）
- `tests/` 导入路径需同步更新