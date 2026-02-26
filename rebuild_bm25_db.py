#!/usr/bin/env python
"""重建BM25数据库"""
import os
import shutil
from pathlib import Path
from dotenv import load_dotenv
from llama_index.core import SimpleDirectoryReader
from llama_index.core.node_parser import SimpleNodeParser
from llama_index.retrievers.bm25 import BM25Retriever
import jieba

load_dotenv()

ROOT = Path(__file__).resolve().parents[0]
DATA_DIR = Path(os.getenv("DATA_DIR", ROOT / "data" / "防洪预案"))
BM25_DB_PATH = os.getenv("BM25_DB_PATH")

print("=" * 70)
print("重建BM25数据库")
print("=" * 70)
print(f"数据目录: {DATA_DIR}")
print(f"BM25数据库路径: {BM25_DB_PATH}")

# 清毒旧数据库
if Path(BM25_DB_PATH).exists():
    print(f"\n删除旧数据库: {BM25_DB_PATH}")
    shutil.rmtree(BM25_DB_PATH)

# 加载文档
print("\n加载文档...")
loader = SimpleDirectoryReader(str(DATA_DIR), recursive=True)
documents = loader.load_data()
print(f"已加载: {len(documents)} 个文档")

# 将documents转换为nodes
print("\n解析文档为节点...")
parser = SimpleNodeParser.from_defaults()
nodes = parser.get_nodes_from_documents(documents)
print(f"已生成: {len(nodes)} 个节点")

# 自定义中文分词函数
def chinese_tokenizer(text):
    """增强型中文分词器"""
    tokens = list(jieba.cut_for_search(text))
    return tokens

# 创建BM25索引
print("\n构建BM25索引...")
bm25_retriever = BM25Retriever.from_defaults(
    nodes=nodes,
    similarity_top_k=3,
    tokenizer=chinese_tokenizer
)

# 保存到磁盘
print(f"\n保存BM25索引到: {BM25_DB_PATH}")
bm25_retriever.persist(BM25_DB_PATH)

print("\n" + "=" * 70)
print("BM25数据库重建完成！")
print("=" * 70)
