"""
Phase 2 三组实验完整对比
- Baseline: 原始文档直接检索（不预构建数据库）
- CR: 上下文增强检索（使用预构建的CR数据库）
- KG: 知识图谱推理检索（使用预构建的KG）
"""
import os
import sys
import json
import time
from pathlib import Path

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from dotenv import load_dotenv
sys.path.insert(0, str(Path(__file__).parents[1]))

from llama_index.core import (
    VectorStoreIndex, 
    SimpleDirectoryReader,
    StorageContext,
    load_index_from_storage,
    Settings,
    QueryBundle
)
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.retrievers.bm25 import BM25Retriever
from llama_index.core.retrievers import BaseRetriever
from llama_index.core.schema import NodeWithScore
from llama_index.llms.ollama import Ollama
import chromadb
import jieba
from typing import List

load_dotenv()

# 测试问题集（扩展版，增加不同类型）
TEST_QUERIES = [
    {"query": "杨家横水库的汛限水位是多少？", "category": "数值查询", "type": "简单事实"},
    {"query": "防洪预案中的应急预案等级有哪些？", "category": "分级查询", "type": "枚举列表"},
    {"query": "堤防巡查的标准是什么？", "category": "标准规范", "type": "规则描述"},
    {"query": "汛期调度的规则是什么？", "category": "规则流程", "type": "流程说明"},
    {"query": "防洪抢险有哪些措施？", "category": "措施清单", "type": "枚举列表"},
    {"query": "水位超过多少需要启动预案？", "category": "触发条件", "type": "条件判断"},
    {"query": "谁负责防洪指挥调度？", "category": "责任人查询", "type": "实体查询"},
    {"query": "水库大坝出现险情时应该联系谁？", "category": "应急联系", "type": "多跳推理"},
]

def chinese_tokenizer(text):
    """中文分词器"""
    return list(jieba.cut_for_search(text))

class HybridRetriever(BaseRetriever):
    """混合检索器（向量+BM25）"""
    def __init__(self, vector_retriever, bm25_retriever):
        self.vector_retriever = vector_retriever
        self.bm25_retriever = bm25_retriever
        super().__init__()

    def _retrieve(self, query_bundle: QueryBundle) -> List[NodeWithScore]:
        vector_results = self.vector_retriever.retrieve(query_bundle) if self.vector_retriever else []
        bm25_results = self.bm25_retriever.retrieve(query_bundle) if self.bm25_retriever else []
        
        all_nodes = {}
        for node in vector_results + bm25_results:
            if node.node_id not in all_nodes:
                all_nodes[node.node_id] = node
            else:
                # 合并分数（简单平均）
                all_nodes[node.node_id].score = (all_nodes[node.node_id].score + node.score) / 2
        
        sorted_nodes = sorted(all_nodes.values(), key=lambda x: x.score if x.score else 0, reverse=True)
        return sorted_nodes[:10]

def init_baseline_retriever(data_dir):
    """初始化Baseline检索器 - 直接从原始文档构建"""
    print("🔹 Baseline: 从原始文档构建临时索引...")
    
    embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-zh-v1.5", device="cpu")
    
    # 读取原始文档
    documents = SimpleDirectoryReader(data_dir).load_data()
    print(f"   加载了 {len(documents)} 个文档")
    
    # 构建向量索引
    vector_index = VectorStoreIndex.from_documents(documents, embed_model=embed_model)
    vector_retriever = vector_index.as_retriever(similarity_top_k=5)
    
    # 构建BM25索引
    nodes = vector_index.docstore.docs.values()
    bm25_retriever = BM25Retriever.from_defaults(
        nodes=list(nodes),
        similarity_top_k=5,
        tokenizer=chinese_tokenizer
    )
    
    return HybridRetriever(vector_retriever, bm25_retriever)

def init_cr_retriever(db_path, bm25_path, collection_name):
    """初始化CR检索器 - 从预构建的数据库加载"""
    print("🔹 CR Enhanced: 从预构建数据库加载...")
    
    embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-zh-v1.5", device="cpu")
    
    if not os.path.exists(db_path):
        print(f"   ❌ 数据库不存在: {db_path}")
        return None
    
    db = chromadb.PersistentClient(path=db_path)
    try:
        chroma_collection = db.get_collection(collection_name)
    except:
        print(f"   ❌ Collection 不存在: {collection_name}")
        return None
    
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
    vector_index = VectorStoreIndex.from_vector_store(vector_store, embed_model=embed_model)
    vector_retriever = vector_index.as_retriever(similarity_top_k=5)
    
    bm25_retriever = None
    if os.path.exists(bm25_path):
        bm25_retriever = BM25Retriever.from_persist_dir(bm25_path)
        bm25_retriever._similarity_top_k = 5
    
    return HybridRetriever(vector_retriever, bm25_retriever)

def init_kg_retriever(kg_dir):
    """初始化KG检索器"""
    print("🔹 Knowledge Graph: 从预构建图谱加载...")
    
    if not os.path.exists(kg_dir):
        print(f"   ❌ KG目录不存在: {kg_dir}")
        return None
    
    llm = Ollama(model="gemma3:12b", request_timeout=120.0)
    embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-zh-v1.5", device="cpu")
    Settings.llm = llm
    Settings.embed_model = embed_model
    
    storage_context = StorageContext.from_defaults(persist_dir=kg_dir)
    kg_index = load_index_from_storage(storage_context)
    
    # 使用混合模式检索（实体匹配+向量）
    retriever = kg_index.as_retriever(
        include_text=True,
        retriever_mode="hybrid",
        similarity_top_k=5
    )
    
    return retriever

def run_single_experiment(experiment_name, retriever, queries):
    """运行单个实验"""
    print(f"\n{'='*70}")
    print(f"实验: {experiment_name}")
    print(f"{'='*70}\n")
    
    if not retriever:
        print(f"❌ {experiment_name} 检索器初始化失败")
        return None
    
    results = []
    for item in queries:
        query = item["query"]
        print(f"🔍 {query}")
        
        try:
            start = time.time()
            nodes = retriever.retrieve(QueryBundle(query))
            elapsed = time.time() - start
            
            if nodes and len(nodes) > 0:
                top_text = nodes[0].text[:150].replace('\n', ' ')
                top_score = nodes[0].score if nodes[0].score else 0
                results_count = len(nodes)
            else:
                top_text = "无结果"
                top_score = 0
                results_count = 0
            
            result = {
                "query": query,
                "category": item["category"],
                "type": item["type"],
                "time": elapsed,
                "top_1_text": top_text,
                "top_1_score": top_score,
                "results_count": results_count
            }
            results.append(result)
            
            print(f"   ⏱️  耗时: {elapsed:.2f}s | 得分: {top_score:.3f} | 结果数: {results_count}")
            print(f"   📄 {top_text}...\n")
            
        except Exception as e:
            print(f"   ❌ 错误: {e}\n")
            results.append({
                "query": query,
                "category": item["category"],
                "type": item["type"],
                "error": str(e)
            })
    
    return results

def generate_markdown_report(all_results, queries):
    """生成Markdown对比报告"""
    report_path = Path("results/phase2_complete_comparison.md")
    
    md = "# Phase 2: 完整三组实验对比分析\n\n"
    md += f"**测试时间**: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    
    md += "## 实验配置\n\n"
    md += "| 实验组 | 说明 | 数据来源 |\n"
    md += "|--------|------|----------|\n"
    md += "| **Baseline** | 原始文档直接检索（向量+BM25） | 临时构建，无LLM增强 |\n"
    md += "| **CR Enhanced** | 上下文增强检索 | 预构建数据库，含LLM生成的上下文 |\n"
    md += "| **Knowledge Graph** | 知识图谱推理检索 | 预构建KG，三元组+实体关系 |\n\n"
    
    md += "## 测试问题分类\n\n"
    md += "| 类型 | 数量 | 说明 |\n"
    md += "|------|------|------|\n"
    types = {}
    for q in queries:
        t = q["type"]
        types[t] = types.get(t, 0) + 1
    for t, count in types.items():
        md += f"| {t} | {count} | - |\n"
    md += "\n"
    
    md += "## 逐题详细对比\n\n"
    
    for i, q_item in enumerate(queries):
        query = q_item["query"]
        md += f"### Q{i+1}: {query}\n\n"
        md += f"**类型**: {q_item['type']} | **分类**: {q_item['category']}\n\n"
        
        md += "| 实验 | Top-1 得分 | 耗时(s) | Top-1 预览 |\n"
        md += "|------|-----------|---------|------------|\n"
        
        for exp_name in ["Baseline", "CR_Enhanced", "KG"]:
            if exp_name in all_results:
                result = all_results[exp_name][i]
                score = result.get("top_1_score", 0)
                elapsed = result.get("time", 0)
                preview = result.get("top_1_text", "N/A")[:80].replace('|', '\\|')
                md += f"| {exp_name} | {score:.3f} | {elapsed:.2f} | {preview}... |\n"
        
        md += "\n"
    
    md += "## 性能统计\n\n"
    md += "| 实验 | 平均耗时(s) | 平均得分 | 无结果数 |\n"
    md += "|------|------------|----------|----------|\n"
    
    for exp_name, results in all_results.items():
        times = [r.get("time", 0) for r in results if "error" not in r]
        scores = [r.get("top_1_score", 0) for r in results if "error" not in r]
        no_results = sum(1 for r in results if r.get("results_count", 0) == 0)
        
        avg_time = sum(times) / len(times) if times else 0
        avg_score = sum(scores) / len(scores) if scores else 0
        
        md += f"| {exp_name} | {avg_time:.2f} | {avg_score:.3f} | {no_results} |\n"
    
    md += "\n## 结论\n\n"
    md += "_待补充：基于上述数据的定性分析_\n\n"
    
    report_path.write_text(md, encoding='utf-8')
    print(f"\n📊 完整对比报告已保存: {report_path}")

def main():
    print("="*80)
    print("  Phase 2: 三组实验完整对比")
    print("="*80)
    
    # 配置
    DATA_DIR = os.getenv("DATA_DIR", "./data/防洪预案")
    CR_VECTOR_DB = "./src/db/flood_prevention_db_cr_vectordb"
    CR_BM25_DB = "./src/db/flood_prevention_db_cr_bm25"
    KG_DIR = "./src/db/knowledge_graph"
    COLLECTION_NAME = "flood_prevention_collection"
    
    # 初始化检索器
    baseline_retriever = init_baseline_retriever(DATA_DIR)
    cr_retriever = init_cr_retriever(CR_VECTOR_DB, CR_BM25_DB, COLLECTION_NAME)
    kg_retriever = init_kg_retriever(KG_DIR)
    
    all_results = {}
    
    # 运行实验
    if baseline_retriever:
        all_results["Baseline"] = run_single_experiment("Baseline", baseline_retriever, TEST_QUERIES)
    
    if cr_retriever:
        all_results["CR_Enhanced"] = run_single_experiment("CR Enhanced", cr_retriever, TEST_QUERIES)
    
    if kg_retriever:
        all_results["KG"] = run_single_experiment("Knowledge Graph", kg_retriever, TEST_QUERIES)
    
    # 生成报告
    if all_results:
        generate_markdown_report(all_results, TEST_QUERIES)
    
    print("\n✅ 所有实验完成！")

if __name__ == "__main__":
    main()
