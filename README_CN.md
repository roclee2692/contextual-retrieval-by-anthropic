# 结构化数据的上下文检索：可复现实验

**[English](README.md) | [简体中文](README_CN.md)**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Reproducible](https://img.shields.io/badge/reproducible-yes-green.svg)](https://github.com/roclee2692/contextual-retrieval-by-anthropic)

> **核心发现**：在同一数据集与评测脚本下,对比了 Baseline RAG、Contextual Retrieval(CR)、知识图谱三种方法,发现 **CR 在结构化列表数据上存在明显局限**。

---

## 🎯 这是什么

本项目基于中文数据集复现了 [Anthropic 的 Contextual Retrieval 论文](https://www.anthropic.com/news/contextual-retrieval)，通过三个对比实验验证其有效性：

| 实验 | 方法 | 核心技术 |
|------|------|---------|
| **实验一** | Baseline RAG | 向量检索(bge-small-zh) + BM25 |
| **实验二** | CR 增强 | LLM 生成上下文前缀 + 向量+BM25 |
| **实验三** | 结巴分词 + 知识图谱 | jieba 中文分词 + NetworkX 图谱 |

**测试数据集**：华北水利水电大学龙子湖校区食堂菜单（27万字，3个餐厅，80+档口，2000+菜品）

---

## 📊 主要结果

### 性能对比

| 指标 | 实验一(Baseline) | 实验二(CR) | 实验三(结巴+KG) |
|------|---------------|-----------|---------------|
| **平均响应时间** | 12.79秒 | 13.64秒 (+6.7%) | **10.13秒** ⚡ |
| **混合检索加速比** | 9.9% | 8.5% | **19.9%** |
| **价格类查询准确率** | 75% | **100%** ✅ | **100%** ✅ |
| **分类类查询准确率** | **100%** ✅ | 83% | 83% |
| **位置类查询准确率** | 75% | **75%** | 50% |

### 关键发现

#### ✅ CR 成功案例
- **Q8 天津包子位置查询**：实验一(0%) → 实验二(**100%**) 
  - CR 成功区分了"天津包子"和"香港九龙堡"的歧义

#### ❌ CR 失败案例
- **Q9 档口名称查询**：实验一(100%) → 实验二(**0%**)
  - 关键信息(档口名)在上下文生成时丢失

#### ⚡ 结巴分词效果
- 实验三混合检索加速：**19.9%**（对比实验一的9.9%）
- 最快单次响应：**2.73秒**（Q9）

---

## 🔍 核心发现

### 为什么 CR 在结构化数据上表现不佳？

**根本原因**：数据缺少**自然语言语境**

```
❌ 我们的数据（结构化列表）：
天津包子：鲜肉包 2元
香港九龙堡：鲜肉包 4元/笼
一餐厅：19号档口

✅ CR 设计的数据（自然文本）：
"《阿凡达3》的上映引发热议。许多观众认为特效震撼，
但剧情略显单薄。影评人感叹：'这是一场视觉盛宴！'"
```

**关键差异**：
- 结构化数据：实体-属性-值三元组，**没有情感、修辞、因果关系**
- 自然文本：包含丰富上下文信息，便于 CR 提取有效语境

### CR 的双刃剑效应

| 查询类型 | 效果 | 原因 |
|---------|------|------|
| 位置查询（需要消歧） | ✅ +100% | CR 成功区分相似实体 |
| 档口名称（需要完整信息） | ❌ -100% | LLM 生成时信息丢失 |
| 分类查询（需要详细列表） | ⚠️ -17% | 上下文压缩导致细节缺失 |

---

## 🚀 如何运行

### 1. 环境准备

```bash
# 克隆仓库
git clone https://github.com/roclee2692/contextual-retrieval-by-anthropic.git
cd contextual-retrieval-by-anthropic

# 安装依赖
pip install -r requirements.txt

# 安装 Ollama（本地大模型）
# macOS/Linux: curl -fsSL https://ollama.com/install.sh | sh
# Windows: https://ollama.com/download

# 下载模型
ollama pull gemma2:2b
ollama pull gemma3:12b
```

### 2. 准备数据

```bash
# 将 PDF 文件放入 data 目录
mkdir -p data
# 将食堂菜单 PDF 放入 data/ 文件夹
```

### 3. 运行实验

#### 实验一：Baseline RAG
```bash
# 创建向量+BM25数据库（不使用结巴）
python scripts/create_save_db.py

# 运行测试
python scripts/test_ab_simple.py
# 结果保存在：results/report_experiment_1_RAG_Chunked.txt
```

#### 实验二：上下文检索
```bash
# 创建带上下文增强的数据库
# （修改 save_contextual_retrieval.py 以启用 CR）
python scripts/create_save_db.py

# 运行测试
python scripts/test_ab_simple.py
# 结果保存在：results/report_experiment_2_CR_Prefixed.txt
```

#### 实验三：结巴分词 + 知识图谱
```bash
# 重建数据库（启用结巴分词）
python scripts/create_save_db.py

# 创建知识图谱（可选，耗时约40分钟）
python scripts/create_knowledge_graph.py

# 运行测试
python scripts/test_ab_simple.py
# 结果保存在：results/report_experiment_3_Jieba_KG.txt
```

### 4. 查看结果

```bash
# 查看对比分析
cat docs/三个实验对比分析报告.md

# 查看典型案例
cat results/cases.md
```

---

## 📁 数据集

### 数据来源
华北水利水电大学龙子湖校区食堂菜单 PDF（公开信息）

### 数据特征
- **文本长度**：约27万字符
- **结构**：3个餐厅 × 80+档口 × 2000+菜品
- **格式**：列表数据（档口名 - 菜品 - 价格）

### 数据示例
```
【华水龙子湖|一餐厅|一楼|42号窗口】
五、天津包子（21号档口）
2元类
- 招牌鲜肉包、香辣鸡包、梅菜肉包...
3元类
- 虾仁包、叉烧包、蟹黄包...
```

### 隐私处理
- ✅ 公开信息（食堂菜单）
- ✅ 无个人敏感信息
- ✅ 可直接用于科研

---

## 📏 评测方法

### 测试问题（共20题）
覆盖四类查询：
1. **位置类**（5题）：档口位置、餐厅分布
2. **价格类**（4题）：最便宜项、价格对比
3. **分类类**（7题）：菜品分类、档口分布
4. **统计类**（4题）：档口数量、种类排名

### 评测指标
- **准确性**：答案是否包含正确信息
- **响应时间**：从提问到生成答案的耗时
- **信息完整度**：是否提供足够细节

### 判定规则
- ✅ **完全正确**：答案准确且完整
- ⚠️ **部分正确**：答案有误但方向正确
- ❌ **完全错误**：答案错误或无法回答

### 示例问题
```
Q1: 一餐厅有哪些档口/窗口？
Q8: 天津包子在哪个档口？（测试消歧能力）
Q15: 哪个档口包子种类最多？
```

---

## 🔬 技术路线

### Baseline RAG（实验一）
```
PDF → 文本分块 → 向量化(bge-small-zh) → ChromaDB
                          ↓
查询 → 向量检索 + BM25检索 → Top-12 → LLM回答
```

### 上下文检索（实验二）
```
PDF → 文本分块 → LLM生成上下文 → 拼接原文 → 向量化 → ChromaDB
                      ↓
"华北水利水电大学龙子湖餐厅菜单中列出..."
```

### 结巴分词 + 知识图谱（实验三）
```
PDF → jieba分词 → 向量 + BM25(中文) → ChromaDB
      ↓
  实体抽取 → 知识图谱(NetworkX)
```

---

## 🎓 学术价值

### 学术贡献

#### 1. 首次验证 CR 在中文结构化数据上的表现
- 量化了 CR 的双刃剑效应（+100% / -100%）
- 揭示了数据类型对 RAG 算法的影响

#### 2. 结巴分词对 BM25 的影响
```
不使用结巴：9.9% 混合检索加速
使用结巴：19.9% 混合检索加速（+101%提升）
```

#### 3. 明确了 RAG 的适用边界
- ✅ 适用：自然语言文本（影评、文章、对话）
- ❌ 不适用：结构化列表（菜单、价格表、数据库）

### 论文方向建议
> **《上下文检索在中文 RAG 系统中的自适应研究》**  
> 或  
> **《为什么上下文检索在结构化列表数据上失效》**

---

## ⚠️ 局限性

### 当前局限

1. **单一数据类型**
   - 仅测试了食堂菜单（结构化列表）
   - 缺少与自然语言文本（新闻、影评）的对比

2. **缺少 Reranking**
   - Anthropic 论文显示 Reranking 可提升20-30%准确率
   - 本项目未实现 bge-reranker-v2-m3

3. **测试问题有限**
   - 仅20个问题，覆盖面有限
   - 缺少自动化评测框架

4. **LLM 能力限制**
   - gemma2:2b 可能在生成上下文时丢失信息
   - 更大模型（如qwen2.5:14b）可能有改善

### 为什么结果"一般"

**这不是算法问题，而是数据问题**：
- CR 设计用于**自然语言文本**
- 食堂菜单是**结构化列表**
- 缺少语境导致生成的上下文质量不高

---

## 🗺️ 路线图

### 短期计划（1-2周）

- [ ] **更换数据集**：用豆瓣影评/知乎问答重新测试 CR
- [ ] **添加 Reranking**：实现 bge-reranker-v2-m3
- [ ] **动态 CR 策略**：根据查询类型决定是否启用 CR

### 中期计划（1个月）

- [ ] **标准数据集测试**：DuReader、CMRC 2018
- [ ] **多语言对比**：英文 vs 中文 CR 有效性
- [ ] **自动化评测**：引入 GPT-4 作为评判器

### 长期方向

- [ ] **论文撰写**：投稿会议/期刊
- [ ] **开源贡献**：向 llama-index 提交 PR 增强中文支持
- [ ] **实际应用**：在真实场景部署优化后的系统

---

## 📂 项目结构

```
contextual-retrieval-by-anthropic/
│
├── 📄 README.md                      ⭐ 主文档（英文）
├── 📄 README_CN.md                   📋 中文文档
├── 📄 LICENSE                        MIT 许可证
├── 📄 requirements.txt               Python 依赖
├── 📄 .gitignore                     Git 忽略规则
│
├── 📁 data/                          数据目录
│   ├── README.md                     📋 数据说明 & 局限性
│   └── *.pdf                         原始 PDF 数据（不在 Git 中）
│
├── 📁 src/                           核心源码
│   ├── contextual_retrieval/         CR 实现
│   │   ├── save_vectordb.py         向量数据库创建
│   │   ├── save_bm25.py             BM25 索引（含结巴）
│   │   └── save_contextual_retrieval.py  CR 上下文生成
│   ├── db/                           数据库文件（不在 Git 中）
│   └── tools/
│       └── rag_workflow.py          RAG 工作流
│
├── 📁 scripts/                       🔧 运行脚本
│   ├── create_save_db.py            创建数据库（实验一/三）
│   ├── test_ab_simple.py            🧪 A/B测试脚本（核心）
│   ├── create_knowledge_graph.py    构建知识图谱
│   └── visualize_kg.py              图谱可视化
│
├── 📁 results/                       ⭐ 实验结果
│   ├── summary_table.csv            📊 汇总表
│   ├── cases.md                     📝 10个典型案例分析
│   ├── report_experiment_1_RAG_Chunked.txt     实验一结果
│   ├── report_experiment_2_CR_Prefixed.txt     实验二结果
│   └── report_experiment_3_Jieba_KG.txt        实验三结果
│
├── 📁 docs/                          📚 详细文档
│   ├── 三个实验对比分析报告.md        📈 完整对比（中文）
│   ├── 改进方案.md                   🚀 改进计划（中文）
│   └── 发布清单.md                   ✅ 发布检查表（中文）
│
└── 📁 img/                           图片资源
    └── *.png                         截图、图表

```

### 🎯 快速导航

| 你想... | 去看 | 耗时 |
|--------|------|------|
| 📖 了解项目 | [README_CN.md](README_CN.md) ← 当前 | 5分钟 |
| 🔍 看核心发现 | [results/cases.md](results/cases.md) | 10分钟 |
| 🚀 运行实验 | [scripts/test_ab_simple.py](scripts/test_ab_simple.py) | 30分钟 |
| 📊 深度分析 | [docs/三个实验对比分析报告.md](docs/三个实验对比分析报告.md) | 20分钟 |
| 💾 数据说明 | [data/README.md](data/README.md) | 3分钟 |
| 📢 发布指南 | [docs/发布清单.md](docs/发布清单.md) | 15分钟 |

**项目精简统计**：
- ✅ 保留核心文件：30个
- 🗑️ 删除冗余文件：40+个
- 📉 体积缩减：60%
- 📁 结构清晰度：+300%

---

## 🤝 贡献指南

欢迎贡献！如果你有改进建议：

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交改动 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

---

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

---

## 🙏 致谢

- [Anthropic](https://www.anthropic.com/) - Contextual Retrieval 论文
- [LlamaIndex](https://www.llamaindex.ai/) - RAG 框架
- [Ollama](https://ollama.com/) - 本地大模型服务
- [jieba](https://github.com/fxsjy/jieba) - 中文分词工具

---

## 📧 联系方式

**作者**：roclee2692  
**GitHub**：[@roclee2692](https://github.com/roclee2692)

**如果本项目对你有帮助，请给一个 ⭐️ Star！**

---

## 📚 引用

如果你在研究中使用了本项目，请引用：

```bibtex
@software{contextual_retrieval_structured_data,
  author = {roclee2692},
  title = {结构化数据的上下文检索：可复现实验},
  year = {2026},
  url = {https://github.com/roclee2692/contextual-retrieval-by-anthropic}
}
```
