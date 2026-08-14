## Context

当前 `rag-server` 只支持纯文本问答。用户无法直接带着图片/视频/音频等附件提问，需要先手动导入知识库再查询，流程割裂。

核心约束：
- LLM 不要求多模态能力，保持纯文本接口
- 完全复用现有的 Loader 管线处理文件（ImageLoader / VideoLoader / AudioLoader / PDFLoader / WordLoader / MarkdownLoader）
- 不修改现有 `query()` 接口，只新增 `query_with_files()`

## Goals / Non-Goals

**Goals:**
- 新增 `rag_server/question/` 模块，提供 `Question(ABC)` 抽象接口
- 新增 `rag-server ask` CLI 交互命令
- 复用 Loader 将图片/视频/音频/PDF/Word/MD 转为文本后执行 RAG
- 临时目录用完自动清理
- `question` 组件可插拔，由 config 控制实现

**Non-Goals:**
- 不改 LLM 接口（不引入多模态）
- 不改 Embedding 接口
- 不改 Retriever / Ranker / PromptBuilder
- 不改 MCP 工具接口
- 不保存对话记录

## Decisions

### 1. question/ 模块结构

```
rag_server/
└── question/
    ├── __init__.py
    ├── base.py             ← Question(ABC): ask(files, question) → str
    └── handler.py          ← DefaultQuestionHandler @register("question", "default")
```

### 2. Question 抽象接口

```python
from abc import ABC, abstractmethod
from typing import List

class Question(ABC):
    """文件提问抽象。管线只调 ask()，不关心文件如何转文本。"""

    @abstractmethod
    async def ask(self, file_paths: List[str], question: str) -> str:
        """处理文件列表 + 问题，返回合并后的查询文本。"""
        ...
```

### 3. DefaultQuestionHandler 实现

```python
@register("question", "default")
class DefaultQuestionHandler(Question):
    """默认实现：用 Loader 处理各类文件，合并为 MD 文本。"""

    def __init__(self):
        auto_register("rag_server.loaders")

    async def ask(self, file_paths: List[str], question: str) -> str:
        parts = []
        for fp in file_paths:
            loader = self._resolve_loader(fp)
            if loader:
                output = await loader.load(fp)
                parts.append(output.md_text)
        parts.append(question)
        return "\n\n".join(parts)

    def _resolve_loader(self, file_path: str) -> Optional[BaseLoader]:
        ext = os.path.splitext(file_path)[1].lower()
        from rag_server.registry import _registry
        for name, cls in _registry.get("loader", {}).items():
            if ext in getattr(cls, "extensions", []):
                return Factory.create("loader", name)
        return None
```

### 4. QueryPipeline 扩展

```python
class QueryPipeline:
    # ... 已有 query() ...

    async def query_with_files(
        self,
        file_paths: List[str],
        question: str,
        stream: bool = True,
    ) -> AsyncIterator[str]:
        question_handler = Factory.create(
            "question", self.config.query_pipeline.question_provider,
        )
        query_text = await question_handler.ask(file_paths, question)
        async for chunk in self.query(query_text, stream=stream):
            yield chunk
```

### 5. Config 扩展

```python
@dataclass
clas QueryPielineConfig:
    question_proider: str = "default"
    # ... 现有字段 ...
```

```yaml
quey_pipeline:
  queston_provider: default    # 文件提问处理器
  retriever_provider: hybrid
  ranker_provider: hybrid
  prompt_builder_provider: default
  ...
```

### 6. 统一投递目录（CLI / Web / MCP 共用）

三个接口共享同一个固定目录 `data/ask_incoming/`，生命周期规则一致：

- 目录不存在时自动创建
- 处理完成后只删除内部文件，**不删目录本身**
- 各接口无需关心目录管理，统一由 `QuestionHandler` 内部维护

```
data/
├── ask_incoming/         ← 文件提问投递箱（持久存在）
│   ├── photo.jpg         ← 用户放入
│   ├── doc.pdf
│   └── ...               ← 处理后自动删除
├── input/                ← 知识库导入（独立）
└── ...
```

**目录路径配置**：`config.data.ask_incoming_dir`，默认 `./data/ask_incoming/`

#### 6.1 CLI `ask` 命令交互流

```python
async def _run_ask():
    incoming = Path(cfg.data.root) / "ask_incoming"
    incoming.mkdir(parents=True, exist_ok=True)

    files = _scan_files(incoming)
    if files:
        print(f"检测到 {len(files)} 个文件")
    else:
        print("未检测到附件，将进行纯文本提问")

    question = input("请输入问题：")
    if not question:
        return

    pipeline = QueryPipeline(config)
    async for chunk in pipeline.query_with_files(files, question):
        print(chunk, end="", flush=True)
    print()

    _clean_files(incoming)  # 只删文件，不删目录
```

#### 6.2 MCP tool

```python
@server.tool()
async def ask_with_file(question: str) -> str:
    """当用户询问关于文件（图片/视频/音频/PDF/Word/Markdown 等）的问题时，
    使用此工具处理文件并回答问题。

    使用方式：
    1. 工具会自动创建投递目录
    2. 如果目录为空，会返回目录路径
    3. 将目录路径告知用户，请用户将文件放入该目录
    4. 用户放好文件后，以"查看文件+问题"的方式重新提问即可
    """
    incoming = Path(config.data.root) / "ask_incoming"
    incoming.mkdir(parents=True, exist_ok=True)

    files = [f for f in incoming.iterdir() if f.is_file()]
    if not files:
        return (
            f"未检测到文件。请告知用户将文件放入以下目录，"
            f"然后以'查看文件+问题'的方式重新提问：\n{incoming}"
        )

    answer_parts = []
    async for chunk in pipeline.query_with_files(
        [str(f) for f in files], question,
    ):
        answer_parts.append(chunk)
    answer = "".join(answer_parts)

    for f in files:
        f.unlink()

    return answer
```

#### 6.3 Web（Streamlit）

```python
uploaded_files = st.file_uploader("选择文件", accept_multiple_files=True)
question = st.chat_input("请输入问题")

if question:
    incoming = Path(cfg.data.root) / "ask_incoming"
    incoming.mkdir(parents=True, exist_ok=True)
    fo uf in uploade_files or []:
        (incoming / uf.name).writ_bytes(uf.gtvalue())
    
    anser = ""
    async for chunk ipipeline.quey_with_files(...):
        anser += chnk
    t.markdwn(aner)
    lean_fies(incming)

### 7. 修改文清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `a_server/question/__init__.py` | **新增** | 空 init |
| `a_server/question/base.py` | **新增** | `Qestion(BC)` 抽象接口 |
| `a_server/question/handler.py` | **新增** | `DefaultQestionHandler` 实现 |
| `ag_server/config.py` | 修改 | `QueryPielineConfig` 新增 `question_provider` |
| `ag_server/pipeline/query.py` | 修改 | 新增 `query_with_files()` 方法 |
| `ag_server/interfaces/cli.py` | 修改 | 新增 `ask` 命令 |
| `config.yaml` | 修改 | `uery_pipeline` 新增 `question_provider` |

## Risks / Trade-offs

| 风险 | 缓解措施 |
|------|---------|
| 大文件（长视频）加载慢 | 临时目录文件处理是同步的，用户等待时能看到进度 |
| 临时目录残留（异常退出时） | `try/finally` 保证清理，加上 `ignore_errors=True` |
| Loader 本身可能抛异常（ffmpeg 缺失等） | 每个文件单独 try/except，失败文件跳过不影响其他文件 |