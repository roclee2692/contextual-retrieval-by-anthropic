# 项目实施路线图

## 🎯 三个独立的实验方向

### 实验 1: 普通 RAG Baseline（最简单，先做这个）
**目标**: 测试基础向量检索效果

**使用文件**: 
- ✅ `NCWU_Longzihu_Canteens_RAG_Chunked.pdf`（只放这一个）

**特点**:
- 纯文本分块，无上下文增强
- 快速构建（5-10分钟）
- 作为性能基准

**步骤**:
```powershell
# 1. 只保留 RAG-chunked PDF
Remove-Item ./data/NCWU_Longzihu_Canteens_CR_Prefixed.pdf

# 2. 创建数据库
python create_save_db.py

# 3. 运行 A/B 测试
python test_ab_simple.py 3
# A = 纯向量检索
# B = 混合检索（向量 + BM25）
```

---

### 实验 2: Contextual Retrieval（中等难度）
**目标**: 测试上下文增强的效果

**使用文件**:
- ✅ `NCWU_Longzihu_Canteens_CR_Prefixed.pdf`（只放这一个）

**特点**:
- 每个文本块前添加了上下文信息
- 构建时间稍长（10-15分钟）
- 提高检索准确率

**步骤**:
```powershell
# 1. 删除旧数据库
Remove-Item -Recurse ./src/db/canteen_db_*

# 2. 只保留 CR-prefixed PDF
Remove-Item ./data/NCWU_Longzihu_Canteens_RAG_Chunked.pdf

# 3. 重新创建数据库
python create_save_db.py

# 4. 运行 A/B 测试
python test_ab_simple.py 3
```

**对比**: 实验1 vs 实验2 → 看 CR 是否提升效果

---

### 实验 3: 知识图谱（高级，最后做）
**目标**: 测试结构化知识推理

**使用文件**:
- ✅ `NCWU_Longzihu_Canteens_RAG_Chunked.pdf`（推荐用 RAG-chunked，因为 KG 会自动提取结构）

**特点**:
- 自动提取实体和关系
- 支持多跳推理
- 构建慢（15-40分钟）

**步骤**:
```powershell
# 1. 使用 RAG-chunked PDF
# 2. 构建知识图谱
python create_knowledge_graph.py

# 3. 测试图谱查询
python create_knowledge_graph.py test
```

**对比**: 实验1/2 vs 实验3 → 看 KG 在关系查询上的优势

---

## 📊 完整实验对比表

| 实验 | PDF 文件 | A 方法 | B 方法 | 目的 |
|------|----------|--------|--------|------|
| **实验1** | RAG-chunked | 纯向量检索 | 向量+BM25 | 建立基准 |
| **实验2** | CR-prefixed | 纯向量检索 | 向量+BM25 | 测试 CR 效果 |
| **实验3** | RAG-chunked | 知识图谱 | 混合检索 | 测试结构化推理 |

---

## 🎯 推荐的执行顺序

### 阶段 1: 基础测试（今天完成）
```powershell
# Step 1: 准备数据
cd D:\DpanPython\python-projects\contextual-retrieval-by-anthropic\data
# 只保留 NCWU_Longzihu_Canteens_RAG_Chunked.pdf

# Step 2: 创建数据库
cd ..
python create_save_db.py

# Step 3: 运行测试
python test_ab_simple.py 3

# Step 4: 查看结果
notepad ab_test_report_*.txt
```

### 阶段 2: CR 对比（明天）
```powershell
# Step 1: 清理旧数据库
Remove-Item -Recurse ./src/db/canteen_db_*

# Step 2: 替换 PDF 为 CR 版本
# 只保留 NCWU_Longzihu_Canteens_CR_Prefixed.pdf

# Step 3: 重新测试
python create_save_db.py
python test_ab_simple.py 3

# Step 4: 对比两次结果
```

### 阶段 3: 知识图谱（后天）
```powershell
# Step 1: 构建知识图谱
python create_knowledge_graph.py

# Step 2: 测试图谱查询
python create_knowledge_graph.py test

# Step 3: 可视化（可选）
python visualize_kg.py
```

---

## ⚠️ 重要提醒

### ✅ DO（推荐做法）
- **每次只放 1 个 PDF 文件**
- **每个实验独立进行**
- **保存每次测试结果**（文件名带日期）
- **先完成简单的，再做复杂的**

### ❌ DON'T（避免）
- ~~同时放两个 PDF~~（会混淆数据）
- ~~跳过基础测试直接做 KG~~（无法对比）
- ~~不删除旧数据库就重新创建~~（会累积错误）

---

## 📝 当前建议

**现在立即做**: 实验 1（基础 RAG）

```powershell
# 1. 检查数据文件
cd D:\DpanPython\python-projects\contextual-retrieval-by-anthropic\data
dir

# 2. 如果有两个 PDF，删除 CR 版本
Remove-Item NCWU_Longzihu_Canteens_CR_Prefixed.pdf

# 3. 只保留 RAG-chunked.pdf
# 4. 运行测试
cd ..
python test_ab_simple.py 3
```

这样你会得到：
- ✅ 基准性能数据
- ✅ A/B 对比结果
- ✅ 为后续实验建立参考标准

