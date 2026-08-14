# MCP RAG Server

一个功能完善的 RAG（检索增强生成）知识库服务，通过 **MCP 协议** 暴露给 LLM 客户端原生使用。
---

## 快速开始

```bash
# 0. 安装 Python（推荐 3.11 ~ 3.13）
#     官网下载: https://www.python.org/downloads/
#     安装时勾选"Add Python to PATH"

# 1. 打开终端（cmd/PowerShell），cd 到本项目目录
cd 本项目路径
> 不会找路径？在文件管理器打开本项目文件夹，点击地址栏复制完整路径即可。

# 2. 创建虚拟环境（隔离项目依赖，不污染系统）
python -m venv .venv

# 激活虚拟环境
# Windows:
.venv\Scripts\activate
# Mac / Linux:
# source .venv/bin/activate

# 3. 安装本项目和依赖
pip install -e .

# 4. 配置 API Key
cp .env.example .env
# 编辑 .env 填入你的 API Key

# 5. 把文档放入 data/input/
# 支持：PDF、Markdown、Word、图片、音频、视频

# 6. 将文档录入知识库
python -m rag_server ingest

# 7. MCP 配置启动
### MCP 客户端配置

以 VS Code 的 Cline 插件为例，在 MCP 设置中添加：

```json
{
  "mcpServers": {
    "rag-server": {
      "autoApprove": [],
      "disabled": false,
      "timeout": 60,
      "type": "stdio",
      "command": "这里填本项目路径/.venv/Scripts/python.exe",
      "args": ["-m", "rag_server"],
      "cwd": "这里填本项目路径"
    }
  }
}
```


### CLI 命令

| 命令 | 说明 |
|------|------|
| `python -m rag_server ingest` | 扫描 `data/input/` 并导入文档 |
| `python -m rag_server query <问题>` | 查询问答 |
| `python -m rag_server stats` | 查看知识库统计 |
| `python -m rag_server clean` | 清空所有索引数据 |
| 命令 | 说明 |
|------|------|
| `python -m rag_server ingest` | 扫描 `data/input/` 并导入文档 |
| `python -m rag_server query <问题>` | 查询问答 |
| `python -m rag_server stats` | 查看知识库统计 |
| `python -m rag_server clean` | 清空所有索引数据 |
```
---

## 配置说明

所有配置在 `config.yaml` 中，可通过环境变量覆盖。

### LLM（大语言模型）

| 字段 | 默认值 | 说明 |
|------|--------|------|
| `llm.provider` | `openai` | LLM 提供商：`openai` \ `anthropic`（推荐写 .env 中）|
| `llm.base_url` | `https://api.openai.com/v1` | API 地址（推荐写 .env 中）|
| `llm.api_key` | `""` | API Key（推荐写 .env 中）|
| `llm.model` | `gpt-4o-mini` | 模型名称（推荐写 .env 中）|
| `llm.temperature` | `0.7` | 生成温度：0.0 ~ 2.0 |
| `llm.max_chars` | `30000` | 输入上下文最大字符数 |
| `llm.stream` | `true` | 是否流式返回 |

### Embedding（文本嵌入）

| 字段 | 默认值 | 说明 |
|------|--------|------|
| `embedding.provider` | `openai` | 嵌入提供商：`openai` \ `dashscope`（推荐写 .env 中）|
| `embedding.base_url` | `https://api.openai.com/v1` | API 地址（推荐写 .env 中）|
| `embedding.api_key` | `""` | API Key（推荐写 .env 中）|
| `embedding.model` | `text-embedding-3-small` | 嵌入模型名称（推荐写 .env 中）|

### ASR（语音识别）

| 字段 | 默认值 | 说明 |
|------|--------|------|
| `asr.provider` | `dashscope` | ASR 提供商：`dashscope`（推荐写 .env 中）|
| `asr.base_url` | DashScope ASR 接口地址 | API 地址（推荐写 .env 中）|
| `asr.api_key` | `""` | API Key（推荐写 .env 中）|
| `asr.model` | `qwen-audio-3.0-asr-flash` | ASR 模型名称（推荐写 .env 中）|

### Ingestion Pipeline（文件处理管线）

| 字段 | 默认值 | 说明 |
|------|--------|------|
| `ingestion_pipeline.cleaner_provider` | `default` | 文本清洗：`default` \| `minimal` \| `verbose` |
| `ingestion_pipeline.splitter_provider` | `default` | 文本分块 |
| `ingestion_pipeline.chunk_size` | `1000` | 目标分块大小（字符数） |
| `ingestion_pipeline.stride` | `800` | 滑动步距（字符数） |
| `ingestion_pipeline.storage_provider` | `file` | 持久化方式：`file` |
| `ingestion_pipeline.indexer_provider` | `chroma` | 索引方式：`chroma` |

### Query Pipeline（问答管线）

| 字段 | 默认值 | 说明 |
|------|--------|------|
| `query_pipeline.retriever_provider` | `hybrid` | 检索方式：`hybrid` \ `vector_only` \ `bm25_only` |
| `query_pipeline.ranker_provider` | `hybrid` | 排序方式：`hybrid`(权重融合) \ `rrf` |
| `query_pipeline.prompt_builder_provider` | `default` | 提示词组装方式 |
| `query_pipeline.vector_weight` | `0.5` | 向量检索权重（0.0 ~ 1.0） |
| `query_pipeline.vector_top_k` | `20` | 向量检索返回前 N 条 |
| `query_pipeline.bm25_top_k` | `20` | BM25 检索返回前 N 条 |
| `query_pipeline.final_top_k` | `10` | 融合后最终返回前 N 条 |

### Data（数据目录）

| 字段 | 默认值 | 说明 |
|------|--------|------|
| `data.root` | `./data` | 数据根目录 |

---

## 支持的文件格式

| 格式 | 扩展名 | 加载器 | 额外依赖 |
|------|--------|--------|---------|
| PDF | `.pdf` | PDFLoader (PyMuPDF) | `pymupdf` |
| Markdown | `.md` | MarkdownLoader | — |
| Word | `.docx` | WordLoader (python-docx) | `python-docx` |
| 图片 | `.png`, `.jpg`, `.jpeg`, `.gif`, `.bmp` | ImageLoader | `pytesseract`（可选） |
| 音频 | `.mp3`, `.wav`, `.m4a` | AudioLoader (ASR) | `dashscope` |
| 视频 | `.mp4`, `.avi`, `.mov`, `.mkv` | VideoLoader (ffmpeg + ASR) | `dashscope` + ffmpeg |

---

## MCP 工具

服务通过 `FastMCP` 注册了 3 个工具：

| 工具 | 参数 | 说明 |
|------|-------|------|
| `rag_query` | `query: str`, `stream: bool = True` | RAG 问答。仅查询 |
| `ingest_documents` | （无） | 扫描 `data/input/`，处理全部文件经过导入管线 |
| `get_stats` | （无） | 返回 `{files: int, chunks: int}` 知识库状态 |

---

## CLI 命令

| 命令 | 说明 |
|------|------|
| `python -m rag_server ingest` | 扫描 `data/input/` 并导入文档 |
| `python -m rag_server query <问题>` | 查询问答 |
| `python -m rag_server stats` | 查看知识库统计 |
| `python -m rag_server clean` | 清空所有索引数据 |

---

## Web 界面（Streamlit）

提供基于 Streamlit 的简易问答页面，供人手动查询：

```bash
streamlit run rag_server/interfaces/web.py
```

侧边栏控制检索参数；主区域输入问题和流式回答。

---

## Ingestion Pipeline (文件处理管线)

放入 `data/input/` 的文件经过以下流程处理：

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐      
│  Input   │──▶│  Loader  │──▶│  Cleaner │───▶│ Splitter │
│  Files   │    │(per ext) │    │(default) │    │(stride)  │
│ (输入文件)│   │(扩展名匹配)│   │ (文本清洗)│    │(文本分割) │
└──────────┘    └──────────┘    └──────────┘    └──────────┘
                                                    │
                                                    ▼
                                              ┌──────────┐
                                              │  Indexer │
                                              │(per file)│
                                              │(构建索引) │
                                              └──────────┘
                                                    │
                                                    ▼
                              ┌─────────────────────────────────┐
                              │                                 │
                              ▼                                 ▼
                        ┌──────────┐                     ┌──────────┐
                        │  Chroma  │                     │   BM25   │
                        │ (vector) │                     │ (sparse) │
                        │ (向量库)  │                     │ (关键词) │
                        └──────────┘                     └──────────┘
                        ┌──────────┐
                        │  index   │
                        │  .json   │
                        │(存原文块) │
                        └──────────┘
```

- 每个文件根据扩展名自动匹配 **Loader**（PDF / MD / Word / 图片 / 音频 / 视频）
- 文本经过 **Cleaner** 清洗（合并断行、压缩空白、保留结构）
- **Splitter** 按段落、分块大小、滑动步距控制分块，前后各带上下文重叠
- 每个 Chunk 经 **Embedding** 向量化后存入 **Chroma** 向量数据库
- 所有 Chunk 写入 **index.json**（chunk_id → 全文 + 元数据）
- 全部文件处理完毕后，从 index.json 全量重建 **BM25** 关键词索引

---

## Query Pipeline (问答管线)

用户提问经过以下流程处理：

```
                ┌──────────────────────────────┐
                │              Query           │
                │           (用户问题)          │
                └──────────────────────────────┘
                              │
                              ▼
                ┌──────────────────────────────┐
                │       Hybrid Retrieve        │
                │         (双路检索)            │
                │  ┌──────────┐  ┌──────────┐  │
                │  │  Vector  │  │   BM25   │  │
                │  │(Chroma)  │  │(jieba)   │  │
                │  │ (语义匹配)│  │ (关键词) │  │
                │  └──────────┘  └──────────┘  │
                └──────────┬───────────────────┘
                              │
                              ▼
                ┌──────────────────────────────┐
                │           Rank               │
                │         (融合排序)            │
                │  weighted fusion (α×vector   │
                │  + (1-α)×bm25) → top-K       │
                └──────────┬───────────────────┘
                              │
                              ▼
                ┌──────────────────────────────┐
                │       Build Prompt           │
                │       (组装提示词)            │
                │  system template + context   │
                │  + user question             │
                └──────────┬───────────────────┘
                              │
                              ▼
                ┌──────────────────────────────┐
                │      LLM Generation          │
                │        (LLM生成)             │
                │  OpenAI / Anthropic          │
                │  streaming supported         │
                └──────────┬───────────────────┘
                              │
                              ▼
                ┌──────────────────────────────┐
                │           Answer             │
                │          (回答)              │
                └──────────────────────────────┘
```

- **双路检索**: 向量检索（Chroma 语义匹配）+ BM25（jieba 分词关键词匹配）
- **融合排序**: 加权融合 — 可配置 `vector_weight` 控制向量和 BM25 的权重比例
- **组装提示词**: 检索到的 Chunk 拼接系统提示词和用户问题
- **LLM 生成**: 调用配置的 LLM（OpenAI 或 Anthropic）生成回答，支持流式输出

---

## Pluggable Architecture (可插拔架构)

所有核心组件通过 **ABC + @register + Factory** 模式实现可插拔，由 `config.yaml` 驱动：

| 组件 | 抽象接口 | 默认实现 | 注册 Key |
|------|---------|---------|---------|
| Loader | BaseLoader | PDFLoader | `("loader", "pdf")` |
| Cleaner | BaseCleaner | DefaultCleaner | `("cleaner", "default")` |
| Splitter | Splitter | TextSplitter | `("splitter", "default")` |
| Storage | Storage | FileStorage | `("storage", "file")` |
| Indexer | Indexer | ChromaIndexer | `("indexer", "chroma")` |
| Retriever | Retriever | HybridRetriever | `("retriever", "hybrid")` |
| Ranker | Ranker | HybridRanker | `("ranker", "hybrid")` |
| PromptBuilder | PromptBuilder | DefaultPromptBuilder | `("prompt_builder", "default")` |
| LLM | LLM | OpenAILLM | `("llm", "openai")` |
| Embedding | Embedding | OpenAIEmbedding | `("embedding", "openai")` |
| ASR | ASR | DashScopeASR | `("asr", "dashscope")` |

通过 `config.yaml` 切换实现

新增实现 = 新建文件 + `@register`，零改现有代码。

---

## 数据目录

```
data/
├─ input/         # 放入待处理的文档
├─ processed/     # 已处理完成的文件归档
├─ docs/          # 转换后的 MD 原文
├─ assets/        # 从文档中提取的图片文件
├─ vector/       # Chroma 持久化数据
├─ sparse/        # BM25 持久化索引
└─ index.json    # chunk_id → 全文 + 元数据 对照表
```