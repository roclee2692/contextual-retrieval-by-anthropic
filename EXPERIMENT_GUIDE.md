# 实验运行指南 | Experiment Execution Guide

本项目包含 **两个阶段、共 5 组实验**，分别针对不同数据形态验证 RAG 技术效果。

---

## 📋 实验总览

### Phase 1: 结构化列表数据（食堂菜单）
- **Exp 1**: Baseline RAG  
- **Exp 2**: Contextual Retrieval (CR)  
- **Exp 3**: Jieba + Simple KG  

### Phase 2: 非结构化领域数据（防洪预案）
- **Exp 4**: Baseline (Flood) - 纯 RAG 无 CR
- **Exp 5**: CR (Flood) - 带上下文的 RAG
- **Exp 6**: Deep Knowledge Graph - 知识图谱推理  

---

## 🚀 方法 1: 一键运行（推荐）

使用项目根目录的 `run_experiment.py` 统一脚本：

### 运行 Phase 1（食堂实验）
```bash
# 完整流程：切换配置 + 构建数据库 + 运行测试
python run_experiment.py canteen --build --test

# 仅运行测试（需已构建数据库）
python run_experiment.py canteen --test
```

### 运行 Phase 2（防洪实验）
```bash
# Exp 4 & 5: 运行 Baseline vs CR 对比测试
python run_experiment.py flood --test

# Exp 6: 构建知识图谱（独立脚本，耗时约 30-40 分钟）
python scripts/create_knowledge_graph.py
python scripts/test_kg_retrieval.py
```

> **注意**: `run_flood_comparison.py` 会自动对比 Baseline 和 CR 两种方法，无需单独运行 Baseline。

---

## 🔧 方法 2: 手动分步执行

### Step 1: 切换实验配置

**Windows PowerShell**:
```powershell
# 食堂实验
Copy-Item .env.canteen .env

# 防洪实验
Copy-Item .env.flood .env
```

**Linux/macOS**:
```bash
# 食堂实验
cp .env.canteen .env

# 防洪实验
cp .env.flood .env
```

### Step 2: 构建数据库

```bash
# 通用构建脚本（根据 .env 自动适配）
python scripts/create_save_db.py
```

**注意**：
- 食堂实验约需 10-15 分钟（如启用 CR，需调用 LLM）
- 防洪实验约需 20-30 分钟
- 脚本包含缓存机制，中断后可断点续传

### Step 3: 运行测试

**Phase 1 测试**:
```bash
python scripts/test_ab_simple.py
```
- 输出: `results/report_experiment_X.txt`
- 包含 20 个预设问题的回答和性能统计

**Phase 2 测试**:
```bash
# 对比测试（CR vs Baseline）
python scripts/run_flood_comparison.py

# 知识图谱测试
python scripts/test_kg_retrieval.py
```

---

## 📊 结果查看

### Phase 1 结果
```bash
# 查看对比表格
cat results/summary_table.csv

# 查看详细案例分析
cat results/cases.md
```

### Phase 2 结果
```bash
# 查看防洪实验对比报告
cat results/flood_comparison_report.md

# 查看知识图谱检索结果
cat results/flood_retrieval_report.json
```

---

## ⚙️ 配置说明

### `.env.canteen` (Phase 1)
```ini
DATA_DIR="./data"                              # 食堂菜单 PDF 所在目录
DB_NAME="canteen_db"                           # 数据库前缀
VECTOR_DB_PATH="./src/db/canteen_db_vectordb" # 向量库路径
BM25_DB_PATH="./src/db/canteen_db_bm25"       # BM25 索引路径
```

### `.env.flood` (Phase 2)
```ini
DATA_DIR="./data/防洪预案_txt"                 # 防洪文本文件目录
DB_NAME="flood_prevention_db"                  # 数据库前缀
VECTOR_DB_PATH="./src/db/flood_prevention_db_vectordb"
BM25_DB_PATH="./src/db/flood_prevention_db_bm25"
```

---

## 🔍 常见问题

**Q: 如何知道当前使用的是哪个实验配置？**  
A: 查看项目根目录的 `.env` 文件头部注释。

**Q: 可以同时运行两个实验吗？**  
A: 不推荐。虽然数据库路径不同，但环境变量是全局的。请切换配置后再运行。

**Q: 构建数据库时中断了怎么办？**  
A: `create_save_db.py` 包含缓存机制（`context_cache.json`），重新运行会从断点继续。

**Q: 如何清空数据库重新构建？**  
A: 删除对应的数据库文件夹：
```bash
rm -rf src/db/canteen_db_*        # 清空食堂数据库
rm -rf src/db/flood_prevention_*  # 清空防洪数据库
```

---

## 📞 需要帮助？

遇到问题请提交 [Issue](https://github.com/roclee2692/contextual-retrieval-by-anthropic/issues)。
