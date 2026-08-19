"""RAG 查询管线：检索 → 融合 → 组装 → LLM 生成。"""

import logging
from typing import AsyncIterator, List, Optional, Tuple

from rag_server.config import Config
from rag_server.registry import Factory, auto_register
from rag_server.retrieval.base import Retriever, Ranker
from rag_server.stores.index_store import IndexStore
from rag_server.utils.timer import timeit
from rag_server.models.llm.base import LLM

auto_register("rag_server.models.llm")
auto_register("rag_server.models.embedding")
auto_register("rag_server.retrieval")
auto_register("rag_server.prompt")

logger = logging.getLogger(__name__)


class QueryPipeline:
    """RAG 查询编排管线。所有步骤由 config 驱动。"""

    def __init__(self, config: Config):
        self.config = config
        self.index_store = IndexStore(config.data.index_path)
        self._retriever: Optional[Retriever] = None
        self._ranker: Optional[Ranker] = None
        self._prompt_builder = None
        self._llm: Optional[LLM] = None

    def _ensure_services(self):
        """确保所有服务已创建。"""
        cfg = self.config
        r = cfg.query_pipeline  #拿到config中的query_pipeline配置
        if self._retriever is None:
            self._retriever = Factory.create(
                "retriever", r.retriever_provider,
                vector_dir=cfg.data.vector_dir,
                sparse_dir=cfg.data.sparse_dir,
                embedding_provider=cfg.embedding.provider,
                base_url=cfg.embedding.base_url,
                api_key=cfg.embedding.api_key,
                model=cfg.embedding.model,
                vector_top_k=r.vector_top_k,
                bm25_top_k=r.bm25_top_k,
            )
        if self._ranker is None:
            self._ranker = Factory.create(
                "ranker", r.ranker_provider,
                vector_weight=r.vector_weight,
                final_top_k=r.final_top_k,
            )
        if self._prompt_builder is None:
            self._prompt_builder = Factory.create(
                "prompt_builder", r.prompt_builder_provider,
                max_chars=cfg.llm.max_chars,
            )
        if self._llm is None:
            self._llm = Factory.create(
                "llm", cfg.llm.provider,
                base_url=cfg.llm.base_url,
                api_key=cfg.llm.api_key,
                model=cfg.llm.model,
            )

    def is_index_empty(self) -> bool:
        """检查索引是否为空（用于首次查询判断）。"""
        return self.index_store.count_chunks() == 0

    def _resolve_chunks(self, fused_ids: List[str]) -> str:
        """根据 fused_ids 获取完整文本。"""
        if not fused_ids:
            return ""

        chunks = []
        for cid in fused_ids:
            entry = self.index_store.get(cid)
            if entry:
                chunks.append(entry)

        if not chunks:
            return ""

        return "\n\n".join(c.get("text", "") for c in chunks)

    @timeit
    async def query(self, query: str, stream: bool = True) -> AsyncIterator[str]:
        """执行 RAG 查询，返回生成结果。

        流程：
        1. 检索（Retriever）
        2. 融合（Fuser）
        3. 上下文组装（Assembler）
        4. LLM 生成
        """

        self._ensure_services()  # 确保服务已创建

        # 1. 检索
        results = await self._retriever.retrieve(query)

        # 2. 排序
        fused_ids = self._ranker.rank(results)

        if not fused_ids:
            yield "未找到相关信息"
            return

        # 3. 获取完整文本 + 组装 Prompt
        context = self._resolve_chunks(fused_ids)
        if not context:
            yield "未找到相关信息"
            return

        messages = await self._prompt_builder.build(context, query)

        # 4. LLM 生成
        async for chunk in self._llm.chat(messages, stream=stream,
                                          temperature=self.config.llm.temperature):
            yield chunk