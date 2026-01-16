# 龙子湖食堂知识图谱构建指南

## 🎯 方案：OneKE + LlamaIndex 知识图谱 RAG

### 技术栈
- **OneKE**: 知识抽取（提取三元组）
- **LlamaIndex**: 图谱索引和查询
- **Neo4j/NetworkX**: 图数据库
- **Ollama**: LLM 推理

---

## 📊 架构设计

```
PDF 文档
    ↓
OneKE 抽取
    ↓
三元组 (实体-关系-实体)
    ↓
LlamaIndex KnowledgeGraphIndex
    ↓
图谱推理 + 向量检索
    ↓
LLM 生成答案
```

---

## 🔧 实现步骤

### 步骤 1: 安装依赖

```bash
# 基础依赖（已有）
pip install llama-index

# 知识图谱相关
pip install llama-index-graph-stores-neo4j  # 如果用 Neo4j
pip install networkx matplotlib  # 如果用 NetworkX（轻量级）

# OneKE 抽取工具
pip install oneke  # 或使用 API 版本
```

### 步骤 2: 使用 OneKE 提取三元组

**方式 A: 使用 OneKE Python 库**
```python
from oneke import OneKE

# 初始化 OneKE
extractor = OneKE(model="oneke-v1")

# 读取 PDF 文本
with open("./data/NCWU_Longzihu_Canteens_RAG_Chunked.pdf", "r") as f:
    text = f.read()

# 提取三元组
triples = extractor.extract(text)
# 输出格式: [(head, relation, tail), ...]
# 例如: [("一号餐厅", "有窗口", "19号我爱我粥"), 
#        ("我爱我粥", "提供", "小米南瓜粥"), 
#        ("小米南瓜粥", "价格", "2元")]
```

**方式 B: 使用 LlamaIndex 内置抽取**
```python
from llama_index.core import KnowledgeGraphIndex
from llama_index.core import SimpleDirectoryReader
from llama_index.llms.ollama import Ollama

# 读取文档
documents = SimpleDirectoryReader("./data").load_data()

# 使用 Ollama 抽取知识图谱
llm = Ollama(model="gemma3:12b", base_url="http://localhost:11434")

# 自动抽取三元组
kg_index = KnowledgeGraphIndex.from_documents(
    documents,
    llm=llm,
    max_triplets_per_chunk=10,
    include_embeddings=True
)
```

### 步骤 3: 创建知识图谱索引

**完整代码示例**:

```python
from llama_index.core import KnowledgeGraphIndex, SimpleDirectoryReader
from llama_index.core.graph_stores import SimpleGraphStore
from llama_index.llms.ollama import Ollama
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
import os

# 配置
os.environ["OLLAMA_BASE_URL"] = "http://localhost:11434"

# 初始化 LLM
llm = Ollama(
    model="gemma3:12b",
    base_url=os.getenv("OLLAMA_BASE_URL"),
    request_timeout=120.0
)

# 初始化 Embedding
embed_model = HuggingFaceEmbedding(
    model_name="BAAI/bge-base-en-v1.5"
)

# 读取文档
documents = SimpleDirectoryReader("./data").load_data()

# 创建图存储
graph_store = SimpleGraphStore()

# 创建知识图谱索引
kg_index = KnowledgeGraphIndex.from_documents(
    documents,
    llm=llm,
    embed_model=embed_model,
    graph_store=graph_store,
    max_triplets_per_chunk=5,
    include_embeddings=True,
    show_progress=True
)

# 保存图谱
kg_index.storage_context.persist(persist_dir="./src/db/knowledge_graph")
```

### 步骤 4: 查询知识图谱

```python
# 加载已保存的图谱
from llama_index.core import load_index_from_storage
from llama_index.core import StorageContext

storage_context = StorageContext.from_defaults(
    persist_dir="./src/db/knowledge_graph"
)
kg_index = load_index_from_storage(storage_context)

# 创建查询引擎
query_engine = kg_index.as_query_engine(
    include_text=True,  # 包含原始文本
    response_mode="tree_summarize",
    embedding_mode="hybrid",
    similarity_top_k=5
)

# 查询
response = query_engine.query("一号餐厅有哪些窗口？")
print(response)

# 获取子图（可视化相关实体）
sub_graph = kg_index.get_networkx_graph()
```

---

## 🎨 知识图谱结构示例

### 食堂领域三元组
```
(一号餐厅, 类型, 食堂)
(一号餐厅, 位置, 龙子湖校区)
(一号餐厅, 包含窗口, 19号我爱我粥)
(19号我爱我粥, 提供, 小米南瓜粥)
(小米南瓜粥, 价格, 2元)
(小米南瓜粥, 容量, 一杯)

(二号餐厅, 类型, 食堂)
(二号餐厅, 楼层, 一楼)
(二号餐厅, 包含窗口, 21号天津包子)
(21号天津包子, 提供, 招牌鲜肉包)
(招牌鲜肉包, 价格, 2元)
```

### 图谱优势
1. **关系推理**: "一号餐厅有哪些2元的食品？" → 遍历价格关系
2. **多跳查询**: "最便宜的包子在哪个食堂？" → 价格比较 + 窗口归属
3. **实体聚合**: "所有粥类产品" → 按类别聚合

---

## 🔄 混合检索：向量 + 图谱 + BM25

```python
from llama_index.core import QueryBundle
from llama_index.core.retrievers import (
    VectorIndexRetriever,
    KnowledgeGraphRAGRetriever,
    BM25Retriever
)
from llama_index.core.query_engine import RetrieverQueryEngine

# 1. 向量检索器
vector_retriever = VectorIndexRetriever(
    index=vector_index,
    similarity_top_k=3
)

# 2. 知识图谱检索器
kg_retriever = KnowledgeGraphRAGRetriever(
    storage_context=kg_storage_context,
    graph_store=graph_store,
    llm=llm,
    include_text=True
)

# 3. BM25 检索器
bm25_retriever = BM25Retriever.from_defaults(
    nodes=nodes,
    similarity_top_k=3
)

# 融合查询引擎
from llama_index.core.query_engine import RouterQueryEngine
from llama_index.core.selectors import LLMSingleSelector

query_engine = RouterQueryEngine(
    selector=LLMSingleSelector.from_defaults(llm=llm),
    query_engine_tools=[
        vector_tool,
        kg_tool,
        bm25_tool
    ]
)

response = query_engine.query("一号餐厅有什么便宜的早餐？")
```

---

## 📝 完整脚本：create_knowledge_graph.py

```python
"""
创建食堂知识图谱
"""
import os
from dotenv import load_dotenv
from llama_index.core import (
    KnowledgeGraphIndex,
    SimpleDirectoryReader,
    StorageContext
)
from llama_index.core.graph_stores import SimpleGraphStore
from llama_index.llms.ollama import Ollama
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

load_dotenv()

print("="*80)
print("龙子湖食堂知识图谱构建")
print("="*80)

# 配置
DATA_DIR = os.getenv("DATA_DIR", "./data")
SAVE_DIR = "./src/db/knowledge_graph"
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# 初始化组件
print("\n[1/4] 初始化 LLM 和 Embedding...")
llm = Ollama(
    model="gemma3:12b",
    base_url=OLLAMA_BASE_URL,
    request_timeout=180.0
)

embed_model = HuggingFaceEmbedding(
    model_name="BAAI/bge-base-en-v1.5"
)

# 读取文档
print("\n[2/4] 读取 PDF 文档...")
documents = SimpleDirectoryReader(DATA_DIR).load_data()
print(f"✓ 加载了 {len(documents)} 个文档")

# 创建图存储
print("\n[3/4] 创建知识图谱（可能需要 10-30 分钟）...")
graph_store = SimpleGraphStore()

kg_index = KnowledgeGraphIndex.from_documents(
    documents,
    llm=llm,
    embed_model=embed_model,
    graph_store=graph_store,
    max_triplets_per_chunk=5,
    include_embeddings=True,
    show_progress=True
)

# 保存图谱
print("\n[4/4] 保存知识图谱...")
kg_index.storage_context.persist(persist_dir=SAVE_DIR)

print("\n" + "="*80)
print("✅ 知识图谱创建完成！")
print(f"保存位置: {SAVE_DIR}")
print("="*80)

# 测试查询
print("\n测试查询: 龙子湖校区有几个食堂？")
query_engine = kg_index.as_query_engine(
    include_text=True,
    response_mode="tree_summarize"
)
response = query_engine.query("龙子湖校区有几个食堂？")
print("\n答案:")
print(response)
```

---

## 🎯 对比三种方法

| 方法 | 优势 | 劣势 | 适用场景 |
|------|------|------|----------|
| **纯向量检索** | 快速、语义理解好 | 缺乏结构化推理 | 开放性问题 |
| **BM25 关键词** | 精确匹配、快 | 无语义理解 | 实体查找 |
| **知识图谱** | 关系推理、多跳查询 | 构建慢、需要抽取 | 复杂关联查询 |

### 最佳实践：三者结合
```
用户查询
    ↓
路由器选择
    ↓
┌──────────┬──────────┬──────────┐
│ 向量检索 │ BM25     │ 图谱推理 │
└──────────┴──────────┴──────────┘
    ↓         ↓         ↓
    结果融合 + 重排序
    ↓
    LLM 生成最终答案
```

---

## 🚀 快速开始

### 方式 1: 轻量级（NetworkX）
```bash
pip install networkx matplotlib
python create_knowledge_graph.py
```

### 方式 2: 生产级（Neo4j）
```bash
# 启动 Neo4j Docker
docker run -d \
  --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password \
  neo4j:latest

# 安装依赖
pip install llama-index-graph-stores-neo4j

# 修改代码使用 Neo4jGraphStore
```

---

## 📊 预期效果

### 查询示例
**Q**: "一号餐厅有哪些2元的食品？"

**图谱推理**:
1. 找到实体 "一号餐厅"
2. 遍历 "包含窗口" 关系
3. 遍历 "提供" 关系
4. 过滤 "价格=2元"
5. 返回所有符合的食品

**答案**: 
- 小米南瓜粥（19号我爱我粥）
- 清火绿豆粥（19号我爱我粥）
- ...

---

## ⚠️ 注意事项

1. **抽取质量**: OneKE/LLM 抽取的三元组需要人工审核
2. **计算成本**: 知识图谱构建比纯向量检索慢 5-10 倍
3. **存储需求**: 图谱需要额外存储空间
4. **查询复杂度**: 多跳查询可能较慢

---

## 📚 参考资源

- [LlamaIndex Knowledge Graph](https://docs.llamaindex.ai/en/stable/examples/index_structs/knowledge_graph/)
- [OneKE 文档](https://github.com/zjunlp/DeepKE/tree/main/example/llm/OneKE)
- [Neo4j Python Driver](https://neo4j.com/docs/python-manual/current/)

---

**建议**: 先用现有的向量+BM25方案完成测试，知识图谱作为进阶优化！

