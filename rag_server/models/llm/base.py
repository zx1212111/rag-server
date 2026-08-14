"""LLM 能力抽象接口。"""

from abc import ABC, abstractmethod
from typing import AsyncIterator, Dict, List


class LLM(ABC):
    """LLM 能力提供者抽象接口。"""

    @abstractmethod
    async def chat(
        self,
        messages: List[Dict[str, str]],
        stream: bool = False,
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        ...