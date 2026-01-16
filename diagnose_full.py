"""
完整诊断：检查数据库、分词器和检索质量
"""
import chromadb
import jieba
from llama_index.retrievers.bm25 import BM25Retriever

print("=" * 80)
print("🔍 完整系统诊断")
print("=" * 80)

# 1. 检查向量数据库
print("\n【1】检查向量数据库")
print("-" * 80)
try:
    client = chromadb.PersistentClient(path="./src/db/canteen_db_vectordb")
    collection = client.get_collection("ncwu_canteen_collection")
    
    results = collection.get()
    total_docs = len(results['ids'])
    print(f"✓ 总文档数: {total_docs}")
    
    # 检查前3个完整文档
    sample = collection.get(limit=3, include=["documents", "metadatas"])
    for i, (doc, meta) in enumerate(zip(sample['documents'], sample['metadatas'])):
        print(f"\n--- 文档 {i+1} ---")
        print(f"长度: {len(doc)} 字符")
        print(f"Metadata: {meta}")
        print(f"前200字符:")
        print(doc[:200])
        
except Exception as e:
    print(f"✗ 向量数据库错误: {e}")

# 2. 检查BM25数据库
print("\n\n【2】检查BM25数据库")
print("-" * 80)
try:
    bm25_retriever = BM25Retriever.from_persist_dir("./src/db/canteen_db_bm25")
    print(f"✓ BM25加载成功")
    
    # 测试检索
    test_query = "包子"
    results = bm25_retriever.retrieve(test_query)
    print(f"\n查询 '{test_query}' 返回 {len(results)} 个结果")
    
    for i, node in enumerate(results[:3]):
        print(f"\n--- BM25结果 {i+1} (分数: {node.score:.4f}) ---")
        print(node.text[:150])
        
except Exception as e:
    print(f"✗ BM25数据库错误: {e}")

# 3. 测试分词器
print("\n\n【3】测试分词器")
print("-" * 80)

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

test_cases = [
    "哪些窗口提供包子类食品？",
    "天津包子",
    "香港九龙包",
    "梅菜扣肉包",
    "鲜肉包子"
]

for text in test_cases:
    tokens = chinese_tokenizer(text)
    print(f"'{text}' → {tokens}")

# 4. 检查关键词覆盖
print("\n\n【4】检查数据库中的关键实体")
print("-" * 80)

keywords_to_check = [
    "一号餐厅", "二号餐厅", "民族餐厅",
    "包子", "天津包子", "香港九龙包",
    "窗口", "档口", "42号", "21号"
]

for keyword in keywords_to_check:
    # 在文档中搜索
    found_count = 0
    for doc in sample['documents']:
        if keyword in doc:
            found_count += 1
    
    status = "✓" if found_count > 0 else "✗"
    print(f"{status} '{keyword}': 出现在 {found_count} 个样本文档中")

print("\n\n【5】推荐操作")
print("-" * 80)

# 检查PDF文件
import os
pdf_path = "./data/"
if os.path.exists(pdf_path):
    pdfs = [f for f in os.listdir(pdf_path) if f.endswith('.pdf')]
    print(f"当前PDF文件: {pdfs}")
    
    if len(pdfs) > 1:
        print("\n⚠️  警告: 检测到多个PDF文件！")
        print("   建议: 只保留一个PDF（CR_Prefixed_v2.pdf）")
    elif len(pdfs) == 1:
        print(f"\n✓ 只有一个PDF: {pdfs[0]}")
    else:
        print("\n✗ 错误: 没有找到PDF文件！")
else:
    print("✗ data/ 目录不存在")

# 检查文档质量
if total_docs < 50:
    print("\n⚠️  警告: 文档数量太少！")
    print(f"   当前: {total_docs} 个，建议 > 100")
    print("   操作: 重新运行 'python create_save_db.py'")

print("\n" + "=" * 80)
print("诊断完成")
print("=" * 80)

