"""
创建防洪预案知识图谱 - 基于 LlamaIndex
使用 LLM 自动从文档中抽取三元组
"""
import os
import sys

# Windows path fix
if sys.platform == 'win32':
    # This might help with some path length issues or encoding
    pass

from pathlib import Path
from dotenv import load_dotenv
from llama_index.core import (
    KnowledgeGraphIndex,
    SimpleDirectoryReader,
    StorageContext,
    Settings,
    PromptTemplate
)
from llama_index.core.graph_stores import SimpleGraphStore
from llama_index.llms.ollama import Ollama
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

# 自定义知识抽取 Schema（针对防洪预案领域）
KG_TRIPLET_EXTRACT_TMPL = """
你是一个专门从防洪预案文档中提取知识图谱的助手。

请从以下文本中提取实体和关系，构建三元组。请尽可能提取关键的防洪实体。

【目标实体类型】
- 水库 (Reservoir)、河流 (River)、堤防 (Dike)
- 机构 (Organization)、部门 (Department)、人员 (Person)、职位 (Role)
- 预案 (Plan)、措施 (Measure)、物资 (Resource)
- 地点 (Location)、水位 (WaterLevel)、警戒线 (AlertLevel)

【关键关系类型】
- managed_by (由...管理), responsible_for (负责)
- located_at (位于), triggers (触发), requires (需要)
- has_measure (采取措施), contacts (联系)
- higher_than (高于), lower_than (低于)

【示例】
文本："常庄水库防汛指挥部由李市长担任指挥长，负责统一调度。"
三元组：
(常庄水库防汛指挥部, managed_by, 李市长)
(李市长, has_role, 指挥长)
(常庄水库防汛指挥部, responsible_for, 统一调度)

请处理以下文本：
{text}

输出格式：每行一个三元组 (头实体, 关系, 尾实体)
"""

def create_knowledge_graph():
    """创建知识图谱索引"""

    load_dotenv()

    print("="*80)
    print("  防洪预案知识图谱构建 (Phase 2)")
    print("="*80)

    # 配置
    DATA_DIR = os.getenv("DATA_DIR", "./data")
    SAVE_DIR = "./src/db/knowledge_graph"
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    
    # 确保保存目录存在
    Path(SAVE_DIR).mkdir(parents=True, exist_ok=True)

    # 初始化组件
    print("\n[1/5] 初始化 LLM 和 Embedding...")
    llm = Ollama(
        model="gemma3:12b",
        base_url=OLLAMA_BASE_URL,
        request_timeout=240.0, # 增加超时时间
        context_window=8192
    )

    embed_model = HuggingFaceEmbedding(
        model_name="BAAI/bge-small-zh-v1.5",
        device="cpu"
    )

    # 设置全局配置
    Settings.llm = llm
    Settings.embed_model = embed_model
    Settings.chunk_size = 512
    Settings.chunk_overlap = 50 

    print("✓ LLM 和 Embedding 初始化完成")

    # 读取文档
    print(f"\n[2/5] 读取文档... (目录: {DATA_DIR})")
    # 只读取 .txt 文件，避免 PDF/Word 解析问题
    reader = SimpleDirectoryReader(DATA_DIR, required_exts=[".txt"], recursive=True)
    documents = reader.load_data()
    print(f"✓ 加载了 {len(documents)} 个文档片段")

    # 创建图存储
    print("\n[3/5] 初始化图存储...")
    graph_store = SimpleGraphStore()
    storage_context = StorageContext.from_defaults(graph_store=graph_store)
    print("✓ 图存储创建完成")

    # 创建知识图谱（耗时较长）
    print("\n[4/5] 从文档中提取知识图谱...")
    print("⏱️  注意：此过程调用 LLM 提取三元组，速度较慢，请耐心等待...")
    
    # 使用较小的 max_triplets_per_chunk 以加快速度，防止幻觉
    kg_index = KnowledgeGraphIndex.from_documents(
        documents,
        storage_context=storage_context,
        max_triplets_per_chunk=3, 
        kg_triple_extract_template=PromptTemplate(KG_TRIPLET_EXTRACT_TMPL),
        show_progress=True,
        include_embeddings=True, # 同时也建立向量索引，支持混合检索
    )
    
    print("✓ 知识图谱提取完成")

    # 保存
    print(f"\n[5/5] 保存到磁盘: {SAVE_DIR}")
    kg_index.storage_context.persist(persist_dir=SAVE_DIR)
    
    print("\n" + "="*80)
    print(f"✅ 完成！知识图谱已保存至: {SAVE_DIR}")
    print("现在可以使用 scripts/test_kg_retrieval.py (需创建) 进行测试")
    print("="*80)

if __name__ == "__main__":
    create_knowledge_graph()

