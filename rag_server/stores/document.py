"""文档存储：MD 文件和图片资产的本地文件管理。"""

import os
import shutil
from pathlib import Path
from typing import Dict, List, Optional

from rag_server.registry import get_supported_extensions


class DocumentStore:
    """文档存储管理。

    职责：
    - MD 文件落盘到 docs/
    - 图片资产落盘到 assets/
    - 源文件从 input/ 移到 processed/
    """

    def __init__(self, data_root: str = "./data"):
        self.root = Path(data_root)
        self.docs_dir = self.root / "docs"
        self.assets_dir = self.root / "assets"
        self.input_dir = self.root / "input"
        self.processed_dir = self.root / "processed"

        # 确保目录存在
        for d in [self.docs_dir, self.assets_dir, self.input_dir, self.processed_dir]:
            d.mkdir(parents=True, exist_ok=True)

    def save_doc(self, filename: str, md_text: str) -> str:
        """保存 MD 文件到 docs/，返回路径。"""
        doc_path = self.docs_dir / filename
        doc_path.write_text(md_text, encoding="utf-8")
        return str(doc_path)

    def save_asset(self, doc_name: str, filename: str, data: bytes) -> str:
        """保存图片到 assets/{doc_name}/，返回相对路径。"""
        asset_dir = self.assets_dir / doc_name
        asset_dir.mkdir(parents=True, exist_ok=True)
        asset_path = asset_dir / filename
        asset_path.write_bytes(data)
        return f"assets/{doc_name}/{filename}"

    def move_to_processed(self, file_path: str):
        """将已处理的源文件移入 processed/。"""
        src = Path(file_path)
        if src.exists():
            dst = self.processed_dir / src.name
            shutil.move(str(src), str(dst))

    def list_input_files(self) -> List[str]:
        """列出 input/ 目录中待处理的文件。"""
        if not self.input_dir.exists():
            return []
        files = []
        supported = get_supported_extensions()
        for f in self.input_dir.iterdir():
            if f.is_file() and f.suffix.lower() in supported:
                files.append(str(f))
        return sorted(files)

    def list_docs(self) -> List[Dict]:
        """列出 docs/ 中已处理的文档信息。"""
        if not self.docs_dir.exists():
            return []
        docs = []
        for f in self.docs_dir.iterdir():
            if f.is_file() and f.suffix == ".md":
                docs.append({
                    "filename": f.name,
                    "path": str(f),
                    "size": f.stat().st_size,
                })
        return sorted(docs, key=lambda x: x["filename"])