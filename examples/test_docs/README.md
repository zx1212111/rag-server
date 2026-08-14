# 测试案例

本目录包含用于测试导入管线的示例文档。
（可以用自己的文档替换）
## 文件列表

| 文件 | 格式 | 说明 |
|------|------|------|
| `高层民用建筑消防安全管理规定.pdf` | PDF | 消防管理法规，含标题和正文 |
| `浙江省房屋使用安全管理条例.docx` | Word | 房屋安全管理条例，含多级标题和分章结构 |

## 测试

# 将文件直接复制到 data/input/
cp tests/test_docs/* data/input/

# 导入
python -m rag_server ingest

# 验证
python -m rag_server stats

# 查询测试（方法1）
python -m rag_server query "高层民用建筑消防安全管理有哪些规定？"

# 查询测试（方法2-网页查询）
streamlit run rag_server/interfaces/web.py

# 清理数据
测试完成后清空知识库：
python -m rag_server clean
