"""
验证测试问题集
"""
import sys
sys.path.insert(0, '.')

from test_ab_simple import TEST_QUESTIONS

print("="*80)
print("测试问题集验证")
print("="*80)

print(f"\n总问题数: {len(TEST_QUESTIONS)}")

print("\n问题分类统计：")
categories = {
    "实体查找": 0,
    "价格查询": 0,
    "窗口定位": 0,
    "菜品推荐": 0,
    "组合查询": 0,
    "对比查询": 0
}

# 简单分类（基于关键词）
for q in TEST_QUESTIONS:
    if "哪些窗口" in q or "有哪些" in q or "什么档口" in q:
        categories["实体查找"] += 1
    elif "元" in q and ("多少" in q or "价格" in q or "便宜" in q):
        categories["价格查询"] += 1
    elif "在哪" in q or "几号" in q:
        categories["窗口定位"] += 1
    elif "想" in q or "推荐" in q or "可以买到" in q:
        categories["菜品推荐"] += 1
    elif "都卖什么" in q or ("元" in q and "哪些" in q):
        categories["组合查询"] += 1
    elif "哪个更" in q or "对比" in q:
        categories["对比查询"] += 1

for cat, count in categories.items():
    if count > 0:
        print(f"  {cat}: {count} 个")

print("\n前 10 个问题预览：")
print("-"*80)
for i, q in enumerate(TEST_QUESTIONS[:10], 1):
    print(f"{i:2d}. {q}")

print("\n后 10 个问题预览：")
print("-"*80)
for i, q in enumerate(TEST_QUESTIONS[-10:], len(TEST_QUESTIONS)-9):
    print(f"{i:2d}. {q}")

print("\n" + "="*80)
print("✅ 问题集验证完成")
print("="*80)
print("\n运行测试：")
print("  python test_ab_simple.py 3    # 测试前3个问题")
print("  python test_ab_simple.py 10   # 测试前10个问题")
print("  python test_ab_simple.py      # 测试所有问题")

