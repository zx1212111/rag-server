"""导入引擎：扫描 input/ → 加载 → 清洗 → 分块 → 持久化 → 向量化。"""

import hashlib
import logging
import os
import time
from typing import List, Optional

from rag_server.config import Config
from rag_server.loaders.base import BaseLoader, LoaderOutput
from rag_server.registry import Factory, auto_register
from rag_server.text.cleaner import BaseCleaner
from rag_server.stores.document import DocumentStore
from rag_server.stores.index_store import IndexStore
from rag_server.utils.timer import timeit

auto_register("rag_server.loaders")
auto_register("rag_server.text")
auto_register("rag_server.stores")
auto_register("rag_server.models.embedding")

logger = logging.getLogger(__name__)


class IngestionPipeline:
    """导入引擎，处理 input/ 中的文件并构建索引。"""

    def __init__(self, config: Config):
        self.config = config
        self.doc_store = DocumentStore(config.data.root)
        self.index_store = IndexStore(config.data.index_path)
        self._cleaner: Optional[BaseCleaner] = None
        self._splitter = None
        self._persister = None
        self._vectorizer = None

    def _ensure_services(self):
        cfg = self.config
        p = cfg.ingestion_pipeline
        if self._cleaner is None:
            self._cleaner = Factory.create("cleaner", p.cleaner_provider)
        if self._splitter is None:
            self._splitter = Factory.create("splitter", p.splitter_provider,
                                              chunk_size=p.chunk_size,
                                              stride=p.stride)
        if self._persister is None:
            self._persister = Factory.create("storage", p.storage_provider,
                                              data_root=cfg.data.root)
        if self._vectorizer is None:
            self._vectorizer = Factory.create(
                "indexer", p.indexer_provider,
                index_path=cfg.data.index_path,
                vector_dir=cfg.data.vector_dir,
                embedding_provider=cfg.embedding.provider,
                base_url=cfg.embedding.base_url,
                api_key=cfg.embedding.api_key,
                model=cfg.embedding.model,
            )

    def _resolve_loader(self, file_path: str) -> Optional[BaseLoader]:
        """根据文件扩展名选择加载器。"""
        ext = os.path.splitext(file_path)[1].lower()
        from rag_server.registry import _registry
        for name, cls in _registry.get("loader", {}).items():
            if ext in getattr(cls, "extensions", []):
                return Factory.create("loader", name)
        logger.warning("不支持的文件类型: %s", file_path)
        return None

    @timeit
    async def run(self) -> str:
        """执行一次导入流程，返回处理结果描述。"""
        self._ensure_services()
        files = self.doc_store.list_input_files()

        if not files:
            return "没有待处理的文件"

        total = len(files)
        success = 0
        failed = 0
        total_chunks = 0
        results = []

        for file_path in files:
            start = time.time()
            doc_name = os.path.splitext(os.path.basename(file_path))[0]
            doc_id = hashlib.md5(file_path.encode()).hexdigest()[:12]

            try:
                # 1. 加载
                loader = self._resolve_loader(file_path)
                if loader is None:
                    failed += 1
                    results.append(f"❌ {file_path}: 不支持的格式")
                    continue

                output: LoaderOutput = await loader.load(file_path)

                # 2. 清洗
                cleaned = self._cleaner.clean(output.md_text)

                # 3. 分块
                chunks = self._splitter.split(cleaned, doc_id)
                total_chunks += len(chunks)

                # 4. 持久化（保存 MD + 图片）
                await self._persister.persist(chunks, output.assets, doc_name)

                # 5. 向量化（索引 + 嵌入 + 向量存储）
                await self._vectorizer.index(chunks)

                # 6. 源文件移入 processed
                self.doc_store.move_to_processed(file_path)

                elapsed = time.time() - start
                success += 1
                results.append(f"✅ {file_path}: {len(chunks)} chunks ({elapsed:.1f}s)")

            except Exception as e:
                elapsed = time.time() - start
                failed += 1
                logger.exception("处理失败: %s", file_path)
                results.append(f"❌ {file_path}: {e} ({elapsed:.1f}s)")

        # 全部文件处理完后重建 BM25
        if success > 0:
            try:
                from rag_server.retrieval.bm25 import BM25Index
                bm25 = BM25Index(self.config.data.sparse_dir)
                bm25.rebuild_from_index(self.index_store)
                results.append(f"📊 BM25 已重建（{self.index_store.count_chunks()} chunks）")
            except Exception as e:
                logger.exception("BM25 重建失败")
                results.append(f"⚠️ BM25 重建失败: {e}")

        summary = (
            f"处理完成：共 {total} 个文件，"
            f"成功 {success}，失败 {failed}，"
            f"新增 {total_chunks} 个 chunk"
        )
        results.insert(0, summary)
        return "\n".join(results)