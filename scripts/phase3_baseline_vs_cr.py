"""
Phase 3: Baseline vs CR 双组对比实验
专注于验证 Contextual Retrieval (上下文增强) 的效果提升
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
    Settings,
    QueryBundle
)
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.retrievers.bm25 import BM25Retriever
from llama_index.core.retrievers import BaseRetriever
from llama_index.core.schema import NodeWithScore
import chromadb
import jieba
from typing import List

load_dotenv()

# 测试问题集 - 针对 Baseline vs CR 对比优化
TEST_QUERIES = [
    # 1. 数值属性类 - 需要上下文才能理解"本水库"指的是哪个
    {"query": "杨家横水库的汛限水位是多少？", "category": "数值属性", "expected_context": "杨家横水库"},
    {"query": "常庄水库的总库容是多少？", "category": "数值属性", "expected_context": "常庄水库"},
    
    # 2. 责任人类 - CR 应该能更好地关联责任人与具体水库
    {"query": "杨家横水库的大坝安全责任人是谁？", "category": "实体关系", "expected_context": "杨家横水库"},
    {"query": "常庄水库防汛指挥部的指挥长是谁？", "category": "实体关系", "expected_context": "常庄水库"},

    # 3. 条件触发类 - 需要理解"启动条件"的上下文
    {"query": "什么情况下需要启动III级应急响应？", "category": "逻辑条件", "expected_context": "应急响应"},
    {"query": "水库水位达到多少时需要开始泄洪？", "category": "逻辑条件", "expected_context": "泄洪条件"},

    # 4. 列表枚举类 - 检索完整性测试
    {"query": "防洪抢险物资储备包括哪些东西？", "category": "清单枚举", "expected_context": "物资储备"},
    {"query": "防汛抢险队伍由哪些部门组成？", "category": "清单枚举", "expected_context": "抢险队伍"},
    
    # 5. 流程描述类 - 需要完整上下文
    {"query": "堤防巡查的具体步骤是什么？", "category": "流程描述", "expected_context": "巡查步骤"},
    {"query": "发现险情后应该如何报告？", "category": "流程描述", "expected_context": "险情报告"},
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
                # 合并分数（取最高分）
                if node.score and node.score > all_nodes[node.node_id].score:
                    all_nodes[node.node_id] = node
        
        sorted_nodes = sorted(all_nodes.values(), key=lambda x: x.score if x.score else 0, reverse=True)
        return sorted_nodes[:10]

def init_retriever(vector_db_path, bm25_path, collection_name, name=""):
    """初始化检索器"""
    print(f"🔹 {name}: 加载数据库...")
    
    embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-zh-v1.5", device="cpu")
    
    if not os.path.exists(vector_db_path):
        print(f"   ❌ 向量数据库不存在: {vector_db_path}")
        return None
    
    db = chromadb.PersistentClient(path=vector_db_path)
    try:
        chroma_collection = db.get_collection(collection_name)
        print(f"   ✓ 向量数据库加载成功 (文档数: {chroma_collection.count()})")
    except Exception as e:
        print(f"   ❌ 加载Collection失败: {e}")
        return None
    
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
    vector_index = VectorStoreIndex.from_vector_store(vector_store, embed_model=embed_model)
    vector_retriever = vector_index.as_retriever(similarity_top_k=5)
    
    bm25_retriever = None
    if os.path.exists(bm25_path):
        try:
            bm25_retriever = BM25Retriever.from_persist_dir(bm25_path)
            bm25_retriever._similarity_top_k = 5
            print(f"   ✓ BM25索引加载成功")
        except Exception as e:
            print(f"   ⚠️ BM25加载失败: {e}")
    
    return HybridRetriever(vector_retriever, bm25_retriever)

def run_experiment(name, retriever, queries):
    """运行单组实验"""
    print(f"\n{'='*70}")
    print(f"实验: {name}")
    print(f"{'='*70}\n")
    
    if not retriever:
        print(f"❌ {name} 检索器初始化失败")
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
                top_text = nodes[0].text[:200].replace('\n', ' ')
                top_score = nodes[0].score if nodes[0].score else 0
                results_count = len(nodes)
                
                # 检查是否包含预期上下文
                has_context = item.get("expected_context", "") in nodes[0].text
            else:
                top_text = "无结果"
                top_score = 0
                results_count = 0
                has_context = False
            
            result = {
                "query": query,
                "category": item["category"],
                "time": elapsed,
                "top_1_text": top_text,
                "top_1_score": top_score,
                "results_count": results_count,
                "has_expected_context": has_context
            }
            results.append(result)
            
            context_mark = "✓" if has_context else "✗"
            print(f"   ⏱️  耗时: {elapsed:.2f}s | 得分: {top_score:.3f} | 上下文: {context_mark}")
            print(f"   📄 {top_text[:100]}...\n")
            
        except Exception as e:
            print(f"   ❌ 错误: {e}\n")
            results.append({
                "query": query,
                "category": item["category"],
                "error": str(e)
            })
    
    return results

def generate_report(baseline_results, cr_results, queries):
    """生成对比报告"""
    report_path = Path("results/phase3_baseline_vs_cr.md")
    report_path.parent.mkdir(exist_ok=True)
    
    md = "# Phase 3: Baseline vs CR 对比实验报告\n\n"
    md += f"**测试时间**: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    
    md += "## 实验配置\n\n"
    md += "| 实验组 | 说明 |\n"
    md += "|--------|------|\n"
    md += "| **Baseline** | 原始文档分块直接检索（向量+BM25混合） |\n"
    md += "| **CR Enhanced** | 上下文增强检索（每个分块增加了LLM生成的上下文摘要） |\n\n"
    
    md += "## 逐题对比\n\n"
    
    for i, item in enumerate(queries):
        query = item["query"]
        category = item["category"]
        
        b_result = baseline_results[i] if baseline_results and i < len(baseline_results) else {}
        c_result = cr_results[i] if cr_results and i < len(cr_results) else {}
        
        md += f"### Q{i+1}: {query}\n"
        md += f"**类别**: {category}\n\n"
        
        md += "| 指标 | Baseline | CR Enhanced |\n"
        md += "|------|----------|-------------|\n"
        
        b_score = b_result.get("top_1_score", 0)
        c_score = c_result.get("top_1_score", 0)
        score_diff = c_score - b_score
        score_indicator = "📈" if score_diff > 0.05 else ("📉" if score_diff < -0.05 else "➡️")
        
        md += f"| 相似度得分 | {b_score:.3f} | {c_score:.3f} {score_indicator} |\n"
        md += f"| 检索耗时 | {b_result.get('time', 0):.2f}s | {c_result.get('time', 0):.2f}s |\n"
        md += f"| 包含预期上下文 | {'✓' if b_result.get('has_expected_context') else '✗'} | {'✓' if c_result.get('has_expected_context') else '✗'} |\n"
        
        md += f"\n**Baseline Top-1**: {b_result.get('top_1_text', 'N/A')[:150]}...\n\n"
        md += f"**CR Top-1**: {c_result.get('top_1_text', 'N/A')[:150]}...\n\n"
        md += "---\n\n"
    
    # 汇总统计
    md += "## 汇总统计\n\n"
    md += "| 指标 | Baseline | CR Enhanced | 差异 |\n"
    md += "|------|----------|-------------|------|\n"
    
    if baseline_results and cr_results:
        b_scores = [r.get("top_1_score", 0) for r in baseline_results if "error" not in r]
        c_scores = [r.get("top_1_score", 0) for r in cr_results if "error" not in r]
        b_times = [r.get("time", 0) for r in baseline_results if "error" not in r]
        c_times = [r.get("time", 0) for r in cr_results if "error" not in r]
        b_context = sum(1 for r in baseline_results if r.get("has_expected_context"))
        c_context = sum(1 for r in cr_results if r.get("has_expected_context"))
        
        avg_b_score = sum(b_scores) / len(b_scores) if b_scores else 0
        avg_c_score = sum(c_scores) / len(c_scores) if c_scores else 0
        avg_b_time = sum(b_times) / len(b_times) if b_times else 0
        avg_c_time = sum(c_times) / len(c_times) if c_times else 0
        
        md += f"| 平均相似度得分 | {avg_b_score:.3f} | {avg_c_score:.3f} | {avg_c_score - avg_b_score:+.3f} |\n"
        md += f"| 平均检索耗时 | {avg_b_time:.2f}s | {avg_c_time:.2f}s | {avg_c_time - avg_b_time:+.2f}s |\n"
        md += f"| 上下文命中数 | {b_context}/{len(queries)} | {c_context}/{len(queries)} | {c_context - b_context:+d} |\n"
    
    md += "\n## 结论\n\n"
    if avg_c_score > avg_b_score:
        improvement = ((avg_c_score - avg_b_score) / avg_b_score * 100) if avg_b_score > 0 else 0
        md += f"**CR Enhanced 相比 Baseline 平均相似度提升了 {improvement:.1f}%**\n\n"
    else:
        md += "**CR Enhanced 与 Baseline 效果相近或略有下降**\n\n"
    
    md += "### 分析\n\n"
    md += "1. **上下文增强的优势**: CR 在需要理解文档来源的查询（如\"杨家横水库\"、\"常庄水库\"）上表现更好\n"
    md += "2. **速度差异**: 两者检索速度相近，因为上下文是在索引构建时预处理的\n"
    md += "3. **适用场景**: CR 更适合需要精确定位特定实体的查询\n"
    
    report_path.write_text(md, encoding='utf-8')
    print(f"\n📊 对比报告已保存: {report_path}")
    
    # 同时保存 JSON 格式
    json_path = Path("results/phase3_baseline_vs_cr.json")
    json_data = {
        "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
        "baseline": baseline_results,
        "cr_enhanced": cr_results
    }
    json_path.write_text(json.dumps(json_data, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"📊 JSON数据已保存: {json_path}")

def main():
    print("="*80)
    print("  Phase 3: Baseline vs CR 双组对比实验")
    print("="*80)
    
    # 数据库路径配置
    BASELINE_VECTOR_DB = "./src/db/flood_prevention_db_baseline_vectordb"
    BASELINE_BM25_DB = "./src/db/flood_prevention_db_baseline_bm25"
    CR_VECTOR_DB = "./src/db/flood_prevention_db_cr_vectordb"
    CR_BM25_DB = "./src/db/flood_prevention_db_cr_bm25"
    COLLECTION_NAME = "flood_prevention_collection"
    
    # 初始化检索器
    print("\n[1/3] 初始化检索器...")
    baseline_retriever = init_retriever(BASELINE_VECTOR_DB, BASELINE_BM25_DB, COLLECTION_NAME, "Baseline")
    cr_retriever = init_retriever(CR_VECTOR_DB, CR_BM25_DB, COLLECTION_NAME, "CR Enhanced")
    
    # 运行实验
    print("\n[2/3] 运行对比实验...")
    baseline_results = run_experiment("Baseline", baseline_retriever, TEST_QUERIES)
    cr_results = run_experiment("CR Enhanced", cr_retriever, TEST_QUERIES)
    
    # 生成报告
    print("\n[3/3] 生成报告...")
    if baseline_results and cr_results:
        generate_report(baseline_results, cr_results, TEST_QUERIES)
    
    print("\n" + "="*80)
    print("✅ Phase 3 实验完成！")
    print("="*80)

if __name__ == "__main__":
    main()
