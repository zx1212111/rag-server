"""Chroma 向量存储实现。

只存向量 + chunk_id，原文不写入 Chroma。
"""

from typing import Any, Dict, List, Optional, Tuple

from rag_server.registry import register
from rag_server.utils.timer import timeit
from .base import VectorStore


@register("vs", "chroma")
class ChromaStore(VectorStore):
    """基于 Chroma 的向量存储。"""

    def __init__(self, persist_dir: str = "./data/vector", collection_name: str = "rag_docs"):
        self._collection = None
        self._persist_dir = persist_dir
        self._collection_name = collection_name
        self._client = None

    def _ensure_client(self):
        if self._client is None:
            import chromadb
            self._client = chromadb.PersistentClient(path=self._persist_dir)
            self._collection = self._client.get_or_create_collection(
                name=self._collection_name,
                metadata={"hnsw:space": "cosine"},
            )

    @timeit
    async def add(self, chunk_id: str, vector: List[float], metadata: Optional[Dict] = None):
        self._ensure_client()
        m = (metadata or {}) or {}
        if not m:
            m = {"chunk_id": chunk_id}
        self._collection.upsert(
            ids=[chunk_id],
            embeddings=[vector],
            metadatas=[m],
        )

    @timeit
    async def add_batch(self, ids: List[str], vectors: List[List[float]],
                         metadatas: Optional[List[Dict]] = None):
        self._ensure_client()
        metas = []
        for i in range(len(ids)):
            m = (metadatas[i] if metadatas and i < len(metadatas) else {}) or {}
            if not m:
                m = {"chunk_id": ids[i]}
            metas.append(m)
        # 使用 upsert 而非 add，崩溃后重跑不会因重复 ID 报错
        self._collection.upsert(
            ids=ids,
            embeddings=vectors,
            metadatas=metas,
        )

    @timeit
    async def search(self, query_vector: List[float], top_k: int = 20) -> List[Tuple[str, float]]:
        self._ensure_client()
        results = self._collection.query(
            query_embeddings=[query_vector],
            n_results=top_k,
        )
        ids = results.get("ids", [[]])[0]
        distances = results.get("distances", [[]])[0]
        # 转换为相似度分数（1 - distance）
        scores = [1 - d for d in distances]
        return list(zip(ids, scores))