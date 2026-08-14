"""持久化抽象：管线只调 persist()，不管存文件还是存数据库。"""

from abc import ABC, abstractmethod
from typing import Dict, List

from rag_server.registry import register
from rag_server.text.chunk import Chunk


class Storage(ABC):
    """持久化抽象。管线只调 persist()，不关心存储实现。"""

    @abstractmethod
    async def persist(
        self,
        chunks: List[Chunk],
        assets: List[Dict],
        doc_name: str,
    ) -> None:
        ...


@register("storage", "file")
class FileStorage(Storage):
    """文件系统持久化实现。保存 MD 原文到 docs/，图片资产到 assets/。"""

    def __init__(self, data_root: str = "./data"):
        from pathlib import Path
        self.docs_dir = Path(data_root) / "docs"
        self.assets_dir = Path(data_root) / "assets"
        self.docs_dir.mkdir(parents=True, exist_ok=True)
        self.assets_dir.mkdir(parents=True, exist_ok=True)

    async def persist(
        self,
        chunks: List[Chunk],
        assets: List[Dict],
        doc_name: str,
    ) -> None:
        """保存 MD 原文和图片资产。"""
        # 保存 MD
        md_text = "\n\n".join(c.content for c in chunks)
        doc_path = self.docs_dir / f"{doc_name}.md"
        doc_path.write_text(md_text, encoding="utf-8")

        # 保存图片资产
        for asset in assets:
            asset_dir = self.assets_dir / doc_name
            asset_dir.mkdir(parents=True, exist_ok=True)
            asset_path = asset_dir / asset["filename"]
            asset_path.write_bytes(asset["data"])