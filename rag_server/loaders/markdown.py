"""Markdown 文档加载器。

直接读取 .md 文件，提取 YAML frontmatter 作为 metadata，检测内嵌图片。
"""

import os
import re
import hashlib
from typing import Dict, List

from rag_server.registry import register
from rag_server.utils.timer import timeit
from .base import BaseLoader, LoaderOutput


@register("loader", "md")
class MarkdownLoader(BaseLoader):
    """Markdown 加载器。"""

    extensions = [".md"]

    @timeit
    async def load(self, file_path: str) -> LoaderOutput:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        # 提取 YAML frontmatter
        metadata: Dict = {"source": file_path}
        md_body = content
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                frontmatter = parts[1].strip()
                for line in frontmatter.split("\n"):
                    if ":" in line:
                        k, v = line.split(":", 1)
                        metadata[k.strip()] = v.strip()
                md_body = parts[2].strip()

        # 检测内嵌图片并提取为资产
        doc_name = os.path.splitext(os.path.basename(file_path))[0]
        assets: List[Dict] = []
        img_pattern = re.compile(r"!\[.*?\]\((.*?)\)")

        for match in img_pattern.finditer(md_body):
            img_path = match.group(1)
            if os.path.exists(img_path):
                with open(img_path, "rb") as f:
                    img_data = f.read()
                img_hash = hashlib.md5(img_data).hexdigest()[:12]
                ext = os.path.splitext(img_path)[1] or ".png"
                assets.append({
                    "filename": f"{img_hash}{ext}",
                    "data": img_data,
                    "original": img_path,
                })

        return LoaderOutput(
            md_text=md_body,
            assets=assets,
            metadata=metadata,
        )