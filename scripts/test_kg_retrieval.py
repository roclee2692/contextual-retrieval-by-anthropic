"""
知识图谱检索测试脚本 - 防洪预案
测试 Phase 2 构建的 Knowledge Graph 效果
"""
import os
import sys

# Windows encoding fix
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from pathlib import Path
from dotenv import load_dotenv
from llama_index.core import (
    StorageContext,
    load_index_from_storage,
    Settings
)
from llama_index.core.retrievers import KnowledgeGraphRAGRetriever
from llama_index.llms.ollama import Ollama
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

# Load environment
load_dotenv()
sys.path.insert(0, str(Path(__file__).parents[1]))  # Add project root

ROOT = Path(__file__).resolve().parents[1]
KG_DIR = str(ROOT / "src" / "db" / "knowledge_graph")

def test_kg_retrieval():
    print("="*80)
    print("  防洪预案知识图谱检索测试")
    print("="*80)

    if not os.path.exists(KG_DIR):
        print(f"❌ 错误: 知识图谱目录不存在 {KG_DIR}。请先运行 create_knowledge_graph.py")
        return

    # 1. Initialize Objects (Must match creation config)
    print("Initialize LLM & Embedding...")
    # Use OneKE to stay consistent with the extraction phase and VRAM usage
    llm = Ollama(
        model="oneke", 
        request_timeout=120.0,
        context_window=1024
    )
    embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-zh-v1.5", device="cpu")
    Settings.llm = llm
    Settings.embed_model = embed_model

    # 2. Load KG Index
    print(f"Loading Knowledge Graph from {KG_DIR}...")
    storage_context = StorageContext.from_defaults(persist_dir=KG_DIR)
    kg_index = load_index_from_storage(storage_context)
    print("✅ Index Loaded Successfully!")

    # 3. Test Queries
    queries = [
        "常庄水库防汛指挥部的指挥长是谁？",
        "防洪预案中包含哪些物资保障措施？",
        "谁负责堤防的巡查工作？",
        "启动防洪预案的条件是什么？"
    ]

    print("\n" + "="*60)
    print("开始测试检索...")
    print("="*60 + "\n")

    # Use Retriever (Retrieves relevant triplets/text)
    # 方式 A: 混合检索 (Entity Matching + Vector)
    retriever = kg_index.as_retriever(
        include_text=True, # 包含原始文本块
        retriever_mode="hybrid", # 混合检索实体和文本
        similarity_top_k=5
    )

    for q in queries:
        print(f"❓ 问题: {q}")
        response = retriever.retrieve(q)
        
        print(f"🔍 检索到的节点数: {len(response)}")
        for i, node in enumerate(response[:3]): # Show top 3
            print(f"   [{i+1}] Score: {node.score:.3f}")
            # KG 节点通常包含三元组信息字符串
            content = node.text.replace('\n', ' ')[:150]
            print(f"       {content}...")
        print("-" * 50)
        
    print("\n✅ 测试完成")

if __name__ == "__main__":
    test_kg_retrieval()
