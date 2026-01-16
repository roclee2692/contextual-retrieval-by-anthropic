# 🔧 RAG系统修复计划

## 📋 当前问题诊断

### 🔴 关键问题
1. **BM25评分异常** - 所有相关性分数都是0.0000
2. **检索结果错误** - 查询"包子"返回"麻辣烫"和"拌面"
3. **增强检索表现差** - 5.5/10分，不如基准测试

### ⚠️ 可能原因
1. BM25索引构建问题
2. 向量模型维度不一致（512 vs 768）
3. 旧数据库残留导致冲突
4. 分词器在保存/加载时丢失

---

## 🎯 修复计划（分3阶段）

### 阶段1️⃣: 清理与验证（优先级：🔥 极高）

#### 任务1.1: 完全清理旧数据库
```powershell
# 删除所有数据库文件
Remove-Item -Recurse -Force ./src/db/canteen_db_bm25
Remove-Item -Recurse -Force ./src/db/canteen_db_vectordb
```

#### 任务1.2: 验证数据源
- [ ] 确认使用 `CR_Prefixed_v2.pdf`
- [ ] 检查PDF内容是否包含"包子"、"天津包子"等关键词
- [ ] 统计文档数量应为232个

#### 任务1.3: 检查依赖版本
```powershell
pip list | Select-String -Pattern "bm25|llama-index|jieba"
```
- [ ] bm25s: 0.2.14 ✓
- [ ] llama-index-retrievers-bm25: 0.6.5 ✓
- [ ] jieba: 最新版本

---

### 阶段2️⃣: 修复BM25构建（优先级：🔥 极高）

#### 任务2.1: 检查BM25保存逻辑
**文件**: `src/contextual_retrieval/save_bm25.py`

**需要验证的点**:
```python
# ✓ 分词器定义是否正确
def chinese_tokenizer(text):
    tokens = list(jieba.cut_for_search(text))
    enhanced_tokens = []
    for token in tokens:
        enhanced_tokens.append(token)
        if '包' in token:
            enhanced_tokens.append('包')
            enhanced_tokens.append('包子')
    return enhanced_tokens

# ✓ BM25创建参数
bm25_retriever = BM25Retriever.from_defaults(
    nodes=nodes,
    similarity_top_k=12,
    tokenizer=chinese_tokenizer,  # 确保传入
)

# ✓ 保存方法
bm25_retriever.persist(save_pth)
```

#### 任务2.2: 测试BM25分词效果
创建测试脚本 `test_bm25_tokenizer.py`:
```python
import jieba

def chinese_tokenizer(text):
    tokens = list(jieba.cut_for_search(text))
    enhanced_tokens = []
    for token in tokens:
        enhanced_tokens.append(token)
        if '包' in token:
            enhanced_tokens.append('包')
            enhanced_tokens.append('包子')
    return enhanced_tokens

# 测试用例
test_texts = [
    "天津包子",
    "我爱我粥",
    "包子类食品",
    "哪里有包子？"
]

for text in test_texts:
    tokens = chinese_tokenizer(text)
    print(f"'{text}' -> {tokens}")
```

#### 任务2.3: 修复BM25加载逻辑
**问题**: 加载时可能没有正确恢复分词器

**检查**: `test_ab_simple.py` 中的加载代码
```python
# 当前代码（可能有问题）
self.bm25_retriever = BM25Retriever.from_persist_dir(
    self.bm25_db_path
)

# 可能需要改为（待验证）
# 分词器可能需要在加载后重新设置？
```

---

### 阶段3️⃣: 统一向量模型（优先级：🔥 高）

#### 任务3.1: 确认向量模型配置
**文件**: `create_save_db.py` 或配置文件

**检查点**:
```python
# 确保使用一致的模型
embed_model = HuggingFaceEmbedding(
    model_name="BAAI/bge-small-zh-v1.5",  # 512维
    # 或
    # model_name="BAAI/bge-base-zh-v1.5",  # 768维
)
```

#### 任务3.2: 删除并重建向量数据库
```python
# 确保完全重建
import shutil
shutil.rmtree("./src/db/canteen_db_vectordb", ignore_errors=True)
shutil.rmtree("./src/db/canteen_db_bm25", ignore_errors=True)
```

---

### 阶段4️⃣: 重建与测试（优先级：🔥 极高）

#### 任务4.1: 重新创建数据库
```powershell
# 1. 删除旧数据库
Remove-Item -Recurse -Force ./src/db/canteen_db_bm25 -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force ./src/db/canteen_db_vectordb -ErrorAction SilentlyContinue

# 2. 重新创建
python create_save_db.py
```

#### 任务4.2: 验证BM25评分
创建 `verify_bm25_scores.py`:
```python
from llama_index.retrievers.bm25 import BM25Retriever
import jieba

# 定义分词器
def chinese_tokenizer(text):
    tokens = list(jieba.cut_for_search(text))
    enhanced_tokens = []
    for token in tokens:
        enhanced_tokens.append(token)
        if '包' in token:
            enhanced_tokens.append('包')
            enhanced_tokens.append('包子')
    return enhanced_tokens

# 加载BM25
bm25_retriever = BM25Retriever.from_persist_dir(
    "./src/db/canteen_db_bm25"
)

# 测试查询
test_queries = [
    "包子",
    "天津包子",
    "我爱我粥",
    "哪些窗口提供包子"
]

for query in test_queries:
    print(f"\n查询: {query}")
    results = bm25_retriever.retrieve(query)
    
    for i, node in enumerate(results[:3], 1):
        score = node.score if hasattr(node, 'score') else 'N/A'
        text_preview = node.text[:100]
        print(f"  {i}. 评分: {score:.4f} | 内容: {text_preview}...")
        
    # 检查评分是否都是0
    scores = [n.score for n in results if hasattr(n, 'score')]
    if all(s == 0.0 for s in scores):
        print("  ⚠️ 警告: 所有评分都是0.0000！")
```

#### 任务4.3: 运行完整测试
```powershell
# 运行A/B测试
python test_ab_simple.py
```

---

## 🔍 诊断检查清单

### 在重建数据库前
- [ ] 确认PDF文件路径正确
- [ ] 确认向量模型名称一致
- [ ] 确认分词器代码正确
- [ ] 删除所有旧数据库文件

### 在重建数据库后
- [ ] 检查文档数量（应为232）
- [ ] 验证BM25评分不全为0
- [ ] 测试"包子"查询返回正确结果
- [ ] 运行完整20问题测试

### 在测试完成后
- [ ] 对比新旧测试报告
- [ ] 记录性能指标
- [ ] 确认包子类查询是否修复

---

## 📊 预期结果

### 🎯 修复目标
1. **BM25评分正常**: 分数范围应在0.1-10.0之间
2. **包子类查询成功**: Q3, Q7, Q8, Q15 全部正确
3. **综合性能提升**: 增强检索分数从5.5 → 7.5+

### 📈 成功标准
| 指标 | 当前 | 目标 | 验证方法 |
|------|------|------|---------|
| BM25非零评分率 | 0% | 100% | verify_bm25_scores.py |
| 包子查询准确率 | 0% (0/4) | 100% (4/4) | test_ab_simple.py Q3,7,8,15 |
| 增强检索总评分 | 5.5/10 | ≥7.5/10 | 对比测试报告 |
| 平均响应时间 | 14.79s | <10s | test_ab_simple.py |

---

## 🚀 执行步骤（按顺序）

### Step 1: 立即执行（5分钟）
```powershell
# 1.1 创建BM25分词测试
python -c "
import jieba

def chinese_tokenizer(text):
    tokens = list(jieba.cut_for_search(text))
    enhanced_tokens = []
    for token in tokens:
        enhanced_tokens.append(token)
        if '包' in token:
            enhanced_tokens.append('包')
            enhanced_tokens.append('包子')
    return enhanced_tokens

test_cases = ['天津包子', '我爱我粥', '包子类食品']
for text in test_cases:
    print(f'{text} -> {chinese_tokenizer(text)}')
"

# 1.2 检查当前数据库大小
Get-ChildItem ./src/db/canteen_db_bm25 -Recurse | Measure-Object -Property Length -Sum
Get-ChildItem ./src/db/canteen_db_vectordb -Recurse | Measure-Object -Property Length -Sum
```

### Step 2: 清理重建（10分钟）
```powershell
# 2.1 完全删除旧数据库
Remove-Item -Recurse -Force ./src/db/canteen_db_bm25 -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force ./src/db/canteen_db_vectordb -ErrorAction SilentlyContinue

# 2.2 重新创建
python create_save_db.py

# 2.3 验证创建结果
python quick_check.py
```

### Step 3: 验证修复（15分钟）
```powershell
# 3.1 创建并运行BM25评分验证脚本（见任务4.2）
# 3.2 运行完整测试
python test_ab_simple.py

# 3.3 对比报告
# 比较新生成的报告与 ab_test_report_20260114_182109.txt
```

---

## 📝 后续优化（可选）

### 如果修复成功
1. 调整BM25权重参数
2. 优化混合检索比例
3. 增加缓存机制

### 如果仍有问题
1. 检查llama-index版本兼容性
2. 尝试不同的分词器策略
3. 考虑使用自定义BM25实现

---

## 🎯 下一步操作建议

**立即执行**: 
1. 运行 Step 1 诊断脚本，确认分词器工作正常
2. 备份当前数据库（如果需要回退）
3. 执行 Step 2 完全重建数据库
4. 运行 Step 3 验证修复效果

**等待反馈**:
- 告诉我 Step 1 的输出结果
- 我会根据结果调整后续步骤
