"""
简化版数据库创建脚本 - 不使用Contextual Retrieval
直接创建向量数据库和BM25数据库，无需Ollama
"""
from llama_index.core import SimpleDirectoryReader
from llama_index.core.node_parser import TokenTextSplitter
from src.contextual_retrieval.save_vectordb import save_chromadb
from src.contextual_retrieval.save_bm25 import save_BM25
import os
from dotenv import load_dotenv

load_dotenv()

# 配置
DATA_DIR = os.getenv("DATA_DIR", "./data")
SAVE_DIR = os.getenv("SAVE_DIR", "./src/db")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "ncwu_canteen_collection")
DB_NAME = "canteen_db"

CHUNK_SIZE = 512
CHUNK_OVERLAP = 20

print("="*80)
print("🚀 简化版数据库创建开始（无需Contextual Retrieval）")
print("="*80)
print(f"数据目录: {DATA_DIR}")
print(f"保存目录: {SAVE_DIR}")
print(f"集合名称: {COLLECTION_NAME}")
print(f"数据库名称: {DB_NAME}")
print("-"*80)

# 1. 读取文档
print("\n1️⃣ 读取PDF文档...")
reader = SimpleDirectoryReader(input_dir=DATA_DIR)
documents = reader.load_data()
print(f"✓ 读取了 {len(documents)} 个文档")

# 2. 分块
print("\n2️⃣ 文档分块...")
splitter = TokenTextSplitter(
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP,
    separator=" ",
)
nodes = splitter.get_nodes_from_documents(documents)
print(f"✓ 创建了 {len(nodes)} 个文本块")

# 3. 创建向量数据库
print("\n3️⃣ 创建向量数据库...")
vectordb_name = DB_NAME + "_vectordb"
save_chromadb(
    nodes=nodes,
    save_dir=SAVE_DIR,
    db_name=vectordb_name,
    collection_name=COLLECTION_NAME
)
print(f"✓ 向量数据库已保存到: {SAVE_DIR}/{vectordb_name}")

# 4. 创建BM25数据库
print("\n4️⃣ 创建BM25数据库...")
bm25db_name = DB_NAME + "_bm25"
save_BM25(
    nodes=nodes,
    save_dir=SAVE_DIR,
    db_name=bm25db_name
)
print(f"✓ BM25数据库已保存到: {SAVE_DIR}/{bm25db_name}")

# 5. 验证
print("\n5️⃣ 验证数据库文件...")
import os
vectordb_path = os.path.join(SAVE_DIR, vectordb_name)
bm25_path = os.path.join(SAVE_DIR, bm25db_name)

vectordb_exists = os.path.exists(vectordb_path)
bm25_exists = os.path.exists(bm25_path)

print(f"向量数据库: {'✓ 存在' if vectordb_exists else '✗ 不存在'}")
print(f"BM25数据库: {'✓ 存在' if bm25_exists else '✗ 不存在'}")

print("\n" + "="*80)
if vectordb_exists and bm25_exists:
    print("✅ 数据库创建成功！")
    print("\n下一步操作：")
    print("  1. 运行检索测试: python test_retrieval_only.py")
    print("  2. 运行A/B测试: python test_ab_simple.py 3")
else:
    print("❌ 数据库创建失败，请检查错误信息")
print("="*80)

