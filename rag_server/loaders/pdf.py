"""PDF 文档加载器。

基于 PyMuPDF 提取文本和图片，保留坐标信息用于重建阅读顺序。
"""

import hashlib
import os
from typing import Dict, List, Optional

try:
    import pymupdf as fitz
except ImportError:
    import fitz  # 旧版兼容

from rag_server.registry import register
from rag_server.utils.timer import timeit
from .base import BaseLoader, LoaderOutput


@register("loader", "pdf")
class PDFLoader(BaseLoader):
    """PDF 加载器，支持文本提取、图片提取、扫描件 OCR。"""

    extensions = [".pdf"]

    def __init__(self, strategy: str = "auto"):
        self.strategy = strategy  # text_only | auto | ocr_all | multimodal

    @timeit
    async def load(self, file_path: str) -> LoaderOutput:
        doc_name = os.path.splitext(os.path.basename(file_path))[0]
        md_parts: List[str] = []
        assets: List[Dict] = []
        page_texts: List[str] = []

        doc = fitz.open(file_path)
        for page_num, page in enumerate(doc):
            # 提取文本块（带坐标）
            blocks = page.get_text("blocks")
            text_blocks = [b for b in blocks if b[6] == 0]  # block[6]==0 表示文本块
            image_blocks = [b for b in blocks if b[6] == 1]  # block[6]==1 表示图片块

            # 按 (y, x) 坐标排序，保持阅读顺序
            text_blocks.sort(key=lambda b: (b[1], b[0]))

            # 提取文本
            page_texts.append(f"## 第 {page_num + 1} 页\n")
            for block in text_blocks:
                text = block[4].strip()
                if text:
                    page_texts.append(text)
                    page_texts.append("")

            # 提取内嵌图片
            for img_info in image_blocks:
                xref = img_info[4] if isinstance(img_info[4], int) else img_info[-1]
                if isinstance(xref, int):
                    try:
                        pix = fitz.Pixmap(doc, xref)
                        img_bytes = pix.tobytes("png")
                        img_hash = hashlib.md5(img_bytes).hexdigest()[:12]
                        img_filename = f"p{page_num + 1}_{img_hash}.png"
                        assets.append({
                            "filename": img_filename,
                            "data": img_bytes,
                            "page": page_num + 1,
                        })
                        md_parts.append(
                            f"![第{page_num + 1}页图片](assets/{doc_name}/{img_filename})"
                        )
                        md_parts.append(
                            f"<!-- asset-id: {img_hash} | page: {page_num + 1} "
                            f"| type: image -->"
                        )
                    except Exception:
                        pass  # 跳过无法提取的图片

        md_text = "\n".join(page_texts)
        page_count = len(doc)
        doc.close()

        return LoaderOutput(
            md_text=md_text,
            assets=assets,
            metadata={"source": file_path, "pages": page_count},
        )