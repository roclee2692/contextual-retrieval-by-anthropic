# Mac 环境复刻指南

> 本指南用于在 macOS（Apple Silicon 或 Intel）上从零复刻该项目的完整运行环境。

---

## 第一步：克隆仓库

```bash
git clone https://github.com/roclee2692/contextual-retrieval-by-anthropic.git
cd contextual-retrieval-by-anthropic
```

---

## 第二步：安装 Python 环境

推荐使用 Python 3.11（用 pyenv 或 Homebrew 安装）。

```bash
# 如果没有 Homebrew，先安装
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 安装 Python
brew install python@3.11

# 创建虚拟环境
python3.11 -m venv .venv
source .venv/bin/activate

# 安装所有依赖
pip install -r requirements.txt
```

---

## 第三步：安装 Ollama 并下载模型

```bash
# 安装 Ollama（macOS 版）
brew install ollama
# 或直接从官网下载：https://ollama.com/download

# 启动 Ollama 服务（后台运行）
ollama serve &

# 下载 Gemma 3:12B 模型（约 7GB，需要等待）
ollama pull gemma3:12b
```

验证模型可用：

```bash
ollama list
# 应该能看到 gemma3:12b
```

---

## 第四步：配置环境变量

```bash
cp .env.example .env
```

用文本编辑器打开 `.env`，确认以下内容：

```dotenv
OLLAMA_BASE_URL=http://localhost:11434
LLM_MODEL=gemma3:12b
EMBEDDING_MODEL=BAAI/bge-small-zh-v1.5
```

---

## 第五步：Embedding 和 Reranker 模型（自动下载）

这两个模型在**第一次运行实验脚本时自动下载**，无需手动操作：

| 模型 | 用途 | 大小 |
|------|------|------|
| `BAAI/bge-small-zh-v1.5` | 中文向量嵌入 | ~90MB |
| `BAAI/bge-reranker-base` | 重排序 Cross-Encoder | ~280MB |

HuggingFace 缓存目录默认：`~/.cache/huggingface/`

---

## 第六步：重建数据库（Baseline + CR 向量库）

数据库不在 git 中，需要在本地重新生成：

```bash
# 激活环境
source .venv/bin/activate

# 生成防洪文档检索数据库（需要先确保 data/ 目录中有原始PDF）
python scripts/create_save_db.py
```

---

## 第七步：运行实验验证

```bash
# Phase 3 基线 vs CR 对比实验
python scripts/phase3_baseline_vs_cr.py

# 查看结果
cat results/phase3_baseline_vs_cr.md
```

---

## 注意事项

- **Apple Silicon（M系列）**：`sentence-transformers` 和 `chromadb` 均支持 MPS 加速
- **Ollama 性能**：M2/M3 Pro 以上运行 gemma3:12b 较流畅；M1 基础款速度较慢
- **内存要求**：建议 16GB+ RAM，gemma3:12b 约占用 8-10GB
- **data/ 目录**：原始 PDF 文件不在 git 中，需要手动拷贝（从 Windows 机器压缩后传输）

---

## 目录结构说明

```
contextual-retrieval-by-anthropic/
├── scripts/          # 实验脚本（主要入口）
│   ├── phase3_baseline_vs_cr.py     # Phase 3 主实验
│   ├── phase3_reranker_ablation.py  # Reranker 消融实验
│   └── create_save_db.py            # 构建数据库
├── src/
│   ├── contextual_retrieval/        # CR 核心模块
│   ├── db/                          # 数据库读取工具
│   ├── tools/                       # RAG 工作流
│   └── schema/                      # 数据 Schema
├── data/                            # 原始文档（不在git中）
├── results/                         # 实验结果 JSON + MD
├── requirements.txt                 # Python 依赖
└── run_experiment.py                # 统一实验入口
```
