"""
最简化测试 - 仅验证数据库加载
"""
import os
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

print("开始测试...")

from dotenv import load_dotenv
load_dotenv()

print("1. 加载 Embedding...")
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-base-en-v1.5")
print("✓ Embedding 加载成功")

print("\n2. 加载向量数据库...")
import chromadb
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.core import VectorStoreIndex

vector_db_path = "./src/db/canteen_db_vectordb"
collection_name = "ncwu_canteen_collection"

client = chromadb.PersistentClient(path=vector_db_path)
collection = client.get_or_create_collection(collection_name)
vector_store = ChromaVectorStore(chroma_collection=collection)
vector_index = VectorStoreIndex.from_vector_store(vector_store, embed_model=embed_model)
print("✓ 向量数据库加载成功")

print("\n3. 测试检索...")
retriever = vector_index.as_retriever(similarity_top_k=3)
nodes = retriever.retrieve("龙子湖校区有几个食堂？")
print(f"✓ 检索到 {len(nodes)} 个相关文档")

for i, node in enumerate(nodes, 1):
    print(f"\n文档 {i} (相似度: {node.score:.4f}):")
    print(node.text[:200] + "...")

print("\n✅ 数据库工作正常！")

