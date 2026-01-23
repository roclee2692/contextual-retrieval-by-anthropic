# Contextual Retrieval on Structured Data: A Reproducible Experiment

**[English](README.md) | [简体中文](README_CN.md)**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Reproducible](https://img.shields.io/badge/reproducible-yes-green.svg)](https://github.com/roclee2692/contextual-retrieval-by-anthropic)

> **Based on**: [Anthropic's Contextual Retrieval](https://www.anthropic.com/news/contextual-retrieval) | **Extended with**: Chinese dataset + comparative experiments + jieba tokenization + knowledge graph

---

## ⚡ TL;DR

**What**: Reproduced Anthropic's Contextual Retrieval on Chinese canteen menu data (270k chars) with 3 controlled experiments  
**Best Result**: Jieba+KG achieved **10.13s avg response** (21% faster) with **19.9% hybrid retrieval speedup**  
**Key Finding**: CR shows **double-edged effect** on structured data — +100% disambiguation accuracy but -100% on detail-heavy queries due to **lack of natural language context**

### 📊 At-a-Glance Results (Canteen Dataset)

| Experiment | Method | Avg Time | Overall Accuracy | Best Use Case |
|-----------|--------|----------|-----------------|---------------|
| **Exp 1** | Baseline RAG | 12.79s | 83.3% | Category queries (100%) |
| **Exp 2** | CR Enhanced | 13.64s | **86.0%** ✅ | Price queries (100%), disambiguation |
| **Exp 3** | Jieba + KG | **10.13s** ⚡ | 77.7% | Speed (21% faster than baseline) |

**Winner**: CR improves accuracy by +3%, but **Jieba tokenization** brings the biggest speed gain (+21%)

---

## 🆕 Phase 2 Extension: Flood Prevention & Knowledge Graph

Building on the findings from the "Structured List Data" (Canteen Exp), we extended the project to a **Domain Specific Unstructured/Semi-structured Data** scenario: **Flood Prevention Plans**.

> **Note**: To switch between experiments, use the configuration files:
> - Canteen Exp: `Copy-Item .env.canteen .env`
> - Flood Exp: `Copy-Item .env.flood .env`

### Key Results from Phase 2 (Flood Dataset)

*Detailed report available in `results/flood_comparison_report.md`*

*   **Contextual Retrieval** significantly outperforms Baseline RAG in finding specific procedural details.
*   **Knowledge Graph (KG)** successfully mapped **600+ entities** (Commander -> Role -> Responsibilities), solving the reasoning gap found in the Canteen experiment.
*   **Reasoning Capability**: The KG allows for multi-hop queries like "Who is responsible for the reservoir overflow trigger?" which pure vector search struggles with.

---

## 🔄 System Pipeline

```mermaid
graph LR
    A[PDF Data] --> B[Text Chunking]
    B --> C{CR Enabled?}
    C -->|Yes| D[LLM Context Gen]
    C -->|No| E[Original Chunks]
    D --> F[Concat Context<br/>+ Original]
    E --> G[Embedding<br/>bge-small-zh]
    F --> G
    G --> H[Vector DB<br/>ChromaDB]
    B --> I{Jieba?}
    I -->|Yes| J[Chinese Tokenize<br/>(Exp 1-3)]
    I -->|No| K[Default English]
    J --> L[BM25 Index]
    K --> L
    M[User Query] --> N[Hybrid Retrieval]
    H --> N
    L --> N
    
    subgraph Phase 2: Knowledge Graph
    B --> O[Entity Extraction]
    O --> P[Graph Store<br/>Structure]
    P --> Q[Graph Query]
    Q -.-> N
    end
```

---

## 🎯 What It Is

This project reproduces [Anthropic's Contextual Retrieval paper](https://www.anthropic.com/news/contextual-retrieval) with three comparative experiments in Chinese:

| Experiment | Method | Core Technologies | Target Data |
|-----------|--------|------------------|-------------|
| **Exp 1** | Baseline RAG | Vector Retrieval (bge-small-zh) + BM25 | Canteen (List) |
| **Exp 2** | CR Enhanced | LLM-generated context prefix + Vector+BM25 | Canteen (List) |
| **Exp 3** | With Jieba + KG | Jieba Chinese tokenization + Knowledge Graph | Canteen (List) |
| **Exp 4 (New)** | **Flood Domain KG** | Domain-specific Schema + Deep Reasoning | **Flood Plans (Text)** |

---

## 📊 Key Results (Phase 1: Canteen)

### Performance Comparison

| Metric | Exp 1 (Baseline) | Exp 2 (CR) | Exp 3 (Jieba+KG) |
|--------|-----------------|-----------|----------------|
| **Avg Response Time** | 12.79s | 13.64s (+6.7%) | **10.13s** ⚡ |
| **Hybrid Retrieval Speedup** | 9.9% | 8.5% | **19.9%** |
| **Price Query Accuracy** | 75% | **100%** ✅ | **100%** ✅ |
| **Category Query Accuracy** | **100%** ✅ | 83% | 83% |
| **Location Query Accuracy** | 75% | **75%** | 50% |

### Critical Findings

#### ✅ CR Success Cases
- **Q8 Tianjin Baozi Location**: Exp 1 (0%) → Exp 2 (**100%**)
  - CR successfully disambiguated "Tianjin Baozi" from "Hong Kong Jiulong Bao"

#### ❌ CR Failure Cases
- **Q9 Stall Name Query**: Exp 1 (100%) → Exp 2 (**0%**)
  - Key information (stall names) lost during context generation

---

## 🚀 Quickstart (Copy & Run)

### Prerequisites
- Python 3.11+
- [Ollama](https://ollama.com/download) installed
- `gemma3:12b` (for QA) and `gemma2:2b` (for context)

### 1️⃣ Setup (Universal)

```bash
git clone https://github.com/roclee2692/contextual-retrieval-by-anthropic.git
cd contextual-retrieval-by-anthropic
pip install -r requirements.txt
```

### 2️⃣ Run Canteen Experiment (Original)

```bash
# Switch Config
Copy-Item .env.canteen .env

# Run
python scripts/create_save_db.py
python scripts/test_ab_simple.py
```

### 3️⃣ Run Flood Experiment (New Phase 2)

```bash
# Switch Config
Copy-Item .env.flood .env

# Run KG Construction (Time consuming!)
python scripts/create_knowledge_graph.py

# Verify Reasoning
python scripts/test_kg_retrieval.py
```

---

## 📁 Project Structure

```
contextual-retrieval-by-anthropic/
├── .env                    # Active Config
├── .env.canteen            # Config for Exp 1 (Canteen)
├── .env.flood              # Config for Exp 2 (Flood)
├── data/                   # Dataset Folder
├── src/                    # Core Logic
│   ├── contextual_retrieval/
│   ├── db/                 # Vector/BM25/Graph Stores
│   └── tools/
└── scripts/                # Experiment Scripts
    ├── test_ab_simple.py       # Canteen Test
    ├── test_kg_retrieval.py    # Flood KG Test
    └── ...
```

---

## 📧 Contact

**Author**: roclee2692
**GitHub**: [@roclee2692](https://github.com/roclee2692)

**If this project helps you, please give it a ⭐️ Star!**

---

## 📚 Citation

If you use this project in your research, please cite:

```bibtex
@software{contextual_retrieval_structured_data,
  author = {roclee2692},
  title = {Contextual Retrieval on Structured Data: A Reproducible Experiment},
  year = {2026},
  url = {https://github.com/roclee2692/contextual-retrieval-by-anthropic}
}
```
