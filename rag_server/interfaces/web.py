"""Streamlit Web 界面。

左栏：检索/LLM/拼接参数
主区域：问答交互
右栏：Ingestion 管线参数（可折叠）
"""

import asyncio

import streamlit as st

from rag_server.config import load_config
from rag_server.pipeline.query import QueryPipeline
from rag_server.pipeline.ingestion import IngestionPipeline
from rag_server.stores.index_store import IndexStore
from rag_server.interfaces.cli import clean_data


def get_pipeline(config):
    return QueryPipeline(config)


async def stream_response(pipeline: QueryPipeline, query: str, stream: bool):
    async for chunk in pipeline.query(query, stream=stream):
        yield chunk


async def run_ingest(config):
    pipeline = IngestionPipeline(config)
    return await pipeline.run()


def main():
    st.set_page_config(page_title="知识库问答", page_icon="📖", layout="wide")

    config = load_config()
    index_store = IndexStore(config.data.index_path)

    # ===== 左侧栏：查询/LLM/拼接参数 =====
    with st.sidebar:
        st.header("⚙️ 检索设置")
        vector_weight = st.slider("向量检索比重", 0.0, 1.0,
                                  config.query_pipeline.vector_weight, 0.05)
        vector_top_k = st.number_input("向量 Top-K", 1, 100,
                                       config.query_pipeline.vector_top_k)
        bm25_top_k = st.number_input("BM25 Top-K", 1, 100,
                                     config.query_pipeline.bm25_top_k)
        final_top_k = st.number_input("最终返回条数", 1, 50,
                                      config.query_pipeline.final_top_k)

        st.header("🤖 LLM 设置")
        model = st.text_input("模型", config.llm.model)
        temperature = st.slider("温度", 0.0, 2.0, config.llm.temperature, 0.1)
        max_chars = st.number_input("最大字符数", 1000, 100000,
                                    config.llm.max_chars, 1000)
        stream = st.checkbox("流式输出", config.llm.stream)

        # 拼接设置已移至右侧系统配置

    # ===== 右侧栏：模型配置 + Ingestion 参数（可折叠） =====
    with st.expander("⚙️ 系统配置", expanded=False):
        st.markdown("**🧠 模型配置**（修改请编辑 `.env` 文件）")
        st.code(
            f"LLM:       provider={config.llm.provider}\n"
            f"           model={config.llm.model}\n"
            f"           base_url={config.llm.base_url}\n"
            f"           api_key={'*' * 8}{config.llm.api_key[-4:] if len(config.llm.api_key) > 4 else '****'}\n"
            f"Embedding: provider={config.embedding.provider}\n"
            f"           model={config.embedding.model}\n"
            f"           base_url={config.embedding.base_url}\n"
            f"           api_key={'*' * 8}{config.embedding.api_key[-4:] if len(config.embedding.api_key) > 4 else '****'}\n"
            f"ASR:       provider={config.asr.provider}\n"
            f"           model={config.asr.model}\n"
            f"           base_url={config.asr.base_url}\n"
            f"           api_key={'*' * 8}{config.asr.api_key[-4:] if len(config.asr.api_key) > 4 else '****'}",
            language="111",
        )

        st.markdown("---")
        st.markdown("**⚙️ Ingestion Pipeline**")

        col1, col2 = st.columns(2)
        with col1:
            chunk_size = st.number_input("分块大小 (chunk_size)", 100, 5000,
                                         config.ingestion_pipeline.chunk_size, 100)
        with col2:
            stride = st.number_input("滑动步距 (stride)", 100, 5000,
                                      config.ingestion_pipeline.stride, 100)

        cleaner = st.selectbox("文本清洗 (cleaner)", ["default", "minimal", "verbose"],
                                index=0)
        splitter = st.text_input("分块器 (splitter)", config.ingestion_pipeline.splitter_provider)
        storage = st.text_input("持久化 (storage)", config.ingestion_pipeline.storage_provider)
        indexer = st.text_input("索引器 (indexer)", config.ingestion_pipeline.indexer_provider)

        st.markdown("---")
        st.markdown("**📊 知识库状态**")
        files = index_store.count_unique_docs()
        chunks = index_store.count_chunks()
        st.metric("已处理文件", files)
        st.metric("总 chunk 数", chunks)

        if st.button("🔄 导入文件"):
            with st.spinner("正在导入..."):
                result = asyncio.run(run_ingest(config))
            st.text(result)
            st.rerun()

        if st.button("🗑️ 清空数据"):
            if st.checkbox("确认清空所有数据？"):
                clean_data(config.data.root)
                st.success("数据已清空")
                st.rerun()

    # ===== 主区域：问答 =====
    st.title("📖 知识库问答")
    query = st.text_input("输入问题", placeholder="请输入你的问题...")

    if query:
        config.llm.model = model
        config.llm.temperature = temperature
        config.llm.max_chars = max_chars
        config.llm.stream = stream
        config.query_pipeline.vector_weight = vector_weight
        config.query_pipeline.vector_top_k = vector_top_k
        config.query_pipeline.bm25_top_k = bm25_top_k
        config.query_pipeline.final_top_k = final_top_k
        config.stitcher.enabled = stitcher_enabled
        config.stitcher.dedup = stitcher_dedup

        pipeline = get_pipeline(config)

        with st.spinner("正在查询..."):
            if stream:
                st.write_stream(stream_response(pipeline, query, stream))
            else:
                result = asyncio.run(
                    anext(stream_response(pipeline, query, stream))
                )
                st.markdown(result)


if __name__ == "__main__":
    main()