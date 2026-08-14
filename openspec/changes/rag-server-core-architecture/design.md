## Context

这是一个全新的 RAG 项目，目标是为内部知识库提供基于检索增强生成的问答能力，并以 MCP 协议暴露给 LLM 客户端。项目从零开始搭建，核心设计原则是解耦、可插拔、最小依赖。

项目的技术约束和前提：
- **语言**: Python >= 3.11
- **框架策略**: 不依赖 LangChain / LlamaIndex 等重框架，核心管线自行实现
- **架构模式**: ABC 抽象接口 + Registry 注册表 + 工厂方法 + 依赖注入
- **依赖管理**: 核心依赖最小化，可选依赖通过 extras 声明（`pip install my-rag[chroma]`）
- **MCP 暴露**: 最终以 MCP 协议 Server 形式对外提供服务

## Goals / Non-Goals

### Goals

- 构建一套从文档加载到答案生成的全链路 RAG 管线
- 所有核心模块通过抽象接口解耦，实现可替换
- 支持 PDF、Markdown、纯图片三种源文件的加载
- 所有源文件统一转换为 Markdown（MD）+ 图片资产（assets）的规范格式
- 通过 Registry 和工厂模式实现组件的可插拔
- 支持 OpenAI 兼容协议和 Anthropic 协议两种 LLM 后端
- 文本嵌入仅通过 OpenAI 兼容协议（Anthropic 不提供嵌入服务）

### Non-Goals

- 不实现分布式部署或多节点协同
- 不提供实时文档同步/监听机制（文档变更需手动或定时触发重载）
- 不内置用户认证和权限管理（留给外层或 MCP Host 解决）
- 不处理非文本格式（音频、视频）

## Decisions

### 1. 整体架构风格：ABC + Registry + Factory

所有核心组件通过 Abstract Base Class 定义接口，通过 Registry 注册实现类，通过工厂方法创建实例。

```
接口层 (ABC)       注册层 (Registry)        实现层
────────────────    ────────────────        ────────────────
VectorStore(ABC) ─→ @register("vs","chroma") ─→ ChromaStore
                   @register("vs","qdrant")  ─→ QdrantStore
LLMProvider(ABC) ─→ @register("llm","openai") ─→ OpenAICompatibleLLM
                   @register("llm","anthropic")─→ AnthropicLLM
```

**Rationale**: 保持一致性——所有组件遵循同样的创建和替换模式，降低学习成本。

### 2. 依赖管理：延迟导入 + extras

```toml
[project.optional-dependencies]
chroma = ["chromadb>=0.5.0"]
qdrant = ["qdrant-client>=1.9.0"]
pdf = ["PyMuPDF>=1.23.0"]
```

每个实现类在 `__init__` 中才触发 import，配置未选中的组件不会加载。

```python
class ChromaStore(VectorStore):
    def __init__(self, **config):
        import chromadb  # ← 仅在此处导入
        ...
```

**Rationale**: 用户只需安装他实际用到的依赖，不会因为没用 Chroma 却必须装 chromadb。

### 3. LLM 协议：两个协议类

设计为协议类 + 能力接口两层：

- **协议层**（`OpenAIProtocol`, `AnthropicProtocol`）：封装底层 HTTP 调用，对应协议各端点
- **能力层**（`LLMProvider`, `EmbeddingProvider`）：薄适配层，组合协议实例

```
OpenAIProtocol(base_url, api_key)
  ├── chat(messages, model)       → POST /v1/chat/completions
  └── embed(texts, model)         → POST /v1/embeddings

AnthropicProtocol(api_key)
  └── chat(messages, model)       → POST /v1/messages

LLMProvider (接口)  ── OpenAICompatibleLLM(protocol: OpenAIProtocol)
                    ── AnthropicLLM(protocol: AnthropicProtocol)

EmbeddingProvider (接口)  ── OpenAICompatibleEmbedding(protocol: OpenAIProtocol)
                            ── DashScopeEmbedding(dashscope SDK)
```

**DashScope 嵌入特殊说明**：Aliyun DashScope API 单次最多嵌入 20 条文本，实现中自动分批处理。
```

**Rationale**: 协议类是底层通信的封装，能力类是上层业务接口。职责分离，且 OpenAI 协议同时覆盖 LLM 和 Embedding 两种能力。

### 4. 文档加载管线：Loader → MD + assets

所有源文件经过 Loader 后统一输出为 MD 文本 + 图片资产：

```
源文件 → Loader → MD 文本 + assets/图片 + metadata
```

#### 4a. PDFLoader

基于 PyMuPDF，提取文本和图片，保留坐标信息用于重建正确阅读顺序和图文关联。

- 文本提取：`page.get_text("blocks")` 获取带坐标的文本块，按 (y, x) 排序
- 图片提取：`doc.extract_image(xref)` 获取内嵌图片，bbox 确定位置
- 扫描件检测：文本块极少但有图片的页面，渲染后 OCR 处理

#### 4b. ImageLoader

针对纯图片文件（截图、图表等），依赖图转文模型生成描述，可选 OCR 提取文字。

- 核心：Image-to-text 模型（LLaVA / GPT-4o / Claude 等）生成语义描述
- 增强：OCR 提取图片中可见文字
- 输出：MD 包含图转文描述 + OCR 文本 + 原图引用

支持策略：
| 策略 | 行为 | 适用场景 |
|------|------|---------|
| `text_only` | 跳过图片，仅处理文本 | 纯文本 PDF |
| `auto`（默认）| 扫描件 OCR，普通文档取文字，图表存图 | 混合文档 |
| `ocr_all` | 每页渲染后全量 OCR | 全扫描件 |
| `multimodal` | 文本 + 存原图，给多模态 LLM 使用 | 图表密集型 |

#### 4c. MarkdownLoader

直接读取 .md 文件，提取 YAML frontmatter 作为 metadata，检测内嵌图片并提取为 assets。

#### 4d. 存储结构

```
data/
  docs/                     ← MD 文件
    2024年报.md
  assets/                   ← 图片文件
    2024年报/
      p1_0.png
      p3_1.png
  .asset_index.json         ← 全局资产索引
```

MD 文件中通过 Markdown 图片语法引用 assets，HTML 注释携带元信息：

```markdown
![销售趋势图](assets/2024年报/p1_0.png)
<!-- asset-id: p1_0 | page: 1 | type: chart | description: ... -->
```

### 5. TextCleaner：可插拔清洗组件

| 注册名 | 作用 |
|--------|------|
| `default` | 标准清洗：去多余空格、合行、规格化换行、修标点 |
| `minimal` | 仅去多余空格和空行 |
| `verbose` | 仅去首尾空格，保留原始排版 |

配置驱动选择：

```yaml
loader:
  config:
    cleaner:
      provider: "default"
```

### 6. 分块策略：语义优先，段落 → 句号 → 逗号逐级降级

以段落为基本单位，段落内如果超出块大小限制则按句号/逗号降级切分，保证语义完整性。

```
                       段落（双空行分隔）
                              │
                    ┌─────────┴─────────┐
                    ▼                     ▼
                在限制内              超出限制
                    │                     │
                    │              ┌──────┴──────┐
                    ▼              ▼              ▼
              整段保留            句号切分        逗号切分
                    │         （语义较完整）  （最后保底）
                    │
                    ▼
              写入 Chunk
```

图片处理规则：在图片信息（![] + <!-- -->）前切分，利用重叠保留上段落尾部作为图片块的上下文。

```
Chunk N                     Chunk N+1（含重叠）
┌──────────────────┐       ┌──────────────────┐
│  段落正文...       │       │  段落正文尾部...    │ ← 200字符重叠
│  段落正文...       │       │  ![](assets/... )  │
│  ↑ 在此切分        │       │  <!-- ... -->      │
└──────────────────┘       └──────────────────┘
                            因重叠，图片块拥有上下文
```

**Rationale**: 段落是自然语义单位，按句切分保持了子句完整性。图片前切分保证了图文关联不丢失——利用重叠机制，图片块天然包含前一段尾部内容。

#### 6a. 分块参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| 块大小 | 1000 字符 | 每块最大尺寸（硬限制，不因语义边界超出）|
| 重叠长度 | 200 字符 | 前后块之间的重叠窗口 |
| 最后一块 | 保留 | 不合并，独立保留 |

#### 6b. Chunk 数据结构

```python
@dataclass
class Chunk:
    id: str                # md5("{doc_id}_{index}_{content[:64]}")[:16]
    doc_id: str            # md5(源文件路径)[:12]
    chunk_index: int       # 文件内第几块（从0开始）
    content: str           # 切分文本
    start_char: int        # 在源文件中的起始位置
    end_char: int          # 结束位置
    metadata: dict         # 来源路径、图片引用等
```

#### 6c. 切分流程

```
def split_text(text, chunk_size=1000, overlap=200):
    paragraphs = split_by_blank_lines(text)           # 段落为一级边界
    chunks = []
    for para in paragraphs:
        if len(para) <= chunk_size:
            chunks.append(para)                       # 整段保留
        else:
            sentences = split_by_sentence_boundaries(para, ['。', '！', '？'])
            if any(len(s) > chunk_size for s in sentences):
                sentences = split_by_comma(para)      # 降级到逗号
            chunks.extend(assemble(sentences, chunk_size, overlap))
    return chunks
```

#### 6d. 特殊内容处理

| 内容类型 | 处理方式 |
|----------|--------|
| 表格/代码/列表 | 视为段落整体，不拆分 |
| 图片信息（![] + <!-- -->） | 在图片前切分，利用重叠保留上文 |
| 图片信息超长 | 截断 description 尾部；全截断仍超则报错 |
| 最后一块不足 chunk_size | 独立保留，不与上块合并 |

### 7. 存储层与数据目录结构

#### 7a. 目录结构

```
data/
  ├── input/            ← 待处理文件（用户放入，触发导入后扫描此目录）
  ├── processed/        ← 已处理文件（处理完成后自动移入）
  ├── docs/             ← 转换后的完整 MD 源文件（重新分块 / MCP 全文查看用）
  ├── assets/           ← 从文档提取的图片资产（按文档名分目录存放）
  ├── vector/           ← Chroma 持久化数据（只存向量 + chunk_id，不含原文）
  ├── sparse/           ← BM25 持久化数据（重建时从 index.json 读取全量文本）
  └── index.json        ← 索引对照表（chunk_id → 全文 + metadata，检索时的文本来源）
```

各目录路径通过配置指定，默认值如上。

#### 7b. 组件数据存储策略

| 组件 | 存储内容 | 数据位置 | 说明 |
|------|---------|---------|------|
| Chroma | 向量 + chunk_id | `vector/` | 仅用于向量相似度检索，不含文本 |
| BM25 | 稀疏索引 + 元数据 | `sparse/` | 仅用于关键词检索，文本重建时从 index.json 读取 |
| index.json | chunk_id → 全文 + metadata | 根目录 | 唯一文本仓库，检索时通过 chunk_id 查全文 |
| DocumentStore | MD 原文全文 | `docs/` | 原始文档，用于重新分块或人工查阅 |
| AssetStore | 图片文件 | `assets/` | 文档内嵌图片，按 `文档名/` 分目录 |

#### 7c. index.json 格式

```json
{
  "chunk_a1b2": {
    "text": "## 营收概况\n2024年全年营收...",
    "doc_id": "doc_2024年报",
    "doc_path": "docs/2024年报.md",
    "chunk_index": 0,
    "start_char": 0,
    "end_char": 1024,
    "metadata": {}
  },
  "chunk_c3d4": { ... }
}
```

### 8. 导入触发流程（Ingestion）

手动或定时触发，通过 CLI 命令执行：

```
rag-server ingest [--input ./data/input] [--output ./data]
```

```
开始 ──→ 扫描 input/ 目录 ──→ 有文件？
                                  │
                    ┌─────────────┴─────────────┐
                    ▼                            ▼
                有文件                         无文件 → 退出
                    │
                    ▼
          对每个文件：
          ├── Loader（PDF/MD/Image）
          ├── TextCleaner
          ├── 分块（按段落优先策略）
          ├── 新 chunk → 追加到 index.json
          ├── 新 chunk → 嵌入 → 追加到 Chroma
          ├── MD 原文 → docs/
          ├── 图片 → assets/
          ├── 源文件 → 移入 processed/
          └── 日志记录（处理结果、耗时）
                    │
                    ▼
          所有文件处理完毕
                    │
                    ▼
          从 index.json 全量重建 BM25
                    │
                    ▼
          完成
```

处理原则：
- **逐文件处理**：每处理完一个文件立即移入 `processed/`，避免中断后重复处理
- **最后重建 BM25**：所有文件处理完后，统一读 index.json 全量重建（rank_bm25 不支持增量更新）
- **日志记录**：每个文件的处理结果、耗时、错误信息
- **幂等性**：因中断未处理的文件保留在 input/ 中，下次继续

### 9. 检索策略：双路混合检索

分块完成后，每个 Chunk 同时被两个索引覆盖：

```
每个 Chunk → ┌──────────────────┐
             │  向量化 → Chroma  │
             ├──────────────────┤
             │  关键词 → BM25   │
             └──────────────────┘
```

#### 9a. 向量检索（Chroma）

- 语义匹配，基于 OpenAI 兼容协议的 Embedding 服务
- 检索参数：`vector_top_k = 20`
- 返回 Chunk 及相似度分数

#### 9b. 关键词检索（BM25）

- 精确匹配，基于 `rank_bm25` 库
- 中文预处理使用 jieba 分词
- 持久化：BM25 数据存 `sparse/` 目录，源文本从 index.json 读取
- 检索参数：`bm25_top_k = 20`

```python
# 加载 / 重建（从 index.json 读取全量文本）
with open("index.json") as f:
    chunks = json.load(f)
all_texts = [chunk["text"] for chunk in chunks]   # 只取文本列表
tokenized = [jieba.lcut(t) for t in all_texts]
bm25 = BM25Okapi(tokenized)

# 检索
tokenized_query = jieba.lcut(query)
scores = bm25.get_scores(tokenized_query)
```

#### 9c. 混合融合策略

```
向量检索（Chroma）── Top 20 ──┐
                               ├── 加权融合 ──→ Top-N → Stitcher → LLM
BM25 检索 ──────── Top 20 ──┘
```

融合公式：
```
最终得分 = α × normalize(vec_score) + (1-α) × normalize(bm25_score)

α: vector_weight，默认 0.5（可配置）
```

归一化方法：Min-Max 归一化到 [0, 1] 区间。

配置参数：
```yaml
retrieval:
  hybrid:
    vector_weight: 0.5        # 向量检索比重（默认 0.5，0=纯BM25，1=纯向量）
    vector_top_k: 20          # 向量检索取 Top-20
    bm25_top_k: 20            # BM25 取 Top-20
    final_top_k: 10           # 最终输出给下游的条数
```

### 10. 拼接策略：ChunkStitcher（可选，默认关闭）

可选功能，关闭时直接返回召回的所有 chunk 原文。开启后，召回连续 chunk 时根据 `start_char` / `end_char` 区间去重拼接，去除重叠部分，返回连续的原始内容。

| 配置 | 默认值 | 说明 |
|------|--------|------|
| `stitcher.enabled` | `false` | 是否启用拼接 |
| `stitcher.dedup` | `true` | 是否去除重叠部分 |

**Rationale**: 默认不拼接——大多数场景下单独召回 chunk 已满足需求，拼接引入额外计算。需要完整上下文时（如摘要生成）再开启。

### 11. RAG 查询管线

用户查询到最终回答的完整流程：

```
用户提问
  │
  ▼
双路检索（第 9 节）
  ├── Chroma → Top 20
  ├── BM25 → Top 20
  └── 融合 → Top N（默认 10）
  │
  ▼
可选拼接（第 10 节）
  │
  ▼
上下文组装
  ├── 拼入 system prompt
  ├── 拼入 chunk 原文（带来源标记）
  └── Token 裁剪（超限时从低分 chunk 丢弃）
  │
  ▼
LLM 生成
  ├── 调用 LLM（OpenAI / Anthropic）
  ├── 默认流式输出
  └── 返回答案（不带来源标记）
```

#### 11a. 上下文组装格式

```text
你是一个知识库助手。请基于以下文档内容回答问题。
如果文档中没有相关信息，直接说"未找到相关信息"，不要编造。

文档内容：

--- 来源：2024年报.md（第3段）---
[chunk 原文...]

--- 来源：系统架构.md（第1段）---
[chunk 原文...]

---

用户问题：[用户输入]
```

#### 11b. Token 限制

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `llm.max_chars` | 30000 | 传给 LLM 的上下文最大字符数 |
| `llm.stream` | `true` | 是否流式输出 |

超过 `max_chars` 时，从分数最低的 chunk 开始丢弃，直到适配限制。

#### 11c. 配置参数

```yaml
llm:
  provider: openai           # openai / anthropic
  model: gpt-4o-mini         # 模型名
  max_chars: 30000           # 上下文最大字符数
  stream: true               # 流式输出
  temperature: 0.7           # 生成温度
```

**Rationale**: 单次查询不保留对话历史，简化存储和上下文管理。不标记来源避免干扰回答的可读性。

### 12. 接口层

系统提供三种访问方式：MCP Server（主入口）、CLI 模式、Web 界面。

#### 12a. MCP Server 启动方式

MCP Host（如 Claude Desktop）通过 stdio 启动 rag-server 子进程：

```
MCP Host
  │
  ├── 启动子进程：rag-server
  │       │
  │       ├── 快速初始化（不处理文件）
  │       ├── 注册工具列表
  │       └── 通过 stdio 等待工具调用
```

#### 12b. MCP 工具定义

| Tool | 触发时机 | 说明 |
|------|---------|------|
| `rag_query` | 用户提问 | 正常问答。首次调用时若 input/ 有待处理文件，自动先跑 ingest 再回答 |
| `ingest_documents` | 管理员手动 | 立即触发文件处理工作流 |
| `get_stats` | 查看状态 | 返回已处理文件数和总 chunk 数 |

```yaml
rag_query:
  description: "基于知识库回答问题。首次调用时自动处理待导入文件"
  arguments:
    query: string
    stream: bool（默认 true）
  returns: string（回答文本）

ingest_documents:
  description: "手动触发文件处理工作流"
  arguments: {}
  returns: string（处理结果，如"已处理 5 个文件"）

get_stats:
  description: "查询知识库状态"
  arguments: {}
  returns:
    files: int    # 已处理文件数
    chunks: int   # 总 chunk 数
```

#### 12c. 首次查询自动导入

```
首次调用 rag_query
  │
  ├── index.json 已有数据？
  │   ├── 有 → 直接查询
  │   └── 无 → input/ 有待处理文件？
  │       ├── 有 → 自动执行 ingest（同第 8 节流程）
  │       │        → ingest 完成后 → 执行查询
  │       └── 无 → 返回"知识库为空，请先导入文档"
```

首次查询因包含 ingest 耗时可能较长，后续查询不受影响。

#### 12d. CLI 模式

不带子命令启动时为 MCP Server 模式；带子命令时进入 CLI 模式。

```bash
rag-server                    # MCP Server 模式（stdio）
rag-server ingest             # 手动触发文件处理
rag-server query "问题"       # 查询问答
rag-server stats              # 查询已处理文件数和总 chunk 数
rag-server clean              # 清空所有数据（docs、assets、vector、sparse、index.json）
```

各子命令功能与 MCP 工具一一对应：

| CLI | 对应 MCP Tool | 说明 |
|-----|--------------|------|
| `rag-server` | — | 启动 MCP Server（stdio 模式），被 MCP Host 调用 |
| `rag-server ingest` | `ingest_documents` | 扫描 input/ 并处理文件 |
| `rag-server query "..."` | `rag_query` | 直接问答，支持 `--no-stream` 关闭流式 |
| `rag-server stats` | `get_stats` | 显示已处理文件数和总 chunk 数 |
| `rag-server clean` | — | 清空数据目录（docs、assets、vector、sparse、index.json） |

#### 12e. Web 界面（Streamlit）

基于 Streamlit 的简易问答页面，通过浏览器访问：

```
streamlit run web_app.py
```

```python
import streamlit as st
from rag_pipeline import query as rag_query

st.set_page_config(page_title="知识库问答", page_icon="📖")
st.title("📖 知识库问答")

query = st.text_input("输入问题")
if query:
    with st.spinner("正在查询..."):
        result = rag_query(query, stream=True)
        st.write_stream(result)
```

| 方式 | 命令 |
|------|------|
| 启动 | `streamlit run web_app.py` |
| 访问 | 浏览器打开 http://localhost:8501 |

页面布局：主区域为问答交互，侧边栏放置所有可调参数和知识库状态。

```
┌──────────────────────────────────────────────────┐
│  📖 知识库问答                                    │
│                                                   │
│  ┌──────────────┐  ┌────────────────────────────┐ │
│  │ ⚙️ 参数设置   │  │  输入框                    │ │
│  │ ────────────  │  │  ┌────────────────────────┐ │ │
│  │ 检索设置      │  │  │  输入问题...            │ │ │
│  │  向量比重: 0.5 │  │  └────────────────────────┘ │ │
│  │  向量TopK: 20 │  │  [ 提问 ]                  │ │
│  │  BM25 TopK:20│  │                            │ │
│  │  最终条数: 10 │  │  回答:                     │ │
│  │              │  │  ┌────────────────────────┐ │ │
│  │ LLM 设置     │  │  │  根据文档检索...        │ │ │
│  │  模型: gpt-4o │  │  │                        │ │ │
│  │  温度: 0.7   │  │  └────────────────────────┘ │ │
│  │  最大字符:3万 │  │                            │ │
│  │  流式: ✔     │  │                            │ │
│  │              │  │                            │ │
│  │ 拼接设置     │  │                            │ │
│  │  启用: □     │  │                            │ │
│  │  去重: ✔     │  │                            │ │
│  │              │  │                            │ │
│  │ 知识库状态   │  │                            │ │
│  │  文件: 12    │  │                            │ │
│  │  chunk: 345  │  │                            │ │
│  └──────────────┘  └────────────────────────────┘ │
└──────────────────────────────────────────────────┘
```

```python
import streamlit as st
from rag_pipeline import query as rag_query, get_stats

st.set_page_config(page_title="知识库问答", page_icon="📖")
st.title("📖 知识库问答")

# 侧边栏参数
with st.sidebar:
    st.header("⚙️ 检索设置")
    vector_weight = st.slider("向量检索比重", 0.0, 1.0, 0.5)
    vector_top_k = st.number_input("向量 Top-K", 1, 100, 20)
    bm25_top_k = st.number_input("BM25 Top-K", 1, 100, 20)
    final_top_k = st.number_input("最终返回条数", 1, 50, 10)

    st.header("🤖 LLM 设置")
    model = st.text_input("模型", "gpt-4o-mini")
    temperature = st.slider("温度", 0.0, 2.0, 0.7)
    max_chars = st.number_input("最大字符数", 1000, 100000, 30000)
    stream = st.checkbox("流式输出", True)

    st.header("🔗 拼接设置")
    stitcher = st.checkbox("启用拼接", False)
    dedup = st.checkbox("去重", True)

    st.header("📊 知识库状态")
    stats = get_stats()
    st.write(f"已处理文件: {stats['files']}")
    st.write(f"总 chunk 数: {stats['chunks']}")

# 主区域问答
query = st.text_input("输入问题")
if query:
    with st.spinner("正在查询..."):
        result = rag_query(
            query,
            stream=stream,
            vector_weight=vector_weight,
            model=model,
            temperature=temperature,
            max_chars=max_chars,
        )
        if stream:
            st.write_stream(result)
        else:
            st.markdown(result)
```

### 13. ASR 语音识别层

语音识别（ASR）作为独立的 AI 能力层，与 LLM、Embedding 并列。提供抽象接口 + 厂商实现。

```
rag_server/asr/
├── __init__.py
├── base.py              ← ASR(ABC): transcribe(audio_path) → str
└── dashscope.py         ← @register("asr", "dashscope") DashScopeASR
```

#### 13a. ASR 抽象接口

```python
class ASR(ABC):
    @abstractmethod
    async def transcribe(self, audio_path: str) -> str:
        """将音频文件转为文字，返回完整文本。"""
        ...
```

#### 13b. DashScopeASR 实现

基于阿里云 DashScope 的语音识别 API（`dashscope.audio.asr`），将音频文件上传并获取识别结果。

```python
@register("asr", "dashscope")
class DashScopeASR(ASR):
    def __init__(self, api_key: str = "", model: str = "paraformer-v1"):
        import dashscope
        dashscope.api_key = api_key
        self.model = model

    async def transcribe(self, audio_path: str) -> str:
        # 调用 DashScope ASR API
        from dashscope.audio.asr import Recognition
        result = Recognition.call(model=self.model, audio_url=audio_path)
        return result.get_text()
```

**Rationale**: 复用项目已有的 dashscope 依赖和 API key，不需要额外申请第三方服务。阿里云 Paraformer 模型支持中英文，识别准确率高。

### 14. Word 文档加载器

支持 `.docx` 格式的 Word 文档，基于 `python-docx` 库读取文本。

#### 14a. 文件格式支持

| 扩展名 | 支持 | 技术方案 |
|--------|------|---------|
| `.docx` | ✅ | `python-docx` 直接读取 |
| `.doc` | ❌ | 旧版二进制格式，需另找方案 |

#### 14b. WordLoader 实现

```python
@register("loader", "docx")
class WordLoader(BaseLoader):
    async def load(self, file_path: str) -> LoaderOutput:
        from docx import Document
        doc = Document(file_path)
        md_parts = []
        for para in doc.paragraphs:
            md_parts.append(para.text)
        return LoaderOutput(
            md_text="\n\n".join(md_parts),
            assets=[],
            metadata={"source": file_path},
        )
```

#### 14c. 图片提取（暂不支持）

`python-docx` 可以读取文档中的内嵌图片，当前版本暂不提取图片资产。后续可按需增强。

**Rationale**: `python-docx` 是 Python 生态中最成熟的 .docx 解析库，轻量且无系统依赖。

### 15. 视频文档加载器

视频加载分两步：音频提取 → 语音转文字，最终输出 MD 文本。

#### 15a. 处理流程

```
视频文件（.mp4/.avi/.mov/.mkv）
  │
  ▼
Step 1: ffmpeg 提取音频
  │   ffmpeg -i input.mp4 -vn -ar 16000 -ac 1 audio.wav
  │
  ▼
Step 2: ASR 语音转文字
  │   DashScopeASR.transcribe("audio.wav")
  │
  ▼
输出 MD 文本
```

#### 15b. FFmpeg 依赖

需要系统安装 FFmpeg：

| 平台 | 安装方式 |
|------|---------|
| Windows | `winget install ffmpeg` 或从 ffmpeg.org 下载 exe |
| macOS | `brew install ffmpeg` |
| Linux | `apt install ffmpeg` |

Python 通过 `subprocess` 调用，不依赖 `ffmpeg-python` 库。

#### 15c. VideoLoader 实现

```python
@register("loader", "video")
class VideoLoader(BaseLoader):
    def __init__(self, asr_provider: str = "dashscope"):
        self.asr_provider = asr_provider

    async def load(self, file_path: str) -> LoaderOutput:
        import subprocess  # 仅作示意，非最终实现
        audio_path = self._extract_audio(file_path)

        asr = Factory.create("asr", self.asr_provider, ...)
        text = await asr.transcribe(audio_path)

        return LoaderOutput(
            md_text=text,
            assets=[],
            metadata={"source": file_path, "type": "video"},
        )

    def _extract_audio(self, video_path: str) -> str:
        audio_path = video_path + ".wav"
        subprocess.run([
            "ffmpeg", "-i", video_path,
            "-vn", "-ar", "16000", "-ac", "1",
            audio_path
        ], check=True)
        return audio_path
```

**Rationale**: ffmpeg 是业界标准的多媒体处理工具，通过 subprocess 调用无需 Python 绑定库。ASR 服务复用已有的 dashscope 能力，不引入新 AI 服务。

#### 15d. 音频文件加载器

纯音频文件处理更简单——无需 ffmpeg 提取步骤，直接 ASR 转文字。

| 扩展名 | 支持 |
|--------|------|
| `.mp3` | ✅ |
| `.wav` | ✅ |
| `.m4a` | ✅ |

```python
@register("loader", "audio")
class AudioLoader(BaseLoader):
    def __init__(self, asr_provider: str = "dashscope"):
        self.asr_provider = asr_provider

    async def load(self, file_path: str) -> LoaderOutput:
        asr = Factory.create("asr", self.asr_provider, ...)
        text = await asr.transcribe(file_path)

        return LoaderOutput(
            md_text=text,
            assets=[],
            metadata={"source": file_path, "type": "audio"},
        )
```

### 16. 项目文件结构

```
rag-server/
|
+-- pyproject.toml              <- 项目元数据 + 依赖声明（核心 + extras）
+-- config.yaml                 <- 默认配置（含 ingestion_pipeline / query_pipeline 段）
+-- README.md
+-- .env.example
+-- .gitignore
|
+-- rag_server/                 <- 核心包
    +-- __init__.py
    +-- __main__.py             <- 入口分发：无参数 -> MCP Server，子命令 -> CLI
    +-- config.py               <- 配置加载（YAML + 环境变量覆盖）
    +-- registry.py             <- @register() / Factory / auto_register()
    |
    +-- models/                 <- AI 模型调用层
    |   +-- llm/                <- LLM 能力（可插拔）
    |   |   +-- base.py         <- LLM(ABC): chat()
    |   |   +-- openai.py       <- OpenAILLM（httpx）
    |   |   +-- anthropic.py    <- AnthropicLLM（httpx）
    |   +-- embedding/          <- Embedding 能力（可插拔）
    |   |   +-- base.py         <- Embedding(ABC): embed()
    |   |   +-- openai.py       <- OpenAIEmbedding（httpx）
    |   |   +-- dashscope.py    <- DashScopeEmbedding（dashscope SDK）
    |   +-- asr/                <- 语音识别（可插拔）
    |       +-- base.py         <- ASR(ABC): transcribe()
    |       +-- dashscope.py    <- DashScopeASR（httpx REST API）
    |
    +-- loaders/                <- 文档加载层（可插拔）
    |   +-- __init__.py
    |   +-- base.py             <- BaseLoader(ABC): extensions + load()
    |   +-- pdf.py              <- PDFLoader（PyMuPDF）
    |   +-- markdown.py         <- MarkdownLoader
    |   +-- image.py            <- ImageLoader（图转文 + OCR）
    |   +-- word.py             <- WordLoader（python-docx）
    |   +-- video.py            <- VideoLoader（ffmpeg + ASR）
    |   +-- audio.py            <- AudioLoader（ASR 直接转文字）
    |
    +-- text/                   <- 文本处理
    |   +-- __init__.py
    |   +-- base.py             <- Splitter(ABC): split()
    |   +-- splitter.py         <- TextSplitter @register("splitter", "default")
    |   +-- chunk.py            <- Chunk dataclass
    |   +-- cleaner.py          <- BaseCleaner(ABC) + DefaultCleaner
    |
    +-- stores/                 <- 存储层
    |   +-- __init__.py
    |   +-- base.py             <- VectorStore(ABC)
    |   +-- chroma.py           <- ChromaStore（向量 + chunk_id）
    |   +-- document.py         <- DocumentStore（文件管理）
    |   +-- index_store.py      <- IndexStore (index.json)
    |   +-- persister.py        <- Storage(ABC) + FileStorage @register("storage", "file")
    |   +-- vectorizer.py       <- Indexer(ABC) + ChromaIndexer @register("indexer", "chroma")
    |
    +-- retrieval/              <- 检索层（可插拔）
    |   +-- __init__.py
    |   +-- base.py             <- Retriever(ABC) + Ranker(ABC)
    |   +-- hybrid.py           <- HybridRetriever @register("retriever", "hybrid")
    |   +-- fusion.py           <- HybridRanker @register("ranker", "hybrid")
    |   +-- bm25.py             <- BM25Index（rank_bm25 + jieba）
    |   +-- stitcher.py         <- ChunkJoiner（可选，上下文拼接）
    |
    +-- prompt/                 <- Prompt 组装
    |   +-- __init__.py         <- 重新导出
    |   +-- builder.py          <- PromptBuilder(ABC) + DefaultPromptBuilder
    |
    +-- pipeline/               <- 编排层（config 驱动，全可插拔）
    |   +-- __init__.py
    |   +-- ingestion.py        <- IngestionPipeline（加载→清洗→分块→持久化→索引）
    |   +-- query.py            <- QueryPipeline（检索→排序→组装→LLM）
    |
    +-- interfaces/             <- 接口层
    |   +-- __init__.py
    |   +-- cli.py              <- CLI 子命令
    |   +-- mcp.py              <- MCP Server
    |   +-- web.py              <- Streamlit 界面
    |
    +-- utils/                  <- 工具
        +-- __init__.py
        +-- timer.py            <- 耗时统计装饰器

+-- tests/                      <- 测试
    +-- __init__.py
    +-- test_integration.py     <- 全链路集成测试
    +-- test_timing.py          <- 耗时报告测试
    +-- test_cleaner.py         <- DefaultCleaner 单元测试
    +-- test_splitter.py        <- TextSplitter 单元测试
    +-- test_persister.py       <- FileStorage 单元测试
    +-- test_fuser.py           <- HybridRanker 单元测试
    +-- test_assembler.py       <- DefaultPromptBuilder 单元测试
    +-- test_retriever.py       <- HybridRetriever（mock）
    +-- test_vectorizer.py      <- ChromaIndexer（mock）
    +-- test_loaders.py         <- 各 Loader 单元测试（mock）

+-- data/                       <- 运行期数据
    +-- input/                  <- 待处理文件
    +-- processed/              <- 已处理文件归档
    +-- docs/                   <- MD 源文件全文
    +-- assets/                 <- 图片资产
    +-- vector/                 <- Chroma 持久化
    +-- sparse/                 <- BM25 持久化
    +-- index.json              <- chunk_id -> 全文索引表
```

**Rationale**: 文件结构即架构。`models/` 物理归组所有 AI 模型调用（llm / embedding / asr）；每条管线全由 config 驱动；每步组件均有 ABC + @register + 独立单元测试。新增任一环节只需加文件 + 注册，零改现有代码。

## Risks / Trade-offs
|------|---------|
| PyMuPDF 对复杂 PDF 表格提取不完整 | 通过配置启用 pdfplumber 做表格增强（可选依赖）|
| 图转文模型增加管线延迟 | 图转文设为可选开关，仅在配置启用时执行 |
| 中文文档的 token/字符估算偏差 | 提供 token 精确模式（tiktoken）和字符估算模式两种选择 |
| Chroma 在大规模（百万级向量）下性能下降 | VectorStore 接口可替换为 Qdrant 等高性能后端 |
| 超长段落降级到逗号切分时仍可能切断语义单元 | 降级只在段落超过块大小时触发，且通过重叠机制补偿上下文 |
| BM25 需要每次启动时重建索引，增量导入有重建延迟 | 中小规模（千份文档内）重建在秒级，可接受；大规模考虑增量方案 |
| 向量与 BM25 分数归一化对融合结果影响敏感 | 提供 vector_weight 可配置，允许用户按场景调优 |
| 上下文超限时丢弃低分 chunk 可能丢失关键信息 | 通过提高检索质量（final_top_k）和增大 max_chars 缓解 |
| Streamlit 增加项目依赖体积 | 仅开发内部 Web 界面时安装，非核心依赖 |