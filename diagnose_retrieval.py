"""
诊断 CR v2 检索问题
"""
import os
from dotenv import load_dotenv
from llama_index.core import SimpleDirectoryReader, VectorStoreIndex, Settings
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.ollama import Ollama
import chromadb
from llama_index.vector_stores.chroma import ChromaVectorStore

load_dotenv()

print("="*80)
print("诊断 CR v2 检索问题")
print("="*80)

# 1. 读取 PDF 查看内容
print("\n[1/4] 读取 PDF 内容...")
docs = SimpleDirectoryReader("./data").load_data()
print(f"✓ 文档数: {len(docs)}")
print(f"✓ 总字符数: {sum(len(d.text) for d in docs)}")

# 检查关键内容
full_text = docs[0].text if docs else ""
print(f"✓ 包含'一号餐厅': {'一号餐厅' in full_text}")
print(f"✓ 包含'包子': {'包子' in full_text}")
print(f"✓ 包含'42号': {'42号' in full_text or '42' in full_text}")

# 显示前500字符
print(f"\n前500字符预览：")
print("-"*80)
print(full_text[:500])
print("-"*80)

# 2. 测试 Embedding 质量
print("\n[2/4] 测试 Embedding 质量...")

# 使用中文 Embedding 模型
embed_model_cn = HuggingFaceEmbedding(
    model_name="BAAI/bge-base-zh-v1.5"  # 中文模型
)

embed_model_en = HuggingFaceEmbedding(
    model_name="BAAI/bge-base-en-v1.5"  # 英文模型（当前使用）
)

query = "一号餐厅有哪些窗口"
text_sample = "Context: Canteen=1 | Window=42 | 一、香港九龙包（42号档口）"

# 计算相似度
query_emb_cn = embed_model_cn.get_query_embedding(query)
text_emb_cn = embed_model_cn.get_text_embedding(text_sample)
similarity_cn = sum(a*b for a,b in zip(query_emb_cn, text_emb_cn))

query_emb_en = embed_model_en.get_query_embedding(query)
text_emb_en = embed_model_en.get_text_embedding(text_sample)
similarity_en = sum(a*b for a,b in zip(query_emb_en, text_emb_en))

print(f"✓ 中文模型相似度: {similarity_cn:.4f}")
print(f"✓ 英文模型相似度: {similarity_en:.4f}")
print(f"✓ 差异: {abs(similarity_cn - similarity_en):.4f}")

if similarity_cn > similarity_en * 1.1:
    print("⚠️  中文模型显著更好！建议切换到中文 Embedding")

# 3. 测试当前数据库检索
print("\n[3/4] 测试当前数据库检索...")

vectordb_client = chromadb.PersistentClient(path="./src/db/canteen_db_vectordb")
chroma_collection = vectordb_client.get_or_create_collection("ncwu_canteen_collection")
vector_store = ChromaVectorStore(chroma_collection=chroma_collection)

# 使用当前的英文模型
Settings.embed_model = embed_model_en
vector_index = VectorStoreIndex.from_vector_store(vector_store, embed_model=embed_model_en)

# 测试检索
retriever = vector_index.as_retriever(similarity_top_k=5)
nodes = retriever.retrieve(query)

print(f"✓ 检索到 {len(nodes)} 个节点")
for i, node in enumerate(nodes, 1):
    print(f"\n节点 {i} (相似度: {node.score:.4f}):")
    print(f"内容: {node.text[:200]}...")

# 4. 测试不同的检索参数
print("\n[4/4] 测试不同的 top_k 参数...")

for k in [3, 5, 10]:
    retriever_k = vector_index.as_retriever(similarity_top_k=k)
    nodes_k = retriever_k.retrieve(query)

    # 检查是否包含相关内容
    has_relevant = any('一号' in node.text or '42' in node.text for node in nodes_k)
    print(f"top_k={k}: 检索到 {len(nodes_k)} 个节点, 包含相关内容: {has_relevant}")

print("\n" + "="*80)
print("诊断完成！")
print("="*80)

print("\n📊 建议：")
print("1. 如果中文模型相似度更高，切换到 bge-base-zh-v1.5")
print("2. 如果 top_k=10 能找到相关内容，增大检索数量")
print("3. 如果都找不到，可能是数据库创建时的问题")

