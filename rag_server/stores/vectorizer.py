"""向量化抽象：管线只调 vectorize()，不关心用哪个向量库。"""

from abc import ABC, abstractmethod
from typing import List

from rag_server.registry import Factory, register
from rag_server.stores.chroma import ChromaStore
from rag_server.stores.index_store import IndexStore
from rag_server.text.chunk import Chunk


class Indexer(ABC):
    """索引抽象。管线只调 index()，嵌入和存储由实现决定。"""

    @abstractmethod
    async def index(self, chunks: List[Chunk]) -> None:
        ...


@register("indexer", "chroma")
class ChromaIndexer(Indexer):
    """Chroma 向量化实现。构建索引 + 嵌入 + Chroma 存储。"""

    def __init__(
        self,
        index_path: str = "./data/index.json",
        vector_dir: str = "./data/vector",
        embedding_provider: str = "openai",
        base_url: str = "",
        api_key: str = "",
        model: str = "text-embedding-3-small",
    ):
        self.index_store = IndexStore(index_path)
        self.vector_store = ChromaStore(persist_dir=vector_dir)
        self.embedding = Factory.create(
            "embedding", embedding_provider,
            base_url=base_url, api_key=api_key, model=model,
        )

    async def index(self, chunks: List[Chunk]) -> None:
        """为所有 chunk 构建索引、生成嵌入并存入向量库。"""
        # 在内存中收集所有条目，批量写入 index.json（避免逐条读写）
        entries = []
        for chunk in chunks:
            entries.append({
                "chunk_id": chunk.id,
                "text": chunk.content,
                "doc_id": chunk.doc_id,
                "doc_path": "",
                "chunk_index": chunk.chunk_index,
                "start_char": chunk.start_char,
                "end_char": chunk.end_char,
                "metadata": chunk.metadata,
            })
        self.index_store.add_batch(entries)  # 写入 index.json

        # 嵌入并存入 Chroma
        texts = [c.content for c in chunks]
        vectors = await self.embedding.embed(texts)
        chunk_ids = [c.id for c in chunks]
        await self.vector_store.add_batch(chunk_ids, vectors)