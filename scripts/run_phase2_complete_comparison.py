"""
Phase 2 完整三组对比实验
对比 Baseline (无上下文) vs CR (有上下文) vs KG (知识图谱)
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

from llama_index.core import VectorStoreIndex, QueryBundle
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.retrievers.bm25 import BM25Retriever
from llama_index.core.retrievers import BaseRetriever
from llama_index.core.schema import NodeWithScore
import chromadb
import jieba
from typing import List

load_dotenv()

# 测试问题集
TEST_QUERIES = [
    {"query": "杨家横水库的汛限水位是多少？", "category": "数值查询"},
    {"query": "防洪预案中的应急预案等级有哪些？", "category": "分级查询"},
    {"query": "堤防巡查的标准是什么？", "category": "标准规范"},
    {"query": "汛期调度的规则是什么？", "category": "规则流程"},
    {"query": "防洪抢险有哪些措施？", "category": "措施清单"},
    {"query": "水位超过多少需要启动预案？", "category": "触发条件"},
    {"query": "谁负责防洪指挥调度？", "category": "责任人查询"},
    {"query": "水库大坝出现险情时应该联系谁？", "category": "多跳推理"},
]

def chinese_tokenizer(text):
    return list(jieba.cut_for_search(text))

class HybridRetriever(BaseRetriever):
    def __init__(self, vector_retriever, bm25_retriever):
        self.vector_retriever = vector_retriever
        self.bm25_retriever = bm25_retriever
        super().__init__()

    def _retrieve(self, query_bundle: QueryBundle) -> List[NodeWithScore]:
        vector_results = self.vector_retriever.retrieve(query_bundle) if self.vector_retriever else []
        bm25_results = self.bm25_retriever.retrieve(query_bundle) if self.bm25_retriever else []
        
        all_nodes = {node.node_id: node for node in vector_results + bm25_results}
        sorted_nodes = sorted(all_nodes.values(), key=lambda x: x.score if x.score else 0, reverse=True)
        return sorted_nodes[:10]

def init_retriever(db_path, bm25_path, collection_name):
    """初始化检索器"""
    embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-zh-v1.5", device="cpu")
    
    if not os.path.exists(db_path):
        return None
    
    db = chromadb.PersistentClient(path=db_path)
    try:
        chroma_collection = db.get_collection(collection_name)
    except:
        return None
    
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
    vector_index = VectorStoreIndex.from_vector_store(vector_store, embed_model=embed_model)
    vector_retriever = vector_index.as_retriever(similarity_top_k=10)
    
    bm25_retriever = None
    if os.path.exists(bm25_path):
        bm25_retriever = BM25Retriever.from_persist_dir(bm25_path)
        bm25_retriever._similarity_top_k = 10
    
    return HybridRetriever(vector_retriever, bm25_retriever)

def run_experiment(experiment_name, db_path, bm25_path, collection_name):
    """运行单个实验"""
    print(f"\n{'='*60}")
    print(f"运行实验: {experiment_name}")
    print(f"{'='*60}\n")
    
    retriever = init_retriever(db_path, bm25_path, collection_name)
    if not retriever:
        print(f"❌ 无法初始化检索器，请检查数据库路径")
        return None
    
    results = []
    for item in TEST_QUERIES:
        query = item["query"]
        print(f"查询: {query}")
        
        try:
            start = time.time()
            nodes = retriever.retrieve(QueryBundle(query))
            elapsed = time.time() - start
            
            top_result = {
                "query": query,
                "category": item["category"],
                "time": elapsed,
                "top_1_preview": nodes[0].text[:200] if nodes else "无结果",
                "top_1_score": nodes[0].score if nodes else 0,
                "results_count": len(nodes)
            }
            results.append(top_result)
            print(f"  ✅ 耗时: {elapsed:.2f}s, Top-1 Score: {top_result['top_1_score']:.3f}")
            print(f"  预览: {top_result['top_1_preview'][:100]}...")
        except Exception as e:
            print(f"  ❌ 错误: {e}")
            results.append({
                "query": query,
                "category": item["category"],
                "error": str(e)
            })
    
    return results

def main():
    # 实验配置
    experiments = {
        "Baseline": {
            "db_path": "./src/db/flood_prevention_db_baseline_vectordb",
            "bm25_path": "./src/db/flood_prevention_db_baseline_bm25",
            "collection": "flood_prevention_collection"
        },
        "CR_Enhanced": {
            "db_path": "./src/db/flood_prevention_db_vectordb",
            "bm25_path": "./src/db/flood_prevention_db_bm25",
            "collection": "flood_prevention_collection"
        }
    }
    
    all_results = {}
    
    for exp_name, config in experiments.items():
        results = run_experiment(exp_name, config["db_path"], config["bm25_path"], config["collection"])
        if results:
            all_results[exp_name] = results
    
    # 生成对比报告
    if len(all_results) >= 2:
        generate_comparison_report(all_results)
    
    print("\n✅ 实验完成！")

def generate_comparison_report(all_results):
    """生成 Markdown 对比报告"""
    report_path = Path("results/phase2_complete_comparison.md")
    
    md = "# Phase 2: 三组实验完整对比报告\n\n"
    md += "## 实验配置\n\n"
    md += "| 实验 | 说明 |\n"
    md += "|---|---|\n"
    md += "| Baseline | 纯向量+BM25，无上下文增强 |\n"
    md += "| CR Enhanced | LLM生成上下文前缀后检索 |\n"
    md += "| Knowledge Graph | 知识图谱推理（待补充）|\n\n"
    
    md += "## 逐题对比\n\n"
    
    # 获取所有查询
    queries = [item["query"] for item in all_results[list(all_results.keys())[0]]]
    
    for i, query in enumerate(queries):
        md += f"### Q{i+1}: {query}\n\n"
        md += "| 实验 | Top-1 预览 | 得分 | 耗时(s) |\n"
        md += "|---|---|---|---|\n"
        
        for exp_name, results in all_results.items():
            item = results[i]
            preview = item.get("top_1_preview", "N/A")[:100].replace('|', '\\|')
            score = item.get("top_1_score", 0)
            elapsed = item.get("time", 0)
            md += f"| {exp_name} | {preview}... | {score:.3f} | {elapsed:.2f} |\n"
        
        md += "\n"
    
    report_path.write_text(md, encoding='utf-8')
    print(f"\n📊 对比报告已保存: {report_path}")

if __name__ == "__main__":
    main()
