"""文件提问抽象接口。"""

from abc import ABC, abstractmethod
from typing import List


class Question(ABC):
    """文件提问抽象。管线只调 ask()，不关心文件如何转文本。"""

    @abstractmethod
    async def ask(self, file_paths: List[str], question: str) -> str:
        """处理文件列表 + 问题，返回合并后的查询文本。"""
        ...