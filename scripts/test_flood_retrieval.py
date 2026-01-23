"""
防洪预案检索测试 - 无需LLM，只测试向量+BM25混合检索
"""
import os
import sys
import time
import json
from pathlib import Path

# 修复Windows编码问题
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from dotenv import load_dotenv

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parents[1]))

from llama_index.core import VectorStoreIndex
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.retrievers.bm25 import BM25Retriever
from llama_index.core import QueryBundle
from llama_index.core.retrievers import BaseRetriever
from llama_index.core.schema import NodeWithScore
import chromadb
import jieba
from typing import List

load_dotenv()

# ===== 配置 =====
DB_PATH = os.getenv("VECTOR_DB_PATH", "./src/db/flood_prevention_db_vectordb")
BM25_PATH = os.getenv("BM25_DB_PATH", "./src/db/flood_prevention_db_bm25")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "flood_prevention_collection")

# 中文分词器
def chinese_tokenizer(text):
    return list(jieba.cut_for_search(text))

# ===== 混合检索器 =====
class HybridRetriever(BaseRetriever):
    def __init__(self, vector_retriever, bm25_retriever):
        self.vector_retriever = vector_retriever
        self.bm25_retriever = bm25_retriever
        super().__init__()

    def _retrieve(self, query_bundle: QueryBundle) -> List[NodeWithScore]:
        # 向量检索
        vector_results = self.vector_retriever.retrieve(query_bundle)
        # BM25检索
        bm25_results = self.bm25_retriever.retrieve(query_bundle)
        
        # 合并并去重
        all_nodes = {node.node_id: node for node in vector_results + bm25_results}
        
        # 按得分排序
        sorted_nodes = sorted(
            all_nodes.values(), 
            key=lambda x: x.score if x.score else 0, 
            reverse=True
        )
        
        return sorted_nodes[:10]  # 返回Top 10

# ===== 测试问题 =====
TEST_QUESTIONS = [
    # 关键词检索
    ("杨家横水库的汛限水位是多少？", "水位相关"),
    ("防洪预案中的应急预案等级有哪些？", "等级分级"),
    ("堤防巡查的标准是什么？", "巡查标准"),
    ("汛期调度的规则是什么？", "调度规则"),
    ("九孔闸的作用是什么？", "工程设施"),
    ("防洪抢险有哪些措施？", "抢险措施"),
    ("水位超过多少需要启动预案？", "触发条件"),
    ("常庄水库的管理制度有哪些？", "管理制度"),
]

# ===== 初始化 =====
def init_retrievers():
    print("=" * 80)
    print("初始化检索器...")
    print("=" * 80)
    
    # 初始化Embedding模型
    embed_model = HuggingFaceEmbedding(
        model_name="BAAI/bge-small-zh-v1.5",
        device="cpu"
    )
    
    # 初始化向量数据库
    db = chromadb.PersistentClient(path=DB_PATH)
    chroma_collection = db.get_collection(COLLECTION_NAME)
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
    vector_index = VectorStoreIndex.from_vector_store(vector_store, embed_model=embed_model)
    vector_retriever = vector_index.as_retriever(similarity_top_k=10)
    
    # 初始化BM25检索器
    bm25_retriever = BM25Retriever.from_persist_dir(BM25_PATH)
    bm25_retriever._similarity_top_k = 10
    
    # 混合检索器
    hybrid_retriever = HybridRetriever(vector_retriever, bm25_retriever)
    
    print("✅ 检索器初始化成功")
    print(f"   - 向量模型: bge-small-zh-v1.5")
    print(f"   - BM25索引: {BM25_PATH}")
    print(f"   - 向量库: {DB_PATH}")
    print()
    
    return hybrid_retriever

# ===== 执行检索 =====
def run_retrieval_test(retriever):
    print("=" * 80)
    print("执行检索测试")
    print("=" * 80)
    print()
    
    results = []
    
    for query, category in TEST_QUESTIONS:
        print(f"【{category}】{query}")
        print("-" * 60)
        
        start_time = time.time()
        query_bundle = QueryBundle(query_str=query)
        
        try:
            retrieved_nodes = retriever.retrieve(query_bundle)
            elapsed = time.time() - start_time
            
            print(f"✅ 检索成功 ({len(retrieved_nodes)} 结果，耗时 {elapsed:.2f}s)")
            print()
            
            # 显示Top 3结果
            for i, node in enumerate(retrieved_nodes[:3], 1):
                score = node.score if node.score else 0
                filename = node.metadata.get('file_name', 'unknown')
                preview = node.text[:100].replace('\n', ' ')
                print(f"   {i}. [{score:.3f}] {filename}")
                print(f"      {preview}...")
            
            print()
            
            results.append({
                "query": query,
                "category": category,
                "success": True,
                "results_count": len(retrieved_nodes),
                "time": elapsed,
                "top_3": [
                    {
                        "score": (n.score if n.score else 0),
                        "file": n.metadata.get('file_name', 'unknown'),
                        "text": n.text[:100]
                    }
                    for n in retrieved_nodes[:3]
                ]
            })
            
        except Exception as e:
            print(f"❌ 检索失败: {e}")
            print()
            results.append({
                "query": query,
                "category": category,
                "success": False,
                "error": str(e)
            })
    
    return results

# ===== 生成报告 =====
def generate_report(results):
    print("=" * 80)
    print("检索结果统计")
    print("=" * 80)
    print()
    
    success_count = sum(1 for r in results if r.get("success", False))
    total_count = len(results)
    avg_time = sum(r.get("time", 0) for r in results if r.get("success")) / max(success_count, 1)
    
    print(f"总查询数: {total_count}")
    print(f"成功检索: {success_count}/{total_count}")
    print(f"平均耗时: {avg_time:.2f}s")
    print()
    
    # 按分类统计
    categories = {}
    for r in results:
        cat = r.get("category", "其他")
        if cat not in categories:
            categories[cat] = {"total": 0, "success": 0}
        categories[cat]["total"] += 1
        if r.get("success"):
            categories[cat]["success"] += 1
    
    print("按分类统计:")
    for cat, stats in categories.items():
        success_rate = (stats["success"] / stats["total"] * 100) if stats["total"] > 0 else 0
        print(f"  {cat}: {stats['success']}/{stats['total']} ({success_rate:.0f}%)")
    
    print()
    
    # 保存JSON报告
    report_file = Path(__file__).parent.parent / "results" / "flood_retrieval_report.json"
    report_file.parent.mkdir(parents=True, exist_ok=True)
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 详细报告已保存: {report_file}")

# ===== 主函数 =====
def main():
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "防洪预案混合检索测试" + " " * 40 + "║")
    print("║" + " " * 15 + "（无需LLM，纯向量+BM25检索）" + " " * 35 + "║")
    print("╚" + "=" * 78 + "╝")
    print()
    
    try:
        # 初始化
        retriever = init_retrievers()
        
        # 运行测试
        results = run_retrieval_test(retriever)
        
        # 生成报告
        generate_report(results)
        
        print("\n✅ 测试完成！\n")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
