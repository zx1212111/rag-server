"""入口分发模块。

无参数 → MCP Server 模式（stdio）
子命令 → CLI 模式
"""

import asyncio
import sys


def main():
    """主入口。"""
    if len(sys.argv) > 1: 
        # CLI 模式
        from rag_server.interfaces.cli import cli_main
        cli_main()
    else:
        # MCP Server 模式
        from rag_server.interfaces.mcp import mcp_main
        asyncio.run(mcp_main())


if __name__ == "__main__":
    main()