
import os

new_phase2 = '''## 🆕 Phase 2: 防洪预案三组对比实验(新增)

在 Phase 1 的基础上,我们在 **防洪应急预案** 垂直领域数据上进行了完整的三组对比实验。
*详细对比报告见 `results/phase2_complete_comparison.md`*

### 实验设计
| 实验 | 说明 | 脚本 |
|---|---|---|
| **Exp 4: Baseline** | 纯向量+BM25检索(无CR) | `scripts/phase2_three_way_comparison.py` |
| **Exp 5: CR Enhanced** | 带上下文增强的检索 | `scripts/phase2_three_way_comparison.py` |
| **Exp 6: Deep KG** | 知识图谱推理检索 | `scripts/create_knowledge_graph.py` + `scripts/phase2_three_way_comparison.py` |

### 性能与准确率对比 (2026/01/24 科学修正版)

**重要更新**: 在修正了实验对照组的公平性（Baseline 与 CR 均采用相同的 ChromaDB 持久化结构与 Jieba 分词参数）后，我们得到了新的结论：

| 指标 | Baseline | CR增强 | Knowledge Graph |
|------|----------|--------|----------------|
| **平均检索得分** | **0.493** | **0.495** | 1000.0* |
| **结论** | **基准稳健** | **无显著差异** | **不可用** |

*\*KG得分=1000.0为框架默认高分，实际内容相关性低*

### 🔍 核心发现：在结构化公文中 CR 失效

#### 1. CR 与 Baseline 形成“平局”
- **数据**: 0.493 vs 0.495 (差距 0.4%)
- **原因**: 《防洪预案》本身具备极强的结构性（章节、条款、编号）。相比于 Phase 1 的碎片化菜单数据，原始文档已经提供了足够的上下文。LLM 生成的额外 Context（如“本段落描述了...”）反而成为了信息噪声。

#### 2. 中文分词 (Tokenization) 的隐形瓶颈
- 我们假设 CR 失效是因为 Jieba 分词在 BM25 中缺失，但在强制注入 Jieba 分词参数后，两者得分依然持平。
- 这表明，对于**高度自包含的公文文档**，检索性能的瓶颈不在于上下文缺失，而在于语义匹配的精度。向量检索已经做得足够好，CR 无法在此基础上提供边际增益。

#### 3. Knowledge Graph 的虚假繁荣
- KG 组虽然得分高（1000），但检索结果多为“目录”或“标题”，缺乏实质内容。这证明了在没有特定 Schema 约束的情况下，通用的知识图谱抽取方案在垂直领域完全不可用。

### 🏆 综合排名（阶段二）

1. 🥇 **Baseline (并列)** - 简单、快速、稳健
2. 🥇 **CR增强 (并列)** - 成本更高，但效果无差异
3. 🥉 **Knowledge Graph** - 慢且效果差

---
'''

with open('README_CN.md', 'r', encoding='utf-8') as f:
    content = f.read()

# Split by the section header to replace only Phase 2
# Note: The file might have multiple headers or slight variations
parts = content.split('## 🆕 Phase 2:')

if len(parts) >= 2:
    # Use the first split to get everything BEFORE Phase 2
    prefix = parts[0]
    
    # Use the last part to find the suffix (assuming the last occurrence is what we want, or the first?)
    # ReadFile showed two "Phase 2" headers. We want to replace the whole block.
    # The block ends at "## 🔄"
    
    # Find the remainder after the first "Phase 2"
    remainder = "## 🆕 Phase 2:".join(parts[1:])
    
    # Split remainder by System Pipeline
    pipeline_parts = remainder.split('## 🔄 系统流程图')
    
    if len(pipeline_parts) >= 2:
        suffix = '## 🔄 系统流程图' + pipeline_parts[-1] # Take the last part to be safe
        
        final_content = prefix + new_phase2 + suffix
        with open('README_CN.md', 'w', encoding='utf-8') as f:
            f.write(final_content)
        print('Successfully updated README_CN.md')
    else:
        print('Could not find System Pipeline header')
else:
    print('Could not find Phase 2 header')
