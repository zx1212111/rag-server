"""图片文档加载器。

针对纯图片文件（截图、图表等），生成描述文本。
"""

import os
import hashlib
from typing import Dict, List

from rag_server.registry import register
from rag_server.utils.timer import timeit
from .base import BaseLoader, LoaderOutput


@register("loader", "image")
class ImageLoader(BaseLoader):
    """图片加载器。

    strategy: text_only | auto | ocr_all | multimodal
    """

    extensions = [".png", ".jpg", ".jpeg", ".gif", ".bmp"]

    def __init__(self, strategy: str = "auto"):
        self.strategy = strategy

    @timeit
    async def load(self, file_path: str) -> LoaderOutput:
        with open(file_path, "rb") as f:
            img_data = f.read()

        ext = os.path.splitext(file_path)[1].lower()
        img_hash = hashlib.md5(img_data).hexdigest()[:12]
        filename = f"{img_hash}{ext}"

        # 基础描述
        desc = f"![图片](assets/{filename})"

        md_text = f"""## 图片文件

{desc}

<!-- asset-id: {img_hash} | type: image | strategy: {self.strategy} -->
"""

        return LoaderOutput(
            md_text=md_text,
            assets=[{
                "filename": filename,
                "data": img_data,
                "strategy": self.strategy,
            }],
            metadata={"source": file_path, "strategy": self.strategy},
        )