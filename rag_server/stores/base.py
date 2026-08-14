"""向量存储抽象接口。"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple


class VectorStore(ABC):
    """向量存储抽象接口。

    只存向量 + chunk_id，原文存于 IndexStore。
    """

    @abstractmethod
    async def add(self, chunk_id: str, vector: List[float], metadata: Optional[Dict] = None):
        ...

    @abstractmethod
    async def add_batch(self, ids: List[str], vectors: List[List[float]],
                         metadatas: Optional[List[Dict]] = None):
        ...

    @abstractmethod
    async def search(self, query_vector: List[float], top_k: int = 20) -> List[Tuple[str, float]]:
        """返回 [(chunk_id, score), ...]"""
        ...