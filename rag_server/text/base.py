"""文本分块抽象接口。"""

from abc import ABC, abstractmethod
from typing import List

from .chunk import Chunk


class Splitter(ABC):
    """文本分块器抽象。管线只调 split()，不关心分块策略。"""

    @abstractmethod
    def split(self, text: str, doc_id: str) -> List[Chunk]:
        ...