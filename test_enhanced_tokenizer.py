"""
最终测试：增强型中文分词
"""
import jieba

def enhanced_chinese_tokenizer(text):
    """增强型中文分词"""
    tokens = list(jieba.cut_for_search(text))

    # 扩展：如果有'包'，也添加'包子'
    enhanced_tokens = []
    for token in tokens:
        enhanced_tokens.append(token)
        # 只要包含'包'字，就添加相关词
        if '包' in token:
            enhanced_tokens.append('包')
            enhanced_tokens.append('包子')

    return enhanced_tokens

print("="*80)
print("增强型分词测试")
print("="*80)

texts = [
    "天津包子",
    "香港九龙包",
    "梅菜扣肉包",
    "哪些窗口提供包子类食品？"
]

for text in texts:
    tokens = enhanced_chinese_tokenizer(text)
    print(f"\n原文: {text}")
    print(f"  分词: {tokens}")
    print(f"  包含'包子': {'包子' in tokens}")

#查询与文档的交集
query_tokens = set(enhanced_chinese_tokenizer("哪些窗口提供包子类食品？"))
print(f"\n查询tokens: {query_tokens}")

for text in texts[:3]:
    doc_tokens = set(enhanced_chinese_tokenizer(text))
    common = query_tokens & doc_tokens
    print(f"\n{text}")
    print(f"  交集: {common}")
    print(f"  能匹配: {len(common) > 0}")

print("\n" + "="*80)

