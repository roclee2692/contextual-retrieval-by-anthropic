"""
快速重建 BM25 数据库（使用中文分词）
"""
import os
import sys
from llama_index.core import SimpleDirectoryReader
from llama_index.core.node_parser import SentenceSplitter
from llama_index.retrievers.bm25 import BM25Retriever
import jieba

print("="*80)
print("重建 BM25 数据库（中文分词版本）")
print("="*80)

# 1. 读取 PDF
print("\n[1/3] 读取 PDF...")
docs = SimpleDirectoryReader("./data").load_data()
print(f"✓ 读取了 {len(docs)} 个文档")

# 2. 分块
print("\n[2/3] 分块...")
splitter = SentenceSplitter(chunk_size=512, chunk_overlap=50)
nodes = splitter.get_nodes_from_documents(docs)
print(f"✓ 分成了 {len(nodes)} 个块")

# 3. 创建 BM25（使用增强型中文分词）
print("\n[3/3] 创建 BM25（使用增强型中文分词）...")

# 添加自定义词典
jieba.add_word("包子", freq=1000)
jieba.add_word("九龙包", freq=1000)
jieba.add_word("天津包子", freq=1000)
jieba.add_word("麻辣烫", freq=1000)
jieba.add_word("煎饼果子", freq=1000)

def chinese_tokenizer(text):
    """增强型中文分词器"""
    tokens = list(jieba.cut_for_search(text))

    # 扩展：只要包含'包'，就添加'包'和'包子'
    enhanced_tokens = []
    for token in tokens:
        enhanced_tokens.append(token)
        if '包' in token:
            enhanced_tokens.append('包')
            enhanced_tokens.append('包子')

    return enhanced_tokens

bm25_retriever = BM25Retriever.from_defaults(
    nodes=nodes,
    similarity_top_k=12,
    tokenizer=chinese_tokenizer,
)

# 保存
save_path = "./src/db/canteen_db_bm25"
os.makedirs(os.path.dirname(save_path), exist_ok=True)
bm25_retriever.persist(save_path)

print(f"✓ BM25 数据库已保存到: {save_path}")

# 4. 测试
print("\n[测试] 搜索'包子'...")
test_nodes = bm25_retriever.retrieve("包子")
print(f"✓ 检索到 {len(test_nodes)} 个节点")

has_baozi = False
for i, node in enumerate(test_nodes[:3], 1):
    contains = '包' in node.text or '包子' in node.text
    if contains:
        has_baozi = True
    print(f"\n节点 {i}: {node.text[:100]}...")
    print(f"  包含'包/包子': {contains}")

print("\n" + "="*80)
if has_baozi:
    print("✅ 成功！BM25 能检索到'包子'相关内容！")
else:
    print("⚠️  警告：仍然检索不到，需要进一步调试")
print("="*80)

