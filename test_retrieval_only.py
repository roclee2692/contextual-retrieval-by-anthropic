"""
纯检索测试 - 不使用LLM，直接查看检索结果
用于诊断检索质量问题
"""
import os
import chromadb
from dotenv import load_dotenv
from llama_index.core import VectorStoreIndex
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.retrievers.bm25 import BM25Retriever
from llama_index.core import Settings
import jieba

load_dotenv()

# 中文分词器
def chinese_tokenizer(text):
    """增强型中文分词器"""
    tokens = list(jieba.cut_for_search(text))
    enhanced_tokens = []
    for token in tokens:
        enhanced_tokens.append(token)
        if '包' in token:
            enhanced_tokens.append('包')
            enhanced_tokens.append('包子')
    return enhanced_tokens

print("=" * 80)
print("🔍 纯检索测试（无LLM）")
print("=" * 80)

# 加载配置
vector_db_path = "./src/db/canteen_db_vectordb"
bm25_db_path = "./src/db/canteen_db_bm25"
collection_name = "ncwu_canteen_collection"

# 初始化 Embedding - 使用中文模型
print("\n1. 加载 Embedding 模型...")
embed_model = HuggingFaceEmbedding(
    model_name="BAAI/bge-small-zh-v1.5",  # 中文模型
    device="cpu"
)
Settings.embed_model = embed_model
print("✓ 完成")

# 加载向量数据库
print("\n2. 加载向量数据库...")
vectordb_client = chromadb.PersistentClient(path=vector_db_path)
chroma_collection = vectordb_client.get_or_create_collection(collection_name)
vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
vector_index = VectorStoreIndex.from_vector_store(vector_store, embed_model=embed_model)
print("✓ 完成")

# 加载 BM25
print("\n3. 加载 BM25 数据库...")
bm25_retriever = BM25Retriever.from_persist_dir(bm25_db_path)
print("✓ 完成")

# 测试问题
test_questions = [
    "一号餐厅有哪些窗口或档口？",
    "二号餐厅一楼有哪些档口？",
    "哪些窗口提供包子类食品？",
    "天津包子在哪个窗口？",
    "香港九龙包多少钱？",
]

print("\n" + "=" * 80)
print("开始检索测试")
print("=" * 80)

for i, query in enumerate(test_questions, 1):
    print(f"\n{'='*80}")
    print(f"问题 {i}: {query}")
    print('='*80)

    # 向量检索
    print("\n【向量检索】(Top 5)")
    print("-" * 80)
    vector_retriever = vector_index.as_retriever(similarity_top_k=5)
    vector_nodes = vector_retriever.retrieve(query)

    for j, node in enumerate(vector_nodes, 1):
        score = node.score if hasattr(node, 'score') else 0.0
        print(f"\n结果 {j} (相似度: {score:.4f})")
        print(f"内容: {node.text[:200]}...")

    # BM25检索
    print(f"\n\n【BM25检索】(Top 5)")
    print("-" * 80)
    bm25_retriever.similarity_top_k = 5
    bm25_nodes = bm25_retriever.retrieve(query)

    for j, node in enumerate(bm25_nodes, 1):
        score = node.score if hasattr(node, 'score') else 0.0
        print(f"\n结果 {j} (BM25分数: {score:.4f})")
        print(f"内容: {node.text[:200]}...")

    # 混合结果
    print(f"\n\n【混合去重后】")
    print("-" * 80)
    all_nodes = list({n.node.node_id: n for n in (vector_nodes + bm25_nodes)}.values())
    print(f"向量检索: {len(vector_nodes)} 个结果")
    print(f"BM25检索: {len(bm25_nodes)} 个结果")
    print(f"去重后: {len(all_nodes)} 个唯一结果")

print("\n" + "=" * 80)
print("检索测试完成")
print("=" * 80)

print("\n💡 分析建议:")
print("-" * 80)
print("1. 检查向量检索的相似度分数是否合理（0-1之间）")
print("2. 检查BM25分数是否为0（如果是0说明有问题）")
print("3. 检查检索到的内容是否与问题相关")
print("4. 如果BM25全是0，需要重建BM25索引")
print("5. 如果内容不相关，可能需要调整chunk_size或使用中文embedding")

