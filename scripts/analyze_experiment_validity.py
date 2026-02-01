"""
实验结果统计分析 - 评估 Phase 3 结果的统计显著性
"""
import json
import sys
import io
from pathlib import Path
import math

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 加载实验数据
data = json.loads(Path("results/phase3_baseline_vs_cr.json").read_text(encoding='utf-8'))

baseline = data["baseline"]
cr = data["cr_enhanced"]

print("="*80)
print("  Phase 3 实验结果统计分析 - 评估可靠性")
print("="*80)

# 1. 提取分数对
print("\n[1] 原始数据对比")
print("-"*80)
print(f"{'Query':<45} {'Baseline':>10} {'CR':>10} {'Diff':>10}")
print("-"*80)

diffs = []
for i, (b, c) in enumerate(zip(baseline, cr)):
    b_score = b.get("top_1_score", 0)
    c_score = c.get("top_1_score", 0)
    diff = c_score - b_score
    diffs.append(diff)
    
    query_short = b["query"][:40] + "..." if len(b["query"]) > 40 else b["query"]
    print(f"Q{i+1}: {query_short:<42} {b_score:>10.4f} {c_score:>10.4f} {diff:>+10.4f}")

print("-"*80)

# 2. 描述性统计
print("\n[2] 描述性统计")
print("-"*40)
mean_diff = sum(diffs) / len(diffs)
variance = sum((d - mean_diff)**2 for d in diffs) / (len(diffs) - 1)
std_diff = math.sqrt(variance)
se = std_diff / math.sqrt(len(diffs))  # 标准误

print(f"样本量 n = {len(diffs)}")
print(f"平均差异 (CR - Baseline) = {mean_diff:+.6f}")
print(f"差异标准差 = {std_diff:.6f}")
print(f"标准误 (SE) = {se:.6f}")

# 3. 配对 t 检验 (手动计算，不依赖 scipy)
print("\n[3] 配对 t 检验 (Paired t-test)")
print("-"*40)
t_stat = mean_diff / se if se > 0 else 0
df = len(diffs) - 1

# t 分布临界值 (双尾 α=0.05, df=9)
# t_critical ≈ 2.262 for df=9, α=0.05 two-tailed
t_critical = 2.262

print(f"t 统计量 = {t_stat:.4f}")
print(f"自由度 df = {df}")
print(f"临界值 t_crit (α=0.05, 双尾) = {t_critical}")

if abs(t_stat) > t_critical:
    print(f"结论: |t| > t_crit, 差异显著 (p < 0.05)")
else:
    print(f"结论: |t| ≤ t_crit, 差异不显著 (p > 0.05)")

# 4. 效应量 (Cohen's d)
print("\n[4] 效应量 (Cohen's d)")
print("-"*40)
cohens_d = mean_diff / std_diff if std_diff > 0 else 0
print(f"Cohen's d = {cohens_d:.4f}")
if abs(cohens_d) < 0.2:
    effect_size = "可忽略 (negligible)"
elif abs(cohens_d) < 0.5:
    effect_size = "小 (small)"
elif abs(cohens_d) < 0.8:
    effect_size = "中等 (medium)"
else:
    effect_size = "大 (large)"
print(f"效应大小: {effect_size}")

# 5. 95% 置信区间
print("\n[5] 95% 置信区间")
print("-"*40)
ci_lower = mean_diff - t_critical * se
ci_upper = mean_diff + t_critical * se
print(f"差异的 95% CI: [{ci_lower:.6f}, {ci_upper:.6f}]")
if ci_lower > 0:
    print("置信区间不包含0, 可以认为 CR > Baseline")
elif ci_upper < 0:
    print("置信区间不包含0, 可以认为 CR < Baseline")
else:
    print("⚠️ 置信区间包含0, 无法排除 CR = Baseline 的可能")

# 6. 符号检验 (非参数)
print("\n[6] 符号检验 (Sign Test) - 非参数方法")
print("-"*40)
pos_count = sum(1 for d in diffs if d > 0)
neg_count = sum(1 for d in diffs if d < 0)
zero_count = sum(1 for d in diffs if d == 0)
print(f"CR > Baseline: {pos_count} 次")
print(f"CR < Baseline: {neg_count} 次")
print(f"CR = Baseline: {zero_count} 次")

# 二项分布检验 (在零假设下，p=0.5)
# P(X >= pos_count | n=pos_count+neg_count, p=0.5)
n_valid = pos_count + neg_count
if n_valid > 0:
    # 简化: 用正态近似
    expected = n_valid / 2
    print(f"期望值 (在 H0 下): {expected}")
    print(f"实际正数: {pos_count}")
    if pos_count == n_valid:
        print(f"⚠️ 所有差异都是正的，但样本量太小无法确定显著性")
    elif pos_count >= 0.8 * n_valid:
        print(f"趋势明显，但需要更大样本验证")

# 7. 问题分析
print("\n" + "="*80)
print("  实验设计分析")
print("="*80)

print("\n⚠️ 潜在问题:")
print("-"*40)
issues = [
    ("样本量太小", f"n={len(diffs)}, 统计功效不足", "建议至少 30+ 个测试问题"),
    ("评价指标单一", "只用了相似度得分", "应增加人工评估、MRR、NDCG 等"),
    ("测试问题设计", "问题直接包含实体名，区分度不足", "应增加需要歧义消解的问题"),
    ("缺乏重复实验", "只运行了 1 次", "应重复 3-5 次取平均"),
    ("嵌入模型一致性", "BGE 模型加载可能有随机性", "应固定随机种子"),
]

for issue, detail, suggestion in issues:
    print(f"\n📌 {issue}")
    print(f"   现状: {detail}")
    print(f"   建议: {suggestion}")

# 8. 仔细检查：两组是否返回了完全相同的结果
print("\n[7] 检查检索结果差异")
print("-"*40)
same_top1_count = 0
for i, (b, c) in enumerate(zip(baseline, cr)):
    # 比较原始文本（去掉 CR 的前缀）
    b_text = b["top_1_text"][:100]
    c_text = c["top_1_text"]
    # CR 文本可能有英文前缀，去掉后比较
    c_text_clean = c_text.split(".")[-1][:100] if "." in c_text[:80] else c_text[:100]
    
    if b_text.strip() == c_text_clean.strip():
        same_top1_count += 1
        
print(f"Top-1 结果完全相同: {same_top1_count}/{len(diffs)} ({same_top1_count/len(diffs)*100:.0f}%)")

if same_top1_count > len(diffs) * 0.5:
    print("⚠️ 超过一半的查询返回了相同内容，CR 的英文摘要没有改变检索排序")
    print("   这意味着 1.1% 的分数提升主要来自相同文档在不同数据库中的嵌入差异")

# 9. 最终结论
print("\n" + "="*80)
print("  综合结论")
print("="*80)
print(f"""
1. 统计显著性: {'达到' if abs(t_stat) > t_critical else '未达到'} (t={t_stat:.3f}, p {'<' if abs(t_stat) > t_critical else '>'} 0.05)
2. 效应量: {effect_size} (d={cohens_d:.3f})
3. 置信区间: [{ci_lower:.4f}, {ci_upper:.4f}] {'不' if ci_lower <= 0 <= ci_upper else ''}包含 0

🔍 解读:
- 当前实验的 1.1% 提升 {'具有统计显著性' if abs(t_stat) > t_critical else '不能排除随机误差'}
- 效应量{'' if abs(cohens_d) >= 0.2 else '过'}小，实际意义{'有限' if abs(cohens_d) < 0.5 else '明显'}
- 需要更多测试问题和重复实验来确认结论

📋 改进建议:
1. 增加测试问题至 30-50 个
2. 设计更多「需要上下文消歧」的问题（如"该水库的总库容"而不是"常庄水库的总库容"）
3. 重复实验 3 次，计算平均值和标准差
4. 增加人工评估（是否正确回答了问题）
""")
