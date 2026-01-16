"""
测试搜索引擎模式分词
"""
import jieba

print("="*80)
print("对比：精确模式 vs 搜索引擎模式")
print("="*80)

jieba.suggest_freq('包', True)
jieba.suggest_freq('包子', True)

texts = [
    "天津包子",
    "香港九龙包",
    "梅菜扣肉包",
    "哪些窗口提供包子类食品？"
]

for text in texts:
    precise = list(jieba.cut(text))
    search = list(jieba.cut_for_search(text))

    print(f"\n原文: {text}")
    print(f"  精确模式: {precise}")
    print(f"  搜索模式: {search}")
    print(f"  搜索模式包含'包子': {'包子' in search}")
    print(f"  搜索模式包含'包': {'包' in search}")

print("\n" + "="*80)

