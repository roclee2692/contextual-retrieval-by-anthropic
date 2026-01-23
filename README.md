# Contextual Retrieval & Knowledge Graph: Multi-Domain Experiments
# 上下文检索与知识图谱：多领域对比实验

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**[English](#english) | [中文](#chinese)**

---

<a name="english"></a>
## 🇬🇧 English Overview

This repository demonstrates **Advanced RAG** techniques including **Contextual Retrieval (CR)** and **Knowledge Graphs (KG)** applied to structured and semi-structured data.  
It solves the "loss of context" problem in traditional RAG by using LLMs to generate context for document chunks.

This project now contains two distinct experiments (Datasets):

1.  **Experiment A: Canteen Menus (Original)**
    *   **Data**: 270k characters of structured canteen menu data.
    *   **Focus**: Comparing Baseline RAG vs. CR vs. Jieba optimized BM25.
    *   **Finding**: CR is great for disambiguation but can lose details in dense lists.
2.  **Experiment B: Flood Prevention Plans (New)**
    *   **Data**: Domain-specific government flood emergency plans.
    *   **Focus**: **Knowledge Graph** construction for entity relationship reasoning (e.g., "Who commands the response?").
    *   **Finding**: KG significantly improves reasoning on hierarchical organizational structures.

---

<a name="chinese"></a>
## 🇨🇳 中文介绍

本项目展示了 **高级 RAG** 技术，包括 **上下文检索 (Contextual Retrieval)** 和 **知识图谱 (Knowledge Graph)** 在不同数据类型上的应用。
核心思想是利用 LLM 为文档切片生成背景上下文，解决传统 RAG 的“断章取义”问题。

本项目包含两个独立的实验（数据集）：

### 1. 实验 A：高校食堂菜单 (Original)
*   **数据**：华北水利水电大学龙子湖校区食堂菜单（270k 字符，结构化列表）。
*   **重点**：对比 Baseline RAG、CR 增强版以及 Jieba 分词优化的效果。
*   **结论**：CR 在消除歧义（如“天津包子” vs “包子”）方面效果显著，但在密集列表数据的细节保留上存在挑战。

### 2. 实验 B：防洪应急预案 (New)
*   **数据**：垂直领域的防洪应急预案文本（非结构化/半结构化）。
*   **重点**：构建 **知识图谱** 解决实体关系推理问题（如“谁是防洪总指挥？”）。
*   **结论**：知识图谱能精准捕捉组织架构和职责关系，弥补了纯向量检索在逻辑推理上的短板。

---

## 🚀 Usage / 使用指南

### 🔧 Configuration / 配置切换

Since there are two datasets, we use `.env` files to switch configurations.
由于有两个数据集，我们使用 `.env` 文件来切换配置。

**For Canteen Experiment (Run Experiment A):**
**运行食堂菜单实验：**
```bash
# Windows (PowerShell)
Copy-Item .env.canteen .env
```

**For Flood Experimen (Run Experiment B):**
**运行防洪预案实验：**
```bash
# Windows (PowerShell)
Copy-Item .env.flood .env
```

### 🏗️ Build & Run / 构建与运行

#### Phase 1: Contextual Retrieval DB / 构建上下文数据库
(Works for both experiments based on `.env`)
（根据 `.env` 配置自动适配）
```bash
python scripts/create_save_db.py
```

#### Phase 2: Knowledge Graph / 构建知识图谱
(Currently optimized for Flood Prevention data)
（目前主要针对防洪数据优化）
```bash
python scripts/create_knowledge_graph.py
```

#### Verification / 验证
```bash
# Flood Verification
python scripts/test_kg_retrieval.py
```

---

## 📂 Project Structure / 项目结构

```
d:\DpanPython\python-projects\contextual-retrieval-by-anthropic
├── .env                    # Current active config
├── .env.canteen            # Config for Canteen Menu Experiment
├── .env.flood              # Config for Flood Prevention Experiment
├── data/
│   ├── 防洪预案_txt/        # Data for Flood Exp
│   └── (pdf files...)      # Data for Canteen Exp
├── src/
│   ├── db/                 # Database storage
│   │   ├── canteen_db_*/           # DBs for Canteen
│   │   ├── flood_prevention_db_*/  # DBs for Flood
│   │   └── knowledge_graph/        # Shared/Generic KG store
└── scripts/                # Build and Test scripts
```

---

## 📊 Experiment A Results (Canteen) / 食堂实验结果

| Method | Avg Time | Accuracy (Category) | Accuracy (Price) |
|--------|----------|---------------------|------------------|
| Baseline RAG | 12.79s | 100% | 75% |
| **Contextual Retrieval** | 13.64s | 83% | **100%** |
| **Jieba + KG** | **10.13s** | 83% | **100%** |

> **Insight**: CR shows **double-edged effect** on structured data — +100% disambiguation accuracy but -100% on detail-heavy queries due to **lack of natural language context**.
> **洞察**：CR 在结构化数据上是一把双刃剑——它能 100% 消除歧义，但因为重写过程丢失了原有格式，导致密集细节查询准确率下降。

---

## 📊 Experiment B Results (Flood) / 防洪实验结果

*Detailed report available in `results/flood_comparison_report.md`*
*详细报告见 `results/flood_comparison_report.md`*

*   **Contextual Retrieval** significantly outperforms Baseline RAG in finding specific procedural details.
*   **Knowledge Graph** successfully mapped entity relationships (Commander -> Role -> Responsibilities).
*   **CR** 在查找具体流程细节方面显著优于 Baseline RAG。
*   **知识图谱** 成功映射了实体关系（指挥官 -> 角色 -> 职责）。
