"""
快速查看数据库文档数量
"""
import chromadb

client = chromadb.PersistentClient(path="./src/db/canteen_db_vectordb")
collection = client.get_collection("ncwu_canteen_collection")

# 获取所有ID
results = collection.get()
print(f"总文档数: {len(results['ids'])}")

# 获取前10个文档看看
sample = collection.get(limit=10, include=["documents"])
for i, doc in enumerate(sample['documents']):
    print(f"\n=== 文档 {i+1} ===")
    lines = doc.split('\n')[:5]  # 只看前5行
    for line in lines:
        print(line)

