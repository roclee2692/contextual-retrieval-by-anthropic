"""验证BM25检索效果"""
from llama_index.retrievers.bm25 import BM25Retriever
import jieba
import bm25s

# 定义中文分词器（与创建时一致）
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

# 🔧 关键修复：替换bm25s.tokenize函数
original_tokenize = bm25s.tokenize

def patched_tokenize(text, *args, **kwargs):
    """使用我们的中文分词器"""
    if isinstance(text, str):
        return [chinese_tokenizer(text)]
    else:
        return [chinese_tokenizer(t) for t in text]

bm25s.tokenize = patched_tokenize

print("=== 加载BM25检索器 ===")
bm25_retriever = BM25Retriever.from_persist_dir(
    "./src/db/canteen_db_bm25"
)
print("✓ 已替换bm25s.tokenize为中文分词器")

print("\n=== 测试关键查询 ===\n")
test_queries = [
    "包子",
    "天津包子", 
    "我爱我粥",
    "哪些窗口提供包子"
]

for query in test_queries:
    print(f"查询: {query}")
    results = bm25_retriever.retrieve(query)
    
    for i, node in enumerate(results[:3], 1):
        score = node.score if hasattr(node, 'score') else 'N/A'
        text_preview = node.text[:80].replace('\n', ' ')
        print(f"  {i}. 评分: {score:8.4f} | {text_preview}...")
    
    # 检查是否所有评分都是0
    scores = [n.score for n in results if hasattr(n, 'score')]
    if all(s == 0.0 for s in scores):
        print("  ⚠️ 警告: 所有评分都是0.0000！")
    
    print()
