#!/usr/bin/env python
"""重建向量数据库"""
import os
import shutil
from pathlib import Path
from dotenv import load_dotenv
from llama_index.core import SimpleDirectoryReader, VectorStoreIndex
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.core import StorageContext
import chromadb

load_dotenv()

ROOT = Path(__file__).resolve().parents[0]
DATA_DIR = Path(os.getenv("DATA_DIR", ROOT / "data" / "防洪预案"))
VECTOR_DB_PATH = os.getenv("VECTOR_DB_PATH")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "default")

print("=" * 70)
print("重建向量数据库")
print("=" * 70)
print(f"数据目录: {DATA_DIR}")
print(f"向量数据库路径: {VECTOR_DB_PATH}")
print(f"集合名: {COLLECTION_NAME}")

# 清毒旧数据库
if Path(VECTOR_DB_PATH).exists():
    print(f"\n删除旧数据库: {VECTOR_DB_PATH}")
    shutil.rmtree(VECTOR_DB_PATH)

# 加载文档
print("\n加载文档...")
loader = SimpleDirectoryReader(str(DATA_DIR), recursive=True)
documents = loader.load_data()
print(f"已加载: {len(documents)} 个文档")

# 初始化向量存储和索引
print("\n初始化向量数据库...")
embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-zh-v1.5", device="cpu")

# 创建 Chroma 客户端
client = chromadb.PersistentClient(path=VECTOR_DB_PATH)
collection = client.get_or_create_collection(COLLECTION_NAME)

# 创建向量存储
vector_store = ChromaVectorStore(chroma_collection=collection)
storage_context = StorageContext.from_defaults(vector_store=vector_store)

# 创建索引
print("构建索引...")
index = VectorStoreIndex.from_documents(
    documents,
    storage_context=storage_context,
    embed_model=embed_model,
    show_progress=True
)

print("\n" + "=" * 70)
print("向量数据库重建完成！")
print("=" * 70)
