## Why

构建一个内部知识库 RAG 系统，以 MCP 协议暴露给 LLM 客户端使用。当前团队内部积累了大量的 PDF、Markdown 和图片格式的文档，缺乏一个统一的知识检索和问答系统。需要一套解耦、可插拔、最小依赖的 RAG 方案，独立实现核心管线，避免对 LangChain/LlamaIndex 等重框架的强依赖。

## What Changes

新增整个 RAG 服务，包含以下核心模块：

- **Document Loader 层**: 支持 PDF（PyMuPDF）、Markdown、纯图片三种源文件的加载，统一输出为 MD + assets 的规范格式
- **Text Cleaner 层**: 可插拔的 MD 文本清洗组件，去除 PDF 提取带来的多余空格、断行、空段落等噪音
- **Text Splitter 层**: 基于段落边界的语义分块策略，超长段落按句号/逗号逐级降级切分，图片信息前自动分割保留上下文
- **Embedding Provider 层**: 基于 OpenAI 兼容协议的文本嵌入服务（支持 Ollama / OpenAI 等后端）
- **LLM Provider 层**: 支持 OpenAI 协议和 Anthropic 协议两种 LLM 调用方式，通过协议类抽象解耦
- **Vector Store 层**: 基于 Chroma 的向量存储（抽象接口，可替换为 Qdrant/FAISS 等）
- **BM25 索引层**: 基于 rank_bm25 的关键词检索，与向量检索构成双路混合检索
- **Ingestion 引擎**: 扫描 input 目录，自动完成文件加载、分块、索引构建和文件归档
- **RAGPipeline 编排层**: 将检索 + 生成串联的编排管线
- **MCP Server 层**: 将 RAG 能力以 MCP 工具和资源的形式暴露

## Capabilities

### New Capabilities

- `document-loading`: 从 PDF / Markdown / 图片源文件加载文档，统一转换为 MD 文本 + 图片资产的结构化输出
- `text-processing`: MD 文本清洗与分块处理，保证分块语义完整性
- `ingestion`: 扫描 input 目录，自动完成文档加载、分块、向量化/BM25索引构建，处理完成后将源文件归档到 processed 目录
- `embedding`: 文本嵌入服务，通过 OpenAI 兼容协议将文本转换为向量
- `retrieval`: 基于向量检索+BM25关键词检索的双路混合检索，支持可配置的融合比重
- `llm-generation`: 基于检索上下文的 LLM 问答生成，支持 OpenAI 协议和 Anthropic 协议两种后端，支持流式/非流式输出
- `rag-pipeline`: RAG 查询编排管线，串联检索、重排序、上下文组装和生成
- `web-ui`: 基于 Streamlit 的简易问答界面，通过浏览器输入问题并获取回答
- `mcp-server`: MCP 协议服务器，暴露 rag_query、ingest_documents、get_stats 三个工具，启动时不处理文件，首次查询时自动触发导入

### Modified Capabilities

无（新项目，尚无现有能力规格）

## Impact

- **新增项目**: 全新的 Python 项目，位于当前仓库根目录
- **核心依赖**: Python >=3.11, ChromaDB, PyMuPDF, MCP SDK, httpx, rank_bm25, jieba, dashscope
- **可选依赖**: streamlit（Web 界面）、pdfplumber（表格增强）、pytesseract/EasyOCR（图片 OCR）
- **架构影响**: 无（全新项目，不修改现有代码）
- **部署方式**: 以 MCP Server 为主要入口，不带子命令时启动 MCP Server（stdio 模式）；带子命令时进入 CLI 模式，提供 ingest、query、stats 三个命令
- **数据目录**:
  - `input/`：用户放入待处理文件
  - `processed/`：处理完成后源文件自动归档
  - `docs/`、`assets/`、`vector/`、`sparse/`：分别存储 MD 源文件、图片资产、Chroma 向量数据、BM25 索引
  - `index.json`：统一索引对照表，检索时按 chunk_id 查询全文