"""测试BM25分词器"""
import jieba

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

# 测试用例
test_cases = [
    "天津包子",
    "我爱我粥", 
    "包子类食品",
    "哪里有包子？",
    "麻辣烫"
]

print("=== BM25分词器测试 ===\n")
for text in test_cases:
    tokens = chinese_tokenizer(text)
    print(f"{text:15s} -> {tokens}")
