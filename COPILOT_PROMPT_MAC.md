# AI 助手提示词 — Mac 端项目复刻

> 把以下内容直接粘贴给 Mac 上的 AI 助手（GitHub Copilot / Claude / ChatGPT 均可）。

---

## 提示词正文

```
你好！请帮我在这台 macOS 电脑上完整复刻一个 Python RAG（检索增强生成）研究项目。

## 项目背景

这是一个用于**防洪文档智能检索**的研究项目，对比了三种检索方案：
1. Baseline (BM25 + 向量检索)
2. Contextual Retrieval (CR) - Anthropic 提出的上下文增强检索
3. Knowledge Graph RAG

技术栈：
- LLM: Gemma 3:12B（通过 Ollama 本地运行）
- 向量库: ChromaDB
- 框架: LlamaIndex
- Embedding: BAAI/bge-small-zh-v1.5（中文）
- Reranker: BAAI/bge-reranker-base（Cross-Encoder）

## 你的任务

按照以下顺序帮我完成配置：

### 1. 检查 Python 版本
```bash
python3 --version   # 需要 3.10 或 3.11
```
如果没有，用 `brew install python@3.11` 安装。

### 2. 创建虚拟环境并安装依赖
```bash
cd contextual-retrieval-by-anthropic
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
如果遇到报错，请告诉我具体错误信息。

### 3. 安装 Ollama 并拉取模型
```bash
brew install ollama
ollama serve &   # 后台运行 Ollama 服务
ollama pull gemma3:12b   # 下载约 7GB
```

### 4. 配置环境变量
```bash
cp .env.example .env
# 确认 .env 中 OLLAMA_BASE_URL=http://localhost:11434
```

### 5. 验证安装
```bash
python -c "import llama_index; import chromadb; import sentence_transformers; print('OK')"
```

### 6. 构建向量数据库
```bash
python scripts/create_save_db.py
```

### 7. 运行实验
```bash
python scripts/phase3_baseline_vs_cr.py
```

## 注意事项

- Apple Silicon (M1/M2/M3)：所有依赖均原生支持 ARM，不需要 Rosetta
- 如果 `chromadb` 安装失败，尝试 `pip install chromadb --no-binary chromadb`
- `jieba` 在 Mac 上直接 pip 安装即可，无需额外配置
- HuggingFace 模型在**第一次运行时**自动从网络下载，需要联网
- `data/` 目录中的 PDF 文件**不在 git 仓库中**，需要从 Windows 机器单独拷贝过来

## 遇到问题时

请把完整的报错信息告诉我，我会帮你逐步排查。常见问题：
- `ModuleNotFoundError`: 运行 `pip install -r requirements.txt` 重新安装
- `Connection refused` (Ollama): 运行 `ollama serve` 启动服务
- CUDA/MPS 相关警告：可以忽略，项目主要在 CPU 上运行
```

---

## 拷贝 data/ 目录的方法

data/ 目录中有原始 PDF 文件，不在 Git 仓库中，需要从 Windows 机器传过来。

**推荐方式：局域网传输**

Windows 机器：
```powershell
# 用 7zip 或自带工具压缩 data 目录
Compress-Archive -Path "data" -DestinationPath "data_backup.zip"
```

然后通过 AirDrop、局域网共享、或 U 盘传输到 Mac。

Mac 解压：
```bash
cd contextual-retrieval-by-anthropic
unzip data_backup.zip
```
