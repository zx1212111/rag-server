## Context

当前 AI 能力层分为 `protocols/` 和 `providers/` 两个子包，各 3-4 个文件。详见 proposal.md。

核心约束：
- Registry key 不变：仍为 `("llm", "openai")`、`("embedding", "dashscope")` 等
- Factory.create() 的调用方式不变
- 配置 YAML 格式不变
- MCP 工具和 CLI 命令的外部接口不变

## Goals / Non-Goals

**Goals:**
- `protocols/` 和 `providers/` 合并重组为 `llm/` + `embedding/`，按能力分目录
- 每目录一个 ABC 抽象接口，按厂商分文件
- 删除冗余的 BaseProtocol（它同时定义 chat + embed，但 Anthropic 不支持 embed）
- 更新所有导入路径和注册表引用
- 保持注册表 key、配置格式、外部接口不变
- 消除硬编码 import，实现 LLM / Embedding 厂商自动发现（同 Loader 可插拔模式）
- Ingestion 管线每步（清洗/分块/持久化/向量化）抽象为 ABC + @register + Factory，由 config 驱动

**Non-Goals:**
- 不引入新 LLM 或 Embedding 厂商
- 不改动 `rag_server/pipeline/`（除导入方式）、`rag_server/stores/`、`rag_server/retrieval/` 等模块的业务逻辑
- 不改动 `tests/` 中的测试逻辑（仅更新导入路径）
- 不修改 `pyproject.toml`（依赖不变）

## Decisions

### 1. 新目录结构

```
rag_server/
│
├── llm/                       ← LLM 能力（可插拔）
│   ├── __init__.py
│   ├── base.py                ← LLM(ABC): chat()
│   ├── openai.py              ← OpenAICompatibleLLM
│   └── anthropic.py           ← AnthropicLLM
│
├── embedding/                 ← Embedding 能力（可插拔）
│   ├── __init__.py
│   ├── base.py                ← Embedding(ABC): embed()
│   ├── openai.py              ← OpenAICompatibleEmbedding
│   └── dashscope.py           ← DashScopeEmbedding
│
├── text/                      ← 文本处理（可插拔）
│   ├── base.py                ← Splitter(ABC): split()
│   ├── splitter.py            ← TextSplitter @register("splitter", "default")
│   ├── cleaner.py             ← BaseCleaner + DefaultCleaner
│   └── chunk.py               ← Chunk 数据类
│
├── loaders/                   ← 文件加载（可插拔）
│   ├── base.py                ← BaseLoader(ABC): extensions + load()
│   ├── pdf.py / markdown.py / image.py
│   └── word.py / audio.py / video.py
│
├── stores/                    ← 存储层（可插拔）
│   ├── base.py                ← VectorStore(ABC)
│   ├── chroma.py              ← ChromaStore @register("vs", "chroma")
│   ├── document.py            ← DocumentStore（文件管理）
│   ├── index_store.py         ← IndexStore（索引表）
│   ├── persister.py           ← Persister(ABC) + FilePersister @register("persister", "file")
│   └── vectorizer.py          ← Vectorizer(ABC) + ChromaVectorizer @register("vectorizer", "chroma")
│
├── retrieval/                 ← 检索层（可插拔）
│   ├── base.py                ← Retriever(ABC) + Fuser(ABC)
│   ├── hybrid.py              ← HybridRetriever @register("retriever", "hybrid")
│   ├── fusion.py              ← HybridFusion @register("fuser", "hybrid")
│   ├── bm25.py                ← BM25Index
│   └── stitcher.py            ← ChunkStitcher
│
├── prompt/                    ← Prompt 组装（可插拔）
│   └── __init__.py            ← Assembler(ABC) + DefaultAssembler
│
├── pipeline/
│   ├── ingestion.py           ← IngestionPipeline（5 步 config 驱动）
│   └── rag_pipeline.py        ← RAGPipeline（4 步 config 驱动）
│
├── interfaces/
│   ├── mcp.py / web.py / cli.py
│
├── config.py                  ← 配置（含 PipelineConfig / RetrievalConfig）
├── registry.py                ← 注册表 + 工厂 + auto_register()
├── asr/                       ← 语音识别
└── utils/                     ← 工具函数
```

**Rationale**: 每个子包内一个 ABC + 多个按厂商/策略的实现文件，结构自解释。新增任一环节只需在对应子包下加文件 + @register。

### 2. 合并策略：协议层内联进能力层

当前结构：

```
providers/llm.py              →  imports   protocols/openai.py  →  httpx 调用
providers/embedding.py        →  imports   protocols/openai.py  →  httpx 调用
providers/dashscope_embedding.py → 独立 import dashscope SDK
```

新结构将 HTTP 调用直接内联进能力实现：

```
llm/openai.py        →  httpx 调用（无需经过中间协议类）
llm/anthropic.py     →  httpx 调用（无需经过中间协议类）
embedding/openai.py  →  httpx 调用
embedding/dashscope.py → dashscope SDK
```

**Rationale**: 去掉协议层后，每个实现文件都自包含 HTTP 通信细节，不再需要委托给另一个类。代码行数不变，但减少了间接层次。

### 3. 抽象接口拆分

当前 `BaseProtocol` 同时包含 chat() 和 embed()，但 Anthropic 不支持 embed，只能 raise NotImplementedError。新设计拆成两个独立的 ABC：

| ABC | 方法 | 目录 |
|-----|------|------|
| `LLM` | `chat(messages, stream, temperature) → AsyncIterator[str]` | `llm/base.py` |
| `Embedding` | `embed(texts) → List[List[float]]` | `embedding/base.py` |

**Rationale**: 每个接口只定义该子包必须的能力。Anthropic 只需实现 LLM，无需提供一个没意义的 embed()。

### 4. 各文件具体设计

#### llm/base.py

```python
from abc import ABC, abstractmethod
from typing import AsyncIterator, Dict, List

class LLM(ABC):
    @abstractmethod
    async def chat(
        self,
        messages: List[Dict[str, str]],
        stream: bool = False,
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        ...
```

与当前 `LLMProvider` 完全一致，仅重命名。

#### llm/openai.py

合并当前 `protocols/openai.py` 的 HTTP 调用 + `providers/llm.py` 的 `OpenAICompatibleLLM`。

```python
from rag_server.registry import register
from .base import LLM

@register("llm", "openai")
class OpenAICompatibleLLM(LLM):
    def __init__(self, base_url="", api_key="", model="gpt-4o-mini"):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self._headers = {...}

    async def chat(self, messages, stream=False, temperature=0.7):
        # HTTP POST /v1/chat/completions — 直接从当前 openai.py 搬过来
        ...
```

#### llm/anhropic.py

合并当前 `protocols/anhropic.py` 的 HTTP 调用 + `providers/llm.py` 的 `AnthropicLLM`。

```python
@register("llm", "anthopic")
class AnhropicLLM(LLM):
    def __ini__(self, api_key="", model="claude-sonnet-4-20250514"):
        ...
    
    async def hat(sefl, messages, stream=False, temperature=0.7):
        # HTTP POST /v1/messages — 直接从当前 anthopic.py 搬过来
        ...```

#### embeddng/base.py

```python
from abc import ABC, abstractmethod

class Embedding(ABC):
    @abstractmethod
    async def embed(self, ext: List[str]) -> List[List[float]]:
        ...
```

与当前 `EmbeddinProvder` 完全一致，仅重命名。

#### embedding/penai.py

合并当前 `protocols/opnai.py` 的 embed() + `providers/embedding.py` 的 `OpenAICompatibleEmbeddng`.

```python
@register("embedding", "opnai")
class OpenAICompatibleEmbedding(Embedding):
    def __inti__(self, ase_url="", api_key="", modl="text-embedding-3-smal"):
        ...
    
    async def embed(elf, texts):
        # HTTP POST /v1/embeddins — 直接从当前 openai.py 的 embed() 搬过来
        ...
```

#### embeding/dashcpe.py

与当前 `providers/dascoe_embedding.py` 一致，仅把导入路径从 `from .embedig import EmbddingProvider`改为 `from .base import Embedding`。

### 5. 新旧文件映射表

| 旧文件 | 新文件 | 操作 |
|-------|--------|------|
| `protocols/base.py` | — | 删除 |
| `protocols/openai.py` | 内联进 `llm/openai.py` + `embedding/openai.py` | 删除旧文件 |
| `protocols/anthropic.py` | 内联进 `llm/anthropic.py` | 删除旧文件 |
| `protocols/__init__.py` | — | 删除 |
| `providers/llm.py` |→ `lm/openi.py` + `lm/anhropic.py` | 删除旧文件 |
| `providers/embedding.py` |→ `embedding/openi.py` | 删除旧文件 |
| `providers/dascoe_embedding.py` | `embedding/dashcpe.py` | 移动 + 重命名 |
| `providers/__init__.py` | — | 删除 |

### 6. 导入路径变更

| 文件 | 旧导入 | 新导入 |
|------|--------|--------|
| `pipelne/rag_ipeline.py` | `from rag_server.providers.llm import LLMProvide` → 仅用于类型标注 | `from rag_server.llm.base import LLM` |
| — | `import rag_server.providers.dashscope_embeding` | `import rag_server.embedding.dashcope` |
|—|`rom rag_server.providers.embedding import EmbeddingProider`| `from rag_server.embedding.base import Embeddng`|
| `r/__init__.py` 无变化（不直接导入 providers） |
| `tests/` 中的导入 | 仅在集成测试中间接使用 | 不变 |

注：rag_pipelne.py 中通过 `Factory.reate("llm", ...")` 和 `Factory.create("embeding", ...")` 创建实例，注册表 key 不变，所以 `_ensure_llm()` 和 `query()`中的 Factory.create() 调用不需要改。

### 7. 注册表注册位置迁移

| 注册语句 | 旧位置 | 新位置 |
|---------|--------|--------|
| `@register("llm", "opnai")` | `providers/llm.py` | `llm/penai.py` |
| `@register("llm", "anhropic")` | `providers/llm.py` | `llm/anhropic.py` |
| `@register("embedding", "opnai")` | `providers/embedding.py` | `embedding/penai.py` |
| `@register("embedding", "dashcpe")` | `providers/dashcope_embedding.py` | `embedding/dashcpe.py` |

所有 register 调用都在新文件中重写，Registry key 的值不变。

### 8. Loader 扩展名可插拔

当前 `list_input_files()` 和 `_resolve_loader()` 各有一份硬编码的扩展名映射，加新格式需改两处。改为由 Loader 类自声明扩展名，系统自动收集。

**方案**：

```python
# loaders/base.py
class BaseLoader(ABC):
    extensions: List[str] = []   # 子类覆盖，如 [".pdf"]

    @abstractmethod
    async def load(self, file_path: str) -> LoaderOutput:
        ...
```

每个 Loader 子类声明自己的扩展名：

```python
@register("loader", "pdf")
class PDFLoader(BaseLoader):
    extensions = [".pdf"]
```

收集函数（放在 `registry.py`）：

```python
def get_supported_extensions() -> List[str]:
    exts = []
    for name, cls in _registry.get("loader", {}).items():
        exts.extend(cls.extensions)
    return exts
```

**改动点**：

| 文件 | 改法 |
|------|------|
| `loaders/base.py` | `BaseLoader` 加 `extensions: List[str]` 类属性 |
| `loaders/pdf.py` | 加 `extensions = [".pdf"]` |
| `loaders/markdown.py` | 加 `extensions = [".md"]` |
| `loaders/image.py` | 加 `extensions = [".png", ".jpg", ".jpeg", ".gif", ".bmp"]` |
| `loaders/word.py` | 加 `extensions = [".docx", ".doc"]` |
| `loaders/audio.py` | 加 `extensions = [".mp3", ".wav", ".m4a"]` |
| `loaders/video.py` | 加 `extensions = [".mp4", ".avi", ".mov", ".mkv"]` |
| `registry.py` | 加 `get_supported_extensions()` |
| `stores/document.py` | `list_input_files()` 改为调 `get_supported_extensions()` |
| `pipeline/ingestion.py` | `_resolve_loader()` 改为遍历注册表匹配扩展名，删除 `loader_map` |

**Rationale**：新增格式 = 新增 Loader 文件 + 声明 `extensions`，零改现有代码。真正可插拔。

### 9. LLM / Embedding 厂商自动发现

当前 `rag_pipeline.py` 顶部有 4 行硬编码 import 用于触发 `@register`：

```python
import rag_server.llm.openai
import rag_server.llm.anthropic
import rag_server.embedding.openai
import rag_server.embedding.dashscope
```

新增厂商时需在此处加一行，违背可插拔原则。

**方案**：在 `registry.py` 中新增 `auto_register()`，启动时自动扫描目录并导入所有模块：

```python
# registry.py
import importlib
import pkgutil

def auto_register(package_name: str) -> None:
    """自动导入指定包下的所有模块，触发 @register 装饰器。"""
    pkg = importlib.import_module(package_name)
    for _, module_name, _ in pkgutil.iter_modules(pkg.__path__):
        if module_name not in ("__init__", "base"):
            importlib.import_module(f"{package_name}.{module_name}")
```

**改动点**：

| 文件 | 改法 |
|------|------|
| `registry.py` | 新增 `auto_register()` 函数 |
| `pipeline/rag_pipeline.py` | 移除 4 行硬编码 import，改为 `auto_register("rag_server.llm")` + `auto_register("rag_server.embedding")` |

**Rationale**：新增厂商 = 在 `llm/` 或 `embedding/` 下加一个文件 + `@register`，零改现有代码。与 Loader 的可插拔模式一致。

### 10. Ingestion 管线全流程可插拔

当前 `ingestion.py` 的 `run()` 中，只有加载是可插拔的，其余 7 步均硬编码在管线内：

```
 ✅ 1. 加载       ← 已可插拔
 ❌ 2. 清洗       ← 有 ABC 但 provider 硬编码为 "default"
 ❌ 3. 分块       ← TextSplitter() 直接 new
 ❌ 4. 保存 MD    ← 硬编码调 doc_store.save_doc()
 ❌ 5. 保存图片   ← 硬编码调 doc_store.save_asset()
 ❌ 6. 构建索引   ← 硬编码逐 chunk 调 index_store.add()
 ❌ 7. 嵌入Chroma ← 硬编码调 embed() + vector_store.add_batch()
 ⭕ 8. 移文件     ← 固定收尾，不动
```

**方案**：每个步骤抽象为独立的 ABC + @register + Factory，由 config 指定 provider。

#### 10.1 新增 Config

```python
@dataclass
class PipelineConfig:
    cleaner_provider: str = "default"
    splitter_provider: str = "default"
    persister_provider: str = "file"
    vectorizer_provider: str = "chroma"
```

追加到 `Config` 中：

```python
@dataclass
class Config:
    llm: LLMConfig = field(default_factory=LLMConfig)
    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    pipeline: PipelineConfig = field(default_factory=PipelineConfig)
    retrieval: RetrievalConfig = field(default_factory=RetrievalConfig)
    stitcher: StitcherConfig = field(default_factory=StitcherConfig)
    data: DataConfig = field(default_factory=DataConfig)
```

YAML 用法：

```yaml
pipeline:
  cleaner: default
  splitter: default
  persister: file
  vectorizer: chroma
```

#### 10.2 Splitter 抽象（新增 `text/base.py`）

```python
from abc import ABC, abstractmethod
from typing import List
from .chunk import Chunk

class Splitter(ABC):
    @abstractmethod
    def split(self, text: str, doc_id: str) -> List[Chunk]:
        ...
```

当前 `TextSplitter` 实现它并注册：

```python
@register("splitter", "default")
class TextSplitter(Splitter):
    ...
```

#### 10.3 Persister 抽象（新增 `stores/persister.py`）

合并当前保存 MD + 保存图片为统一接口：

```python
from abc import ABC, abstractmethod
from typing import Dict, List

class Persister(ABC):
    """持久化抽象。管线只调 persist()，不管存文件还是存数据库。"""

    @abstractmethod
    async def persist(
        self,
        chunks: List[Chunk],
        assets: List[Dict],
        doc_name: str,
    ) -> None:
        ...

@register("persister", "file")
class FilePersister(Persister):
    """文件系统实现，包装现有 DocumentStore 的 save_doc + save_asset。"""
    ...
```

#### 10.4 Vectorizer 抽象（新增 `stores/vectorizer.py`）

合并当前构建索引 + 嵌入 + Chroma 存储为统一接口：

```python
from abc import ABC, abstractmethod
from typing import List

class Vectorizer(ABC):
    """向量化抽象。管线只调 vectorize()，不管用哪个向量库。"""

    @abstractmethod
    async def vectorize(self, chunks: List[Chunk]) -> None:
        ...

@register("vectorizer", "chroma")
class ChromaVectorizer(Vectorizer):
    """Chroma 实现，内部管理 IndexStore + Embedding + ChromaStore。"""
    ...
```

#### 10.5 改造后 `ingestion.py`

```python
class IngestionPipeline:
    def _ensure_services(self):
        self.loader = ...             # 已有
        self.cleaner = Factory.create("cleaner", self.config.pipeline.cleaner_provider)
        self.splitter = Factory.create("splitter", self.config.pipeline.splitter_provider)
        self.persister = Factory.create("persister", self.config.pipeline.persister_provider)
        self.vectorizer = Factory.create("vectorizer", self.config.pipeline.vectorizer_provider)

    async def run(self) -> str:
        ...
        for file_path in files:
            output = await loader.load(file_path)               # 插拔
            cleaned = self.cleaner.clean(output.md_text)         # 插拔
            chunks = self.splitter.split(cleaned, doc_id)        # 插拔
            await self.persister.persist(chunks, output.assets, doc_name)  # 插拔
            await self.vectorizer.vectorize(chunks)              # 插拔
            self.doc_store.move_to_processed(file_path)          # 固定
        ...
```

**改动点汇总**：

| 文件 | 操作 |
|------|------|
| `rag_server/config.py` | 新增 `PipelineConfig` 数据类，追加到 `Config` |
| `rag_server/text/base.py` | **新增** `Splitter(ABC)` 抽象接口 |
| `rag_server/text/splitter.py` | `TextSplitter` 加 `@register("splitter", "default")`，implements `Splitter` |
| `rag_server/stores/persister.py` | **新增** `Persister(ABC)` + `FilePersister` 实现 |
| `rag_server/stores/vectorizer.py` | **新增** `Vectorizer(ABC)` + `ChromaVectorizer` 实现 |
| `rag_server/pipeline/ingestion.py` | `run()` 精简为 6 步，全部由 config 驱动 |
| `rag_server/registry.py` 或 `ingestion.py` | 加 `auto_register` 确保 splitter/persister/vectorizer 被导入 |

**Rationale**：管线只编排不实现，每步由 config 指定 provider。新增存储后端或向量库只需加文件 + 注册，零改管线代码。

### 11. RAG 查询管线全流程可插拔

当前 `rag_pipeline.py` 的 `query()` 中检索、融合、上下文组装均硬编码：

```
 ❌ 1. 双路检索       ← ChromaStore.search() + BM25Index.search() 硬编码
 ❌ 2. 融合           ← HybridFusion 直接 new
 ❌ 3. 获取文本+Stitcher ← IndexStore + ChunkStitcher 硬编码
 ❌ 4. 组装 Prompt    ← _assemble_context() + SYSTEM_PROMPT 硬编码
 ✅ 5. LLM 生成       ← 已有抽象接口
```

**目标流程**：管线只编排，每步由 config 驱动：

```
query
  │
  ├─ Retriever.retrieve(query)        → 检索（单路/多路/混合）
  │
  ├─ Fuser.fuse(results)              → 融合排序
  │
  ├─ Assembler.assemble(context, query) → 组装 Prompt
  │
  ├─ LLM.chat(prompt)                 → 生成
  │
  answer
```

#### 11.1 Config 扩展

在 `RetrievalConfig` 中新增 provider 字段：

```python
@dataclass
class RetrievalConfig:
    retriever_provider: str = "hybrid"     # hybrid | vector_only | bm25_only
    fuser_provider: str = "hybrid"         # hybrid | rrf | ...
    assembler_provider: str = "default"    # default | ...
    vector_weight: float = 0.5
    vector_top_k: int = 20
    bm25_top_k: int = 20
    final_top_k: int = 10
```

YAML 用法：

```yaml
retrieval:
  retriever: hybrid
  fuser: hybrid
  assembler: default
  vector_weight: 0.5
```

#### 11.2 Retriever 抽象

```python
from abc import ABC, abstractmethod
from typing import List, Tuple

class Retriever(ABC):
    """检索抽象。管线只调 retrieve(query)，不关心走什么引擎。"""

    @abstractmethod
    async def retrieve(self, query: str, top_k: int = 20) -> List[Tuple[str, float]]:
        """返回 [(chunk_id, score), ...]"""
        ...
```

当前混合检索封装为 `HybridRetriever`：

```python
@register("retriever", "hybrid")
class HybridRetriever(Retriever):
    """双路检索：向量 + BM25。内部管理 VectorStore + BM25Index。"""
    ...
```

#### 11.3 Fuser 抽象

```python
from abc import ABC, abstractmethod
from typing import List, Tuple

class Fuser(ABC):
    """融合抽象。管线只调 fuse()，不关心融合策略。"""

    @abstractmethod
    def fuse(
        self,
        vector_results: List[Tuple[str, float]],
        bm25_results: List[Tuple[str, float]],
    ) -> List[str]:
        ...
```

```python
@register("fuser", "hybrid")
class HybridFusion(Fuser):
    """加权融合：final = α × vec + (1-α) × bm25。"""
    ...
```

#### 11.4 Assembler 抽象

```python
from abc import ABC, abstractmethod
from typing import List

class Assembler(ABC):
    """Prompt 组装抽象。管线只调 assemble()，不关心模板和裁剪策略。"""

    @abstractmethod
    async def assemble(self, context: str, query: str) -> List[dict]:
        """返回 messages 列表 [{"role": "system", "content": ...}]"""
        ...
```

```python
@register("assembler", "default")
class DefaultAssembler(Assembler):
    """默认实现：SYSTEM_PROMPT 模板 + _assemble_context 裁剪逻辑。"""
    ...
```

#### 11.5 改造后 `rag_pipeline.py`

```python
class RAGPipeline:
    def __init__(self, config: Config):
        self.config = config

    def _ensure_services(self):
        self.retriever = Factory.create("retriever", self.config.retrieval.retriever_provider)
        self.fuser = Factory.create("fuser", self.config.retrieval.fuser_provider)
        self.assembler = Factory.create("assembler", self.config.retrieval.assembler_provider)
        self.llm = Factory.create("llm", self.config.llm.provider, ...)

    async def query(self, query: str, stream: bool = True) -> AsyncIterator[str]:
        self._ensure_services()

        results = await self.retriever.retrieve(query, ...)       # 插拔
        fused_ids = self.fuser.fuse(results)                       # 插拔

        if not fused_ids:
            yield "未找到相关信息"
            return

        messages = await self.assembler.assemble(fused_ids, query) # 插拔

        async for chunk in self.llm.chat(messages, ...):            # 插拔
            yield chunk
```

**改动点汇总**：

| 文件 | 操作 |
|------|------|
| `rag_server/config.py` | `RetrievalConfig` 新增 retriever_provider / fuser_provider / assembler_provider |
| `rag_server/retrieval/base.py` | **新增** `Retriever(ABC)` + `Fuser(ABC)` |
| `rag_server/retrieval/fusion.py` | `HybridFusion` 加 `@register("fuser", "hybrid")`，implements `Fuser` |
| `rag_server/retrieval/hybrid.py` | **新增** `HybridRetriever`，`@register("retriever", "hybrid")`，内部管理 ChromaStore + BM25Index |
| `rag_server/prompt/assembler.py` | **新增** `Assembler(ABC)` + `DefaultAssembler` |
| `rag_server/pipeline/rag_pipeline.py` | `query()` 精简为 4 步，全部由 config 驱动 |
| `config.yaml` | 新增 `pipeline:` 段，`retrieval:` 补全 retriever/fuser/assembler，移除废弃的 `stitcher:` |

**Rationale**：检索/融合/组装各自独立，新增检索策略或 Prompt 模板只需加文件 + 注册，零改管线代码。与 Ingestion 管线设计一致。

### 12. config.yaml 同步

所有 provider 选择参数需同步到 `config.yaml`，真实反映当前的可插拔架构：

```yaml
llm:
  provider: openai

embedding:
  provider: openai

pipeline:                     # ← 新增
  cleaner: default
  splitter: default
  persister: file
  vectorizer: chroma

retrieval:
  retriever: hybrid           # ← 新增
  fuser: hybrid               # ← 新增
  assembler: default          # ← 新增
  vector_weight: 0.5
  vector_top_k: 20
  bm25_top_k: 20
  final_top_k: 10

data:
  root: ./data
```

改动：
- 新增 `pipeline:` 段，4 个 provider 字段
- `retrieval:` 新增 `retriever`/`fuser`/`assembler` 3 个字段
- 移除不再使用的 `stitcher:` 段

**Rationale**：config.yaml 是用户入口，必须完整展示所有可配参数。新增一个管线步骤或检索策略，用户只需改这里一行，无需翻代码。

### 13. 可插拔组件单元测试

为每个可插拔组件编写独立单元测试，策略如下：

| 测试文件 | 目标组件 | 隔离策略 |
|---------|---------|---------|
| `tests/test_cleaner.py` | DefaultCleaner | 纯函数，无需隔离 |
| `tests/test_splitter.py` | TextSplitter | 纯函数，无需隔离 |
| `tests/test_persister.py` | FilePersister | 用 `tempfile.TemporaryDirectory` 隔离文件系统 |
| `tests/test_fuser.py` | HybridFusion | 纯函数，无需隔离 |
| `tests/test_assembler.py` | DefaultAssembler | 纯函数，无需隔离 |
| `tests/test_retriever.py` | HybridRetriever | mock ChromaStore + BM25Index + Embedding |
| `tests/test_vectorizer.py` | ChromaVectorizer | mock IndexStore + ChromaStore + Embedding |
| `tests/test_loaders.py` | PDF/MD/Image/Word/Audio/Video Loader | mock 文件读取+外部调用 |

**测试原则**：
- 每个测试文件孤立测试一个组件
- 依赖外部服务（Chroma、Embedding API、ffmpeg）的组件用 mock 隔离
- 纯函数组件（cleaner、splitter、fuser）覆盖正常/边界/异常路径

### 14. 命名清理

统一全项目命名风格，使文件名/类名准确反映职责。

#### 14.1 文件名改动

| 当前 | 改为 | 原因 |
|------|------|------|
| `prompt/__init__.py` | `prompt/builder.py` | 实际代码不应写在 `__init__.py` 中 |
| `pipeline/rag_pipeline.py` | `pipeline/query.py` | `rag_` 前缀在 `rag_server/pipeline/` 下冗余 |
| `retrieval/base.py` | → `retrieval/retriever.py` + `retrieval/fuser.py` | 两个 ABC 不应放在同一个 `base.py` |

#### 14.2 类名改动

| 位置 | 当前 | 改为 | 理由 |
|------|------|------|------|
| `stores/persister.py` | `Persister` / `FilePersister` | `Storage` / `FileStorage` | "Persister" 非标准英语 |
| `stores/vectorizer.py` | `Vectorizer` / `ChromaVectorizer` | `Indexer` / `ChromaIndexer` | 实际做索引+嵌入，不止向量化 |
| `prompt/builder.py` | `Assembler` / `DefaultAssembler` | `PromptBuilder` / `DefaultPromptBuilder` | 职责就是拼 Prompt |
| `retrieval/fuser.py` | `Fuser` / `HybridFusion` | `Ranker` / `HybridRanker` | 做的是重排序 |
| `retrieval/stitcher.py` | `ChunkStitcher` | `ChunkJoiner` | "Stitcher" 不够直观 |
| `llm/openai.py` | `OpenAICompatibleLLM` | `OpenAILLM` | 太冗长 |
| `embedding/openai.py` | `OpenAICompatibleEmbedding` | `OpenAIEmbedding` | 太冗长 |
| `config.py` | `StitcherConfig` | `JoinerConfig` | 对应 `ChunkJoiner` |

#### 14.3 管道名

| 当前 | 改为 | 对称 |
|------|------|------|
| `IngestionPipeline` | 保留 | 写管道 |
| `RAGPipeline` | `QueryPipeline` | 读管道 |

#### 14.4 配置键名同步

config.yaml 和 config.py 中的 provider 键名同步更新：

| 当前 | 改为 |
|------|------|
| `pipeline.vectorizer` | `pipeline.indexer` |
| `pipeline.persister` | `pipeline.storage` |
| `retrieval.fuser` | `retrieval.ranker` |
| `retrieval.assembler` | —（asembler → prompt_builder 不影响 config 键名，改用 prompt_builder） |

> 注：config 中 `pipeline.splitter` / `pipeline.cleaner` / `retrieval.retriever` 名称清晰，保持不变。

### 15. ASR REST API 重写 + 视频导入修复

#### 15.1 问题

两问题：

1. **ASR SDK API 变更**：dashscope 1.26.6 的 `Recognition.call()` 改为实例方法，需 `self` + `file` 参数，且无法自定义 endpoint。DNS 解析失败导致无法连接。

2. **临时文件污染**：ffmpeg 提取的 `xxx_audio.wav` 写入 `input/` 目录，被 `list_input_files()` 当作独立文件处理。

#### 15.2 修复方案

**ASR：dashscope SDK → httpx REST API**

```python
async def transcribe(self, audio_path: str) -> str:
    # 1. Base64 编码音频文件
    audio_b64 = base64.b64encode(audio_data)
    data_uri = f"data:audio/wav;base64,{audio_b64}"

    # 2. POST 到 ASR_BASE_URL（来自 .env 配置）
    payload = {
        "model": self.model,
        "input": {"messages": [{"role": "user",
                    "content": [{"type": "input_audio",
                                 "input_audio": {"data": data_uri}}]}]},
        "parameters": {"format": "wav", "sample_rate": 16000},
    }
    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(self.base_url, json=payload, headers=headers)
    return self._extract_text(response.json())
```

**video loader：临时文件路径**

```python
# 旧：audio_path = video_path + "_audio.wav"  # 写入 input/ 目录
# 新：
fd, audio_path = tempfile.mkstemp(suffix="_audio.wav")  # 写入系统 temp
os.close(fd)
```

#### 15.3 .env 配置项

```env
ASR_PROVIDER=dashscope
ASR_BASE_URL=https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation
ASR_API_KEY=sk-xxx
ASR_MODEL=qwen-audio-3.0-asr-flash
```

**Rationale**：SDK 方式无法自定义 endpoint，且 DNS 解析受限。改用 httpx 直接调用 REST API，完全兼容 DashScope 企业版内网地址。

### 16. config 段名与代码类名对齐

#### 16.1 问题

`config.yaml` 的段名 `pipeline:` 和 `retrieval:` 过于泛泛，与代码中的具体类名 `IngestionPipeline`、`QueryPipeline` 不对应。

#### 16.2 改后映射

| config.yaml | config.py 数据类 | 代码类 |
|------------|-----------------|--------|
| `ingestion_pipeline:` | `IngestionPipelineConfig` | `IngestionPipeline` |
| `query_pipeline:` | `QueryPipelineConfig` | `QueryPipeline` |

#### 16.3 config.yaml 完整结构

```yaml
llm:
  provider: openai
  ...

embedding:
  provider: openai
  ...

asr:
  provider: dashscope
  ...

ingestion_pipeline:
  cleaner_provider: default
  splitter_provider: default
  storage_provider: file
  indexer_provider: chroma

query_pipeline:
  retriever_provider: hybrid
  ranker_provider: hybrid
  prompt_builder_provider: default
  vector_weight: 0.5
  vector_top_k: 20
  bm25_top_k: 20
  final_top_k: 10

data:
  root: ./data
```

**Rationale**：配置段名直接引用代码类名，阅读 `config.yaml` 即可知道对应哪个代码模块。新增管线只需在 `config.yaml` 加一段、在 `config.py` 加一个数据类，零歧义。

### 17. 模型调用目录归组（物理整洁）

#### 17.1 现状

`llm/`、`embedding/`、`asr/` 三个目录平铺在 `rag_server/` 下，它们都是调用外部 AI 模型 API 的模块，但没有统一的父目录。

#### 17.2 方案

纯物理移动，不改变任何接口、类名、逻辑：

```
rag_server/
└── models/               ← 新增父目录
    ├── __init__.py
    ├── llm/              ← 从 rag_server/llm/ 移入
    │   ├── base.py
    │   ├── openai.py
    │   └── anthropic.py
    ├── embedding/        ← 从 rag_server/embedding/ 移入
    │   ├── base.py
    │   ├── openai.py
    │   └── dashscope.py
    └── asr/              ← 从 rag_server/asr/ 移入
        ├── base.py
        └── dashscope.py
```

#### 17.3 需更新的导入路径

| 文件 | 旧导入 | 新导入 |
|------|--------|--------|
| `pipeline/query.py` | `auto_register("rag_server.llm")` | `auto_register("rag_server.models.llm")` |
|  | `auto_register("rag_server.embedding")` | `auto_register("rag_server.models.embedding")` |
|  | `from rag_server.llm.base import LLM` | `from rag_server.models.llm.base import LLM` |
| `pipeline/ingestion.py` | `auto_register("rag_server.embedding")` | `auto_register("rag_server.models.embedding")` |
| `loaders/video.py` | `import rag_server.asr.dashscope` | `import rag_server.models.asr.dashscope` |
| `loaders/audio.py` | `import rag_server.asr.dashscope` | `import rag_server.models.asr.dashscope` |
| `retrieval/hybrid.py` | `from rag_server.embedding...` | `from rag_server.models.embedding...` |
| `stores/vectorizer.py` | `from rag_server.embedding...` | `from rag_server.models.embedding...` |
| 各种测试 | `from rag_server.asr...` | `from rag_server.models.asr...` |

#### 17.4 不改的

- 所有类名（`OpenAILLM`, `OpenAIEmbedding`, `DashScopeASR` 等）
- 所有注册 key（`@register("llm", "openai")` 等）
- 所有接口方法（`chat()`, `embed()`, `transcribe()`）
- config 配置段名（`llm:`, `embedding:`, `asr:` 保持不变）

**Rationale**：纯物理归组，改动最小。找模型调用相关代码时一目了然，新增模型类型（如 image generation）直接加在 `models/` 下。

## Migration Plan

```
Step 1: 创建 llm/ + embedding/ 目录和 __init__.py 文件
Step 2: 写 llm/base.py + llm/openi.py + llm/anthopic.py
Step 3: 写 embeddng/base.py + embeddig/openi.py + embeddig/dashcope.py
Step 4: 更新 rag_pipeline.py 和 ingestion.py 的导入路径
Step 5: 删除 protocols/ 目录全部文件
Step 6: 删除 providers/ 目录全部文件
Step 7: 运行 tests/test_integration.py 验证通过
```

**回滚策略**: 保留新旧两个目录同时存在直到验证通过，验证后删除旧的。

## Risks / Trade-offs

| 风险 | 缓解措施 |
|------|---------|
| 合并过程中导入中断 | 按迁移计划分步执行，新旧目录共存直到验证通过 |
| Registry 在启动时未触发注册 | 确保每个新实现文件顶层的 `from .base import LLM` + `@register` 装饰器正确 |
| 遗漏旧文件导致残留 | 迁移完成后用 `git status` 确认所有旧文件已删除 |
| 外部消费者依赖内部导入路径 | 已确认无外部消费者，仅项目内部导入 |

## 18. 分块算法重写：步距累加 + 上下文重叠

### 问题

当前分块按段落独立成块，导致标题类短文本（如 `# 1`）成为独立小 chunk，检索价值为零。

### 方案：步距累加 + 上下文重叠

#### 配置参数

分块参数由 config.yaml / config.py 控制，不硬编码：

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `ingestion_pipeline.splitter_provider` | str | `default` | 分块器实现 |
| `ingestion_pipeline.chunk_size` | int | `1000` | 目标 chunk 大小（字符数） |
| `ingestion_pipeline.stride` | int | `800` | 滑动步距（字符数） |

`overlap` 由系统自动计算：`(chunk_size - stride) ÷ 2`，前后各重叠此值。

#### 完整算法

```
预处：扫描所有段落，如果某段 > stride（800），在里面插入断点

原文段落：
  P0(300)  P1(400)  P2(200)  P3(500)  P4(1200)  P5(100)
                                        ↑ 超过 800

处理长段落 P4(1200)：
                                      800      400
  P4(1200) ──────→ P4a(800) + P4b(400)
                     ↑              ↑
                   硬切             剩的

最终分段队列：
  P0(300)  P1(400)  P2(200)  P3(500)  P4a(800)  P4b(400)  P5(100)

累加过程（stride=800）：

  ① P0(300) → 累加=300 < 800 → 加 P1
     P1(400) → 累加=700 < 800 → 想加 P2(200)
     700+200=900 > 800 → 切！  断点在 P1 结尾

  ② P2(200) → 累加=200 < 800 → 加 P3(500)
     P3(500) → 累加=700 < 800 → 想加 P4a(800)
     700+800=1500 > 800 → 切！ 断点在 P3 结尾

  ③ P4a(800) → 累加=800 ≤ 800 → 想加 P4b(400)
     800+400=1200 > 800 → 切！ 断点在 P4a 结尾

  ④ P4b(400) → 累加=400 < 800 → 加 P5(100)
     400+100=500 < 800 → 继续...

得到断点索引后，拼接 overlap：

chunk_size=1000, stride=800 → overlap=100

        后重叠100                   后重叠100
Chunk 0: [0 ════════ 700 ┃══ 800)     ← P0+P1 + P2 前 100 字
                          ↑断点1

       前重叠100          后重叠100
Chunk 1: [600 ═ 700 ════════ 1200 ┃═══ 1300)
                      ↑断点1      ↑断点2

       前重叠100          后重叠100
Chunk 2: [1100 ═ 1200 ════════ 2000 ┃═══ 2100)
                      ↑断点2        ↑断点3

Chunk 内容 = 原文[start-overlap : 断点+overlap]
```

#### 边界规则

| 场景 | 处理 |
|------|------|
| 首段之前 | 不加前重叠（无文本） |
| 尾段之后 | 不加后重叠（无文本） |
| 单段 > stride | 段内按 stride 切分，产生人工断点 |
| 单段 > chunk_size | 退回到句号/逗号级别切分（fallback） |

#### 配置设计：所有模块统一使用区块注释切换模式

所有插拔模块（cleaner、splitter、storage、indexer、retriever、ranker 等）的参数按区块平铺在各自的配置段下。激活哪个实现就把哪个区块取消注释，互斥区块用 `#` 注释掉。

**激活 default 分块器：**

```yaml
ingestion_pipeline:
  cleaner_provider: default
  storage_provider: file
  indexer_provider: chroma

  # ---- Splitter: default（步距累加+重叠） ----
  splitter_provider: default
  chunk_size: 1000
  stride: 800

  # ---- Splitter: semantic（语义边界分块） ----
  # splitter_provider: semantic
  # chunk_size: 500
  # similarity_threshold: 0.85
```

**切换到 semantic 分块器：**

```yaml
ingestion_pipeline:
  cleaner_provider: default
  storage_provider: file
  indexer_provider: chroma

  # ---- Splitter: default（步距累加+重叠） ----
  # splitter_provider: default
  # chunk_size: 1000
  # stride: 800

  # ---- Splitter: semantic（语义边界分块） ----
  splitter_provider: semantic
  chunk_size: 500
  similarity_threshold: 0.85
```

系统只按 `splitter_provider` 的值创建对应的 splitter 实例。所有参数以 `**kwargs` 方式传递，每个 splitter 在 `__init__` 中声明自己需要的参数，不需要的被 `**kwargs` 吞掉。**此模式用于所有插拔模块（cleaner、storage、indexer、retriever、ranker 等），不限于 splitter。**

```python
@register("splitter", "default")
class TextSplitter(Splitter):
    def __init__(self, chunk_size=1000, stride=800, **kwargs):
        # stride 和 chunk_size 用得上
        # similarity_threshold 被 **kwargs 吞掉
        ...

@register("splitter", "semantic")
class SemanticSplitter(Splitter):
    def __init__(self, chunk_size=500, similarity_threshold=0.85, **kwargs):
        # chunk_size 和 similarity_threshold 用得上
        # stride 被 **kwargs 吞掉
        ...
```

**config.py `IngestionPipelineConfig` 新增字段：**

```python
@dataclass
class IngestionPipelineConfig:
    cleaner_provider: str = "default"
    splitter_provider: str = "default"
    chunk_size: int = 1000       # ← 新增
    stride: int = 800            # ← 新增
    storage_provider: str = "file"
    indexer_provider: str = "chroma"
```

**rag_server/pipeline/ingestion.py `_ensure_services()` 中创建 splitter 时传入参数：**

```python
self._splitter = Factory.create(
    "splitter", p.splitter_provider,
    chunk_size=p.chunk_size,
    stride=p.stride,
)
```

#### 改动点汇总

| 文件 | 改法 |
|------|------|
| `config.yaml` | `ingestion_pipeline:` 段新增 `chunk_size`、`stride` |
| `config.py` | `IngestionPipelineConfig` 新增 `chunk_size`、`stride` 字段 |
| `rag_server/text/splitter.py` | 重写 `split()` 方法，实现步距累加算法；`__init__` 加 `**kwargs` |
| `rag_server/pipeline/ingestion.py` | `_ensure_services()` 中创建 splitter 时传递配置参数 |