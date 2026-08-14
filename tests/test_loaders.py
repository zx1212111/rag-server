"""加载器单元测试（mock 文件读取和外部调用）。"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_markdown_loader():
    """Markdown 加载器应正确读取 .md 文件。"""
    with patch("builtins.open", MagicMock()) as mock_open:
        mock_file = MagicMock()
        mock_file.__enter__.return_value.read.return_value = "# 测试\n\n内容。"
        mock_open.return_value = mock_file

        from rag_server.loaders.markdown import MarkdownLoader
        loader = MarkdownLoader()
        output = await loader.load("/fake/test.md")

        assert output is not None
        assert "测试" in output.md_text
        assert "内容" in output.md_text


@pytest.mark.asyncio
async def test_image_loader():
    """图片加载器应生成描述文本。"""
    with patch("builtins.open", MagicMock()) as mock_open:
        mock_file = MagicMock()
        mock_file.__enter__.return_value.read.return_value = b"fake_image_data"
        mock_open.return_value = mock_file

        from rag_server.loaders.image import ImageLoader
        loader = ImageLoader(strategy="text_only")
        output = await loader.load("/fake/test.png")

        assert output is not None
        assert "![图片]" in output.md_text
        assert len(output.assets) > 0


@pytest.mark.asyncio
async def test_loader_extensions():
    """每个 Loader 类应声明支持的扩展名。"""
    from rag_server.loaders.pdf import PDFLoader
    assert PDFLoader.extensions == [".pdf"]

    from rag_server.loaders.markdown import MarkdownLoader
    assert MarkdownLoader.extensions == [".md"]

    from rag_server.loaders.image import ImageLoader
    assert ".png" in ImageLoader.extensions
    assert ".jpg" in ImageLoader.extensions

    from rag_server.loaders.word import WordLoader
    assert ".docx" in WordLoader.extensions

    from rag_server.loaders.audio import AudioLoader
    assert ".mp3" in AudioLoader.extensions

    from rag_server.loaders.video import VideoLoader
    assert ".mp4" in VideoLoader.extensions