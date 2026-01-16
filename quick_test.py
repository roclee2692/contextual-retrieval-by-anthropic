"""
快速测试脚本 - 单个问题验证系统
"""
import os
import sys
from dotenv import load_dotenv

# 设置镜像加速
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

print("\n" + "="*80)
print("  龙子湖食堂 RAG 系统 - 快速验证测试")
print("="*80)

load_dotenv()

# 检查数据库
vector_db = os.getenv("VECTOR_DB_PATH", "./src/db/canteen_db_vectordb")
bm25_db = os.getenv("BM25_DB_PATH", "./src/db/canteen_db_bm25")

print("\n[1/4] 检查数据库...")
if not os.path.exists(vector_db):
    print(f"❌ 向量数据库不存在: {vector_db}")
    sys.exit(1)
if not os.path.exists(bm25_db):
    print(f"❌ BM25 数据库不存在: {bm25_db}")
    sys.exit(1)
print("✅ 数据库检查通过")

print("\n[2/4] 加载依赖...")
try:
    from llama_index.core import VectorStoreIndex, Settings
    from llama_index.embeddings.huggingface import HuggingFaceEmbedding
    from llama_index.vector_stores.chroma import ChromaVectorStore
    from llama_index.llms.ollama import Ollama
    import chromadb
    print("✅ 依赖加载成功")
except Exception as e:
    print(f"❌ 依赖加载失败: {e}")
    sys.exit(1)

print("\n[3/4] 初始化模型...")
try:
    # 初始化 LLM
    llm = Ollama(
        model="gemma3:12b",
        base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        request_timeout=120.0
    )
    print("✅ Ollama LLM 初始化成功")

    # 初始化 Embedding（可能需要下载）
    print("  正在加载 Embedding 模型（首次运行可能需要 1-2 分钟下载）...")
    # 使用与数据库创建时相同的模型
    embed_model = HuggingFaceEmbedding(
        model_name="BAAI/bge-base-en-v1.5"
    )
    print("✅ Embedding 模型加载成功")

    Settings.llm = llm
    Settings.embed_model = embed_model

except Exception as e:
    print(f"❌ 模型初始化失败: {e}")
    print("\n可能的原因:")
    print("  1. Ollama 服务未运行（请在 WSL 中运行 'ollama serve'）")
    print("  2. 网络问题导致模型下载失败")
    print("  3. 模型文件损坏")
    sys.exit(1)

print("\n[4/4] 加载数据库并测试查询...")
try:
    # 加载向量数据库
    collection_name = os.getenv("COLLECTION_NAME", "ncwu_canteen_collection")
    vectordb_client = chromadb.PersistentClient(path=vector_db)
    chroma_collection = vectordb_client.get_or_create_collection(collection_name)
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
    vector_index = VectorStoreIndex.from_vector_store(
        vector_store,
        embed_model=embed_model
    )
    print("✅ 向量数据库加载成功")

    # 测试查询
    test_query = "龙子湖校区有几个食堂？"
    print(f"\n测试问题: {test_query}")
    print("正在查询...")

    query_engine = vector_index.as_query_engine(similarity_top_k=3)
    response = query_engine.query(test_query)

    print("\n" + "="*80)
    print("查询结果:")
    print("="*80)
    print(str(response))
    print("="*80)

    print("\n✅ 系统运行正常！")
    print("\n下一步:")
    print("  - 运行完整测试: python test_ab_simple.py 3")
    print("  - 启动 API 服务: python app.py")
    print("  - 使用测试脚本: .\\run_test.ps1")

except Exception as e:
    print(f"❌ 测试失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

