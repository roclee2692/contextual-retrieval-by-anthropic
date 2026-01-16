"""
诊断：数据库里到底有没有'包子'？
"""
from llama_index.core import SimpleDirectoryReader
from llama_index.core.node_parser import SentenceSplitter
import jieba

print("="*80)
print("诊断：查找'包子'在数据中的位置")
print("="*80)

# 1. 读取 PDF
docs = SimpleDirectoryReader("./data").load_data()
print(f"\n[1] PDF 文档数: {len(docs)}")

# 检查原始文档
full_text = "\n".join([d.text for d in docs])
print(f"[2] 总字符数: {len(full_text)}")

# 搜索关键词
keywords = ["包子", "九龙包", "天津包子", "梅菜扣肉包", "鲜肉包"]
print(f"\n[3] 搜索关键词:")
for kw in keywords:
    count = full_text.count(kw)
    print(f"  '{kw}': {count} 次")
    if count > 0:
        # 找到第一个出现位置
        idx = full_text.find(kw)
        context = full_text[max(0, idx-50):idx+100]
        print(f"    示例: ...{context}...")

# 分块后
splitter = SentenceSplitter(chunk_size=512, chunk_overlap=50)
nodes = splitter.get_nodes_from_documents(docs)
print(f"\n[4] 分块后节点数: {len(nodes)}")

# 找包含'包子'的节点
baozi_nodes = []
for i, node in enumerate(nodes):
    if any(kw in node.text for kw in keywords):
        baozi_nodes.append((i, node))

print(f"[5] 包含关键词的节点数: {len(baozi_nodes)}")

if baozi_nodes:
    print(f"\n[6] 示例节点（前3个）:")
    for i, (idx, node) in enumerate(baozi_nodes[:3], 1):
        print(f"\n  节点 #{idx}:")
        print(f"    内容: {node.text[:200]}...")

        # 分词测试
        tokens = list(jieba.cut(node.text[:100]))
        print(f"    分词（前100字符）: {tokens[:20]}")
else:
    print("⚠️  没有找到包含关键词的节点！")

print("\n" + "="*80)

