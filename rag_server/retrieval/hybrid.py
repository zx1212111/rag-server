"""混合检索：向量检索 + BM25 关键词检索。"""

from typing import List, Tuple

from rag_server.registry import Factory, register
from rag_server.stores.chroma import ChromaStore
from rag_server.retrieval.bm25 import BM25Index
from rag_server.retrieval.base import Retriever
from rag_server.utils.timer import timeit


@register("retriever", "hybrid")
class HybridRetriever(Retriever):
    """双路混合检索：向量检索 + BM25 关键词检索。"""

    def __init__(
        self,
        vector_dir: str = "./data/vector",
        sparse_dir: str = "./data/sparse",
        embedding_provider: str = "openai",
        base_url: str = "",
        api_key: str = "",
        model: str = "text-embedding-3-small",
        vector_top_k: int = 20,
        bm25_top_k: int = 20,
    ):
        self.vector_store = ChromaStore(persist_dir=vector_dir)
        self.bm25 = BM25Index(sparse_dir=sparse_dir)
        self.vector_top_k = vector_top_k
        self.bm25_top_k = bm25_top_k
        self._embedding = Factory.create(
            "embedding", embedding_provider,
            base_url=base_url, api_key=api_key, model=model,
        )

    @timeit
    async def retrieve(self, query: str, top_k: int = 20) -> List[Tuple[str, float]]:
        """执行混合检索，返回向量和 BM25 两路结果。"""
        query_vector = (await self._embedding.embed([query]))[0]
        vector_results = await self.vector_store.search(
            query_vector, top_k=self.vector_top_k
        )
        bm25_results = self.bm25.search(
            query, top_k=self.bm25_top_k
        )
        # 双路结果打包返回
        return vector_results + bm25_results