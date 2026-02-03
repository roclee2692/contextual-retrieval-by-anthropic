"""
Phase 3 验证实验：检查实验一致性 & Case 级别分析
目的：
1. 统一 top_k 设置
2. 打印 Baseline vs CR 检索文本对比
3. 人工抽查验证
"""
import os
import sys
import json
from pathlib import Path
from datetime import datetime

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
from typing import List
import numpy as np

load_dotenv()

# ============================================================================
# 配置：统一 top_k
# ============================================================================
VECTOR_TOP_K = 10  # 统一向量检索 top_k
BM25_TOP_K = 10    # 统一 BM25 检索 top_k
FINAL_TOP_K = 3    # 最终返回 top_k

# ============================================================================
# 测试问题（选取有代表性的10个）
# ============================================================================
TEST_QUERIES = [
    # A类：数值属性 (3个)
    {"id": "A01", "query": "杨家横水库的汛限水位是多少？", "category": "A-数值属性", 
     "keywords": ["汛限水位", "298", "水位"]},
    {"id": "A03", "query": "杨家横水库的校核洪水位是多少？", "category": "A-数值属性",
     "keywords": ["校核", "洪水位", "304"]},
    {"id": "A07", "query": "杨家横水库控制的流域面积是多少？", "category": "A-数值属性",
     "keywords": ["流域面积", "平方公里", "km"]},
    
    # B类：实体关系 (4个)
    {"id": "B01", "query": "杨家横水库的大坝安全责任人是谁？", "category": "B-实体关系",
     "keywords": ["责任人", "安全", "负责"]},
    {"id": "B03", "query": "杨家横水库由哪个单位管理？", "category": "B-实体关系",
     "keywords": ["管理", "单位", "处"]},
    {"id": "B05", "query": "杨家横水库位于哪条河流上？", "category": "B-实体关系",
     "keywords": ["河流", "位于", "河"]},
    {"id": "B06", "query": "常庄水库下游主要保护哪些区域？", "category": "B-实体关系",
     "keywords": ["下游", "保护", "区域"]},
    
    # C类：流程条件 (3个)
    {"id": "C01", "query": "什么情况下需要启动III级应急响应？", "category": "C-流程条件",
     "keywords": ["III级", "响应", "启动"]},
    {"id": "C03", "query": "防洪抢险物资储备包括哪些东西？", "category": "C-流程条件",
     "keywords": ["物资", "储备", "包括"]},
    {"id": "C05", "query": "堤防巡查的具体步骤是什么？", "category": "C-流程条件",
     "keywords": ["巡查", "步骤", "检查"]},
]

# ============================================================================
# 数据库路径
# ============================================================================
BASE_DIR = Path(__file__).parents[1]
DB_DIR = BASE_DIR / "src" / "db"

BASELINE_VECTOR_PATH = str(DB_DIR / "flood_prevention_db_baseline_vectordb")
BASELINE_BM25_PATH = str(DB_DIR / "flood_prevention_db_baseline_bm25")
CR_VECTOR_PATH = str(DB_DIR / "flood_prevention_db_cr_vectordb")
CR_BM25_PATH = str(DB_DIR / "flood_prevention_db_cr_bm25")

COLLECTION_NAME = "flood_prevention_collection"


class HybridRetriever(BaseRetriever):
    """混合检索器（向量+BM25），返回原始 nodes 用于分析"""
    def __init__(self, vector_retriever, bm25_retriever, top_k=10):
        self.vector_retriever = vector_retriever
        self.bm25_retriever = bm25_retriever
        self.top_k = top_k
        super().__init__()

    def _retrieve(self, query_bundle: QueryBundle) -> List[NodeWithScore]:
        vector_results = self.vector_retriever.retrieve(query_bundle) if self.vector_retriever else []
        bm25_results = self.bm25_retriever.retrieve(query_bundle) if self.bm25_retriever else []
        
        all_nodes = {}
        for node in vector_results + bm25_results:
            if node.node_id not in all_nodes:
                all_nodes[node.node_id] = node
            else:
                if node.score and node.score > all_nodes[node.node_id].score:
                    all_nodes[node.node_id] = node
        
        sorted_nodes = sorted(all_nodes.values(), key=lambda x: x.score if x.score else 0, reverse=True)
        return sorted_nodes[:self.top_k]


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
    vector_retriever = vector_index.as_retriever(similarity_top_k=VECTOR_TOP_K)
    
    bm25_retriever = None
    if os.path.exists(bm25_path):
        try:
            bm25_retriever = BM25Retriever.from_persist_dir(bm25_path)
            bm25_retriever._similarity_top_k = BM25_TOP_K
            print(f"   ✓ BM25索引加载成功")
        except Exception as e:
            print(f"   ⚠️ BM25加载失败: {e}")
    
    return HybridRetriever(vector_retriever, bm25_retriever, top_k=VECTOR_TOP_K + BM25_TOP_K)


def evaluate_keywords(text, keywords):
    """关键词命中评估"""
    hits = [kw for kw in keywords if kw in text]
    return len(hits) / len(keywords), hits


def run_case_analysis():
    """运行 Case 级别分析"""
    print("=" * 80)
    print("Phase 3 验证实验：Case 级别分析")
    print("=" * 80)
    print(f"\n🕐 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📝 验证问题数: {len(TEST_QUERIES)}")
    print(f"⚙️ 配置: VECTOR_TOP_K={VECTOR_TOP_K}, BM25_TOP_K={BM25_TOP_K}, FINAL_TOP_K={FINAL_TOP_K}")
    
    # 初始化检索器
    print("\n" + "=" * 80)
    print("步骤 1: 初始化检索器")
    print("=" * 80)
    
    baseline_retriever = init_retriever(
        BASELINE_VECTOR_PATH, BASELINE_BM25_PATH, COLLECTION_NAME, "Baseline"
    )
    cr_retriever = init_retriever(
        CR_VECTOR_PATH, CR_BM25_PATH, COLLECTION_NAME, "CR Enhanced"
    )
    
    if not baseline_retriever or not cr_retriever:
        print("❌ 检索器初始化失败，退出")
        return
    
    # Case 级别分析
    print("\n" + "=" * 80)
    print("步骤 2: Case 级别对比分析")
    print("=" * 80)
    
    case_results = []
    
    for item in TEST_QUERIES:
        qid = item["id"]
        query = item["query"]
        category = item["category"]
        keywords = item["keywords"]
        
        print(f"\n{'='*80}")
        print(f"📌 [{qid}] {query}")
        print(f"   类别: {category} | 关键词: {keywords}")
        print(f"{'='*80}")
        
        # Baseline 检索
        baseline_nodes = baseline_retriever.retrieve(query)[:FINAL_TOP_K]
        
        # CR 检索
        cr_nodes = cr_retriever.retrieve(query)[:FINAL_TOP_K]
        
        # 分析 Baseline
        print(f"\n🔵 Baseline 检索结果 (top-{FINAL_TOP_K}):")
        baseline_all_text = ""
        for i, node in enumerate(baseline_nodes):
            text = node.node.get_content()
            baseline_all_text += text + " "
            score = node.score if node.score else 0
            # 截取前200字符
            preview = text[:200].replace('\n', ' ')
            print(f"   [{i+1}] score={score:.4f}")
            print(f"       {preview}...")
        
        baseline_hit_rate, baseline_hits = evaluate_keywords(baseline_all_text, keywords)
        print(f"   📊 关键词命中: {baseline_hits} ({baseline_hit_rate*100:.0f}%)")
        
        # 分析 CR
        print(f"\n🟢 CR Enhanced 检索结果 (top-{FINAL_TOP_K}):")
        cr_all_text = ""
        for i, node in enumerate(cr_nodes):
            text = node.node.get_content()
            cr_all_text += text + " "
            score = node.score if node.score else 0
            # 截取前200字符
            preview = text[:200].replace('\n', ' ')
            print(f"   [{i+1}] score={score:.4f}")
            print(f"       {preview}...")
        
        cr_hit_rate, cr_hits = evaluate_keywords(cr_all_text, keywords)
        print(f"   📊 关键词命中: {cr_hits} ({cr_hit_rate*100:.0f}%)")
        
        # 对比分析
        print(f"\n📈 对比:")
        if cr_hit_rate > baseline_hit_rate:
            winner = "CR ✅"
        elif cr_hit_rate < baseline_hit_rate:
            winner = "Baseline ✅"
        else:
            winner = "平局"
        print(f"   Baseline: {baseline_hit_rate*100:.0f}% vs CR: {cr_hit_rate*100:.0f}% → {winner}")
        
        # 检查是否检索到相同的文档
        baseline_ids = set(n.node_id for n in baseline_nodes)
        cr_ids = set(n.node_id for n in cr_nodes)
        overlap = baseline_ids.intersection(cr_ids)
        print(f"   文档重叠: {len(overlap)}/{FINAL_TOP_K} ({len(overlap)/FINAL_TOP_K*100:.0f}%)")
        
        case_results.append({
            "id": qid,
            "query": query,
            "category": category,
            "baseline_score": baseline_nodes[0].score if baseline_nodes else 0,
            "cr_score": cr_nodes[0].score if cr_nodes else 0,
            "baseline_hit_rate": baseline_hit_rate,
            "cr_hit_rate": cr_hit_rate,
            "baseline_correct": baseline_hit_rate >= 0.5,
            "cr_correct": cr_hit_rate >= 0.5,
            "winner": winner,
            "doc_overlap": len(overlap) / FINAL_TOP_K
        })
    
    # ============================================================================
    # 汇总统计
    # ============================================================================
    print("\n" + "=" * 80)
    print("步骤 3: 汇总统计")
    print("=" * 80)
    
    baseline_correct = sum(1 for r in case_results if r["baseline_correct"])
    cr_correct = sum(1 for r in case_results if r["cr_correct"])
    baseline_wins = sum(1 for r in case_results if "Baseline" in r["winner"])
    cr_wins = sum(1 for r in case_results if "CR" in r["winner"])
    ties = sum(1 for r in case_results if "平局" in r["winner"])
    
    avg_baseline_score = np.mean([r["baseline_score"] for r in case_results])
    avg_cr_score = np.mean([r["cr_score"] for r in case_results])
    avg_overlap = np.mean([r["doc_overlap"] for r in case_results])
    
    print(f"""
┌──────────────────────────────────────────────────────────────┐
│                      验证实验汇总                              │
├──────────────────────────────────────────────────────────────┤
│  配置: VECTOR_TOP_K={VECTOR_TOP_K}, BM25_TOP_K={BM25_TOP_K}, FINAL_TOP_K={FINAL_TOP_K}
├──────────────────────────────────────────────────────────────┤
│                        检索正确率                              │
│  Baseline: {baseline_correct}/{len(case_results)} ({baseline_correct/len(case_results)*100:.1f}%)                                      
│  CR:       {cr_correct}/{len(case_results)} ({cr_correct/len(case_results)*100:.1f}%)                                      
├──────────────────────────────────────────────────────────────┤
│                        胜负统计                                │
│  Baseline 胜: {baseline_wins}                                              
│  CR 胜:       {cr_wins}                                              
│  平局:        {ties}                                              
├──────────────────────────────────────────────────────────────┤
│                        平均分数                                │
│  Baseline: {avg_baseline_score:.4f}                                        
│  CR:       {avg_cr_score:.4f}                                        
├──────────────────────────────────────────────────────────────┤
│                        文档重叠率                              │
│  平均: {avg_overlap*100:.1f}%                                              
└──────────────────────────────────────────────────────────────┘
""")
    
    # 分类统计
    print("\n📊 分类统计:")
    for cat in ["A-数值属性", "B-实体关系", "C-流程条件"]:
        cat_results = [r for r in case_results if r["category"] == cat]
        cat_baseline = sum(1 for r in cat_results if r["baseline_correct"])
        cat_cr = sum(1 for r in cat_results if r["cr_correct"])
        print(f"   {cat}: Baseline {cat_baseline}/{len(cat_results)}, CR {cat_cr}/{len(cat_results)}")
    
    # 保存结果
    results_dir = BASE_DIR / "results"
    results_dir.mkdir(exist_ok=True)
    
    output_path = results_dir / "phase3_case_analysis.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "config": {
                "vector_top_k": VECTOR_TOP_K,
                "bm25_top_k": BM25_TOP_K,
                "final_top_k": FINAL_TOP_K
            },
            "summary": {
                "baseline_accuracy": baseline_correct / len(case_results),
                "cr_accuracy": cr_correct / len(case_results),
                "baseline_wins": baseline_wins,
                "cr_wins": cr_wins,
                "ties": ties,
                "avg_doc_overlap": avg_overlap
            },
            "cases": case_results
        }, f, ensure_ascii=False, indent=2)
    print(f"\n✓ 结果已保存: {output_path}")
    
    # ============================================================================
    # 关键发现
    # ============================================================================
    print("\n" + "=" * 80)
    print("🔍 关键发现")
    print("=" * 80)
    
    if avg_overlap > 0.7:
        print("⚠️ Baseline 和 CR 检索到的文档高度重叠，说明 CR 上下文可能未显著改变检索结果")
    
    if baseline_correct > cr_correct:
        print("⚠️ Baseline 正确率 > CR 正确率，可能原因：")
        print("   1. CR 上下文引入了噪音")
        print("   2. 关键词评估指标本身有偏差")
        print("   3. 数据特性不适合 CR")
    
    if avg_baseline_score < 0.6:
        print("⚠️ 检索分数普遍较低，可能说明：")
        print("   1. 问题与文档匹配度不高")
        print("   2. Embedding 模型对水利领域术语不敏感")
    
    return case_results


if __name__ == "__main__":
    run_case_analysis()
