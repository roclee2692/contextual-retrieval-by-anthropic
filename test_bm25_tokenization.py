"""
测试 BM25 分词问题
"""
import jieba

print("="*80)
print("测试 jieba 分词")
print("="*80)

# 添加自定义词
jieba.add_word("包子", freq=1000)
jieba.add_word("九龙包", freq=1000)
jieba.add_word("天津包子", freq=1000)

# 测试查询
query = "哪些窗口提供包子类食品？"
query_tokens = list(jieba.cut(query))
print(f"\n查询: {query}")
print(f"分词: {query_tokens}")
print(f"包含'包子': {'包子' in query_tokens}")
print(f"包含'包': {'包' in query_tokens}")

# 测试文档
docs = [
    "十、天津包子（21号）\n2元品类\n- 招牌鲜肉包、辣子鸡丁包",
    "一、香港九龙包（42号档口）\n- 鲜肉包：4元/笼",
    "梅菜扣肉包：4元/笼"
]

print(f"\n文档分词:")
for i, doc in enumerate(docs, 1):
    tokens = list(jieba.cut(doc))
    has_baozi = '包子' in tokens
    has_bao = '包' in tokens
    print(f"\n文档{i}: {doc[:30]}...")
    print(f"  分词: {tokens[:15]}")
    print(f"  包含'包子': {has_baozi}")
    print(f"  包含'包': {has_bao}")

    # 交集
    common = set(query_tokens) & set(tokens)
    print(f"  与查询的交集: {common}")

print("\n" + "="*80)
print("结论：")
print("- 如果文档里是'天津包子'，分词后是 ['天津', '包子']")
print("- 如果文档里是'九龙包'，分词后是 ['九龙', '包']")
print("- 查询'包子类食品'，分词后是 ['包子', '类', '食品']")
print("- '包子' 能匹配 '天津包子'，但不能匹配 '九龙包'！")
print("="*80)

