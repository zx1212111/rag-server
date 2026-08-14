"""检索与融合抽象接口。管线只调 retrieve() / fuse()，不关心具体策略。"""

from abc import ABC, abstractmethod
from typing import List, Tuple


class Retriever(ABC):
    """检索抽象。管线只调 retrieve(query)，不关心走什么引擎。"""

    @abstractmethod
    async def retrieve(self, query: str, top_k: int = 20) -> List[Tuple[str, float]]:
        """返回 [(chunk_id, score), ...]"""
        ...


class Ranker(ABC):
    """排序抽象。管线只调 rank()，不关心排序策略。"""

    @abstractmethod
    def rank(self, results: List[Tuple[str, float]]) -> List[str]:
        """对检索结果排序，返回排序后的 chunk_id 列表。"""
        ...