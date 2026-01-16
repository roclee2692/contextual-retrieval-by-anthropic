"""
专门诊断"包子"检索问题
"""
import chromadb
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core import VectorStoreIndex, Settings
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.retrievers.bm25 import BM25Retriever

print("="*80)
print("诊断：为什么找不到'包子'？")
print("="*80)

# 初始化
embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-base-en-v1.5")
Settings.embed_model = embed_model

# 加载向量数据库
vectordb_client = chromadb.PersistentClient(path="./src/db/canteen_db_vectordb")
chroma_collection = vectordb_client.get_or_create_collection("ncwu_canteen_collection")
vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
vector_index = VectorStoreIndex.from_vector_store(vector_store, embed_model=embed_model)

# 加载 BM25
bm25_retriever = BM25Retriever.from_persist_dir("./src/db/canteen_db_bm25")

query = "哪些窗口提供包子类食品？"

print(f"\n[测试1] 向量检索 - top_k=5")
print("-"*80)
vector_retriever = vector_index.as_retriever(similarity_top_k=5)
nodes = vector_retriever.retrieve(query)
for i, node in enumerate(nodes, 1):
    has_baozi = '包子' in node.text or '包' in node.text
    print(f"\n节点 {i} (相似度: {node.score:.4f}) [包含'包子': {has_baozi}]")
    print(f"内容片段: {node.text[:150]}...")

print(f"\n[测试2] 向量检索 - top_k=10")
print("-"*80)
vector_retriever_10 = vector_index.as_retriever(similarity_top_k=10)
nodes_10 = vector_retriever_10.retrieve(query)
baozi_nodes = [n for n in nodes_10 if '包子' in n.text or '香港九龙包' in n.text or '天津包子' in n.text]
print(f"✓ 检索到 {len(nodes_10)} 个节点")
print(f"✓ 包含'包子'的节点: {len(baozi_nodes)} 个")
if baozi_nodes:
    print(f"✓ 最高相似度: {max(n.score for n in baozi_nodes):.4f}")
    print(f"✓ 排名: {[i+1 for i, n in enumerate(nodes_10) if '包子' in n.text or '香港九龙包' in n.text]}")

print(f"\n[测试3] BM25 检索")
print("-"*80)
bm25_nodes = bm25_retriever.retrieve(query)
baozi_bm25 = [n for n in bm25_nodes if '包子' in n.text]
print(f"✓ BM25 检索到 {len(bm25_nodes)} 个节点")
print(f"✓ 包含'包子'的节点: {len(baozi_bm25)} 个")
if baozi_bm25:
    print(f"\n第一个包子节点内容:")
    print(baozi_bm25[0].text[:200])

print(f"\n[测试4] 关键词搜索")
print("-"*80)
all_docs = chroma_collection.get()
texts = all_docs['documents']
baozi_docs = [t for t in texts if '包子' in t or '香港九龙包' in t or '天津包子' in t]
print(f"✓ 数据库总文档数: {len(texts)}")
print(f"✓ 包含'包子'的文档数: {len(baozi_docs)}")
if baozi_docs:
    print(f"\n示例文档:")
    print(baozi_docs[0][:300])

print("\n" + "="*80)
print("诊断结论")
print("="*80)

if len(baozi_docs) == 0:
    print("❌ 数据库中没有'包子'相关文档！数据缺失！")
elif len(baozi_nodes) == 0:
    print("⚠️  数据库有'包子'，但 top_k=5 找不到！需要增加 top_k 或优化 Embedding")
else:
    print("✅ 数据库有'包子'，可以检索到")
    print(f"   - 建议 top_k >= {min([i+1 for i, n in enumerate(nodes_10) if '包子' in n.text])}")

