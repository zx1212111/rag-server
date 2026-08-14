"""文档加载器抽象基类。"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class LoaderOutput:
    """加载器统一输出格式。"""
    md_text: str                          # 转换后的 Markdown 文本
    assets: List[Dict] = field(default_factory=list)  # 图片资产列表
    metadata: Dict = field(default_factory=dict)      # 文档元数据


class BaseLoader(ABC):
    """文档加载器抽象接口。

    所有加载器将源文件统一输出为 MD 文本 + 图片资产 + metadata。

    子类必须声明支持的扩展名:
        extensions = [".pdf"]
    """

    extensions: List[str] = []  # 子类覆盖，声明支持的文件扩展名

    @abstractmethod
    async def load(self, file_path: str) -> LoaderOutput:
        ...