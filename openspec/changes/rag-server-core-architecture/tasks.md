## 1. 项目初始化

- [x] 1.1 创建项目目录结构和包初始化文件
  - `rag_server/__init__.py`
  - `rag_server/__main__.py`
  - `rag_server/protocols/__init__.py`
  - `rag_server/providers/__init__.py`
  - `rag_server/loaders/__init__.py`
  - `rag_server/text/__init__.py`
  - `rag_server/stores/__init__.py`
  - `rag_server/retrieval/__init__.py`
  - `rag_server/pipeline/__init__.py`
  - `rag_server/interfaces/__init__.py`
  - `tests/__init__.py`
  - `.gitignore`
  - `.env.example`
  - `README.md`
  - `data/input/`、`data/processed/` 等目录骨架
- [x] 1.2 编写 `pyproject.toml`，声明核心依赖和可选依赖（extras）
- [x] 1.3 实现 `rag_server/config.py` + 默认 `config.yaml`（YAML + 环境变量覆盖）

## 2. 协议层 + 注册表

- [x] 2.1 实现注册表 `rag_server/registry.py`：`@register()` 装饰器 + `Factory.create()`
- [x] 2.2 实现 `rag_server/protocols/base.py`：`BaseProtocol(ABC)`
- [x] 2.3 实现 `rag_server/protocols/openai.py`：`OpenAIProtocol`（chat + embed 端点）
- [x] 2.4 实现 `rag_server/protocols/anthropic.py`：`AnthropicProtocol`（messages 端点）

## 3. AI 能力层

- [x] 3.1 实现 `rag_server/providers/llm.py`：`LLMProvider(ABC)` + `@register("llm", "openai") OpenAICompatibleLLM` + `@register("llm", "anthropic") AnthropicLLM`
- [x] 3.2 实现 `rag_server/providers/embedding.py`：`EmbeddingProvider(ABC)` + `@register("embedding", "openai") OpenAICompatibleEmbedding`
- [x] 3.3 实现 `rag_server/providers/dashscope_embedding.py`：`@register("embedding", "dashscope") DashScopeEmbedding`（分批处理，单次最多 20 条）

## 4. 文档加载层

- [x] 4.1 定义 `rag_server/loaders/base.py`：`BaseLoader(ABC)`（输入 → MD 文本 + assets + metadata）
- [x] 4.2 实现 `rag_server/loaders/pdf.py`：`@register("loader", "pdf") PDFLoader`（PyMuPDF，坐标排序，OCR）
- [x] 4.3 实现 `rag_server/loaders/markdown.py`：`@register("loader", "md") MarkdownLoader`（YAML frontmatter，内嵌图片检测）
- [x] 4.4 实现 `rag_server/loaders/image.py`：`@register("loader", "image") ImageLoader`（图转文 + OCR，支持 text_only/auto/ocr_all/multimodal）

## 5. 文本处理层

- [x] 5.1 实现 `rag_server/text/cleaner.py`：`BaseCleaner(ABC)` + `@register("cleaner", "default") DefaultCleaner` + `minimal` / `verbose`
- [x] 5.2 定义 `rag_server/text/chunk.py`：`Chunk` dataclass（id / doc_id / content / start_char / end_char / metadata）
- [x] 5.3 实现 `rag_server/text/splitter.py`：`TextSplitter`（段落优先 → 句号 → 逗号降级，图片前切分，重叠保留上下文）

## 6. 存储层

- [x] 6.1 实现 `rag_server/stores/base.py`：`VectorStore(ABC)`
- [x] 6.2 实现 `rag_server/stores/chroma.py`：`@register("vs", "chroma") ChromaStore`（只存向量 + chunk_id）
- [x] 6.3 实现 `rag_server/stores/document.py`：`DocumentStore`（MD → docs/，资产 → assets/）
- [x] 6.4 实现 `rag_server/stores/index_store.py`：`IndexStore`（index.json 的 chunk_id → 全文 + metadata 读写）

## 7. 导入引擎（Ingestion）

- [x] 7.1 实现 `rag_server/pipeline/ingestion.py` 核心流程：扫描 input/ → 逐文件 Loader → Cleaner → Splitter
- [x] 7.2 实现归档逻辑：MD → docs/，图片 → assets/，源文件 → processed/
- [x] 7.3 实现索引更新：追加 index.json → 嵌入 Chroma → 全量重建 BM25
- [x] 7.4 实现错误处理和日志记录（每文件处理结果、耗时）

## 8. 检索层

- [x] 8.1 实现 `rag_server/retrieval/bm25.py`：`BM25Index`（rank_bm25 + jieba，从 index.json 重建）
- [x] 8.2 实现 Chroma 向量检索（按相似度取 Top-K，返回 chunk_id + 分）
- [x] 8.3 实现 `rag_server/retrieval/fusion.py`：`HybridFusion`（加权融合 `α × norm(vec) + (1-α) × norm(bm25)`）
- [x] 8.4 实现 `rag_server/retrieval/stitcher.py`：`ChunkStitcher`（可选，默认关闭）

## 9. RAG 查询管线

- [x] 9.1 实现 `rag_server/pipeline/rag_pipeline.py`：`RAGPipeline` 编排类
- [x] 9.2 实现上下文组装（system prompt + 检索结果 + 用户问题）
- [x] 9.3 实现 Token 裁剪（超 `max_chars` 时从低分 chunk 丢弃）
- [x] 9.4 实现 LLM 生成（调用 LLMProvider，支持流式/非流式输出）

## 10. 接口层

- [x] 10.1 实现 `rag_server/__main__.py`：入口分发（无参数 → MCP 模式，子命令 → CLI 模式）
- [x] 10.2 实现 `rag_server/interfaces/cli.py`：CLI 子命令（ingest / query / stats）
- [x] 10.3 实现 `rag_server/interfaces/mcp.py`：MCP Server（rag_query / ingest_documents / get_stats 三个工具 + 首次查询自动导入）
- [x] 10.4 实现 `rag_server/interfaces/web.py`：Streamlit 界面（主区问答 + 侧边栏参数 + 知识库状态）

## 11. 集成测试

- [x] 11.1 验证全链路集成测试（ingest → query → 返回结果）

## 12. ASR 语音识别层

- [x] 12.1 创建 `rag_server/asr/` 目录和 `rag_server/asr/__init__.py`
- [x] 12.2 创建 `rag_server/asr/base.py`：`ASR(ABC)` 抽象接口，定义 `transcribe(audio_path) → str`
- [x] 12.3 创建 `rag_server/asr/dashscope.py`：`@register("asr", "dashscope") DashScopeASR`（调用阿里云语音识别 API，将音频文件转为文字）

## 13. Word 文档加载器

- [x] 13.1 安装依赖 `python-docx`（读取 .docx）
- [x] 13.2 创建 `rag_server/loaders/word.py`：`@register("loader", "docx") WordLoader`（支持 .docx，提取文本转为 MD；.doc 旧格式暂不支持）
- [x] 13.3 在 `pyproject.toml` 的 `dependencies` 中添加 `python-docx`

## 14. 音频/视频文档加载器

- [x] 14.1 安装 FFmpeg（Windows 已安装）
- [x] 14.2 创建 `rag_server/loaders/video.py`：`@register("loader", "video") VideoLoader`（step 1: ffmpeg 提取音频 → step 2: 调用 ASR 转文字 → 输出 MD）
- [x] 14.3 创建 `rag_server/loaders/audio.py`：`@register("loader", "audio") AudioLoader`（支持 .mp3/.wav/.m4a，直接调用 ASR 转文字）
- [x] 14.4 在 `rag_server/pipeline/ingestion.py` 中添加 import，触发注册

## 15. 更新导入引擎

- [x] 15.1 在 `rag_server/pipeline/ingestion.py` 的 `_resolve_loader()` 中添加 .doc/.docx/.mp4/.avi/.mov/.mkv 的文件类型映射
- [x] 15.2 验证新 loader 注册成功（Loader: docx/audio/video ✓, ASR: dashscope ✓）