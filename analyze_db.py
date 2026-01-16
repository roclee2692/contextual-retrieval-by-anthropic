"""
分析数据库中的文档内容
"""
import os
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

import chromadb
from collections import Counter
import re

print("="*80)
print("数据库内容分析")
print("="*80)

# 连接数据库
vector_db_path = "./src/db/canteen_db_vectordb"
collection_name = "ncwu_canteen_collection"

client = chromadb.PersistentClient(path=vector_db_path)
collection = client.get_collection(collection_name)

# 获取所有文档
results = collection.get(include=["documents", "metadatas"])

print(f"\n总文档数: {len(results['documents'])}")

# 分析餐厅分布
canteen_pattern = r'【(一号餐厅|二号餐厅|民族餐厅)】'
canteen_counter = Counter()

for doc in results['documents']:
    matches = re.findall(canteen_pattern, doc)
    for match in matches:
        canteen_counter[match] += 1

print("\n餐厅分布:")
for canteen, count in sorted(canteen_counter.items()):
    print(f"  {canteen}: {count} 个文档")

# 分析窗口分布
window_pattern = r'【窗口(\d+)】'
windows = []
for doc in results['documents']:
    matches = re.findall(window_pattern, doc)
    windows.extend(matches)

print(f"\n窗口数量统计:")
print(f"  一号餐厅窗口: {len([w for doc in results['documents'] if '一号餐厅' in doc])}")
print(f"  二号餐厅窗口: {len([w for doc in results['documents'] if '二号餐厅' in doc])}")

# 检查上下文格式
print("\n前5个文档示例:")
for i, doc in enumerate(results['documents'][:5]):
    print(f"\n--- 文档 {i+1} ---")
    # 只显示前200个字符
    print(doc[:200])
    print("...")

# 检查是否有民族餐厅
ethnic_docs = [doc for doc in results['documents'] if '民族' in doc]
print(f"\n包含'民族'的文档: {len(ethnic_docs)}")
if ethnic_docs:
    print("示例:")
    print(ethnic_docs[0][:300])

print("\n" + "="*80)
print("分析完成")
print("="*80)

