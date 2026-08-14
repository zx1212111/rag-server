"""Embedding 能力抽象接口。"""

from abc import ABC, abstractmethod
from typing import List


class Embedding(ABC):
    """文本嵌入能力提供者抽象接口。"""

    @abstractmethod
    async def embed(self, texts: List[str]) -> List[List[float]]:
        ...