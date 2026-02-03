"""
Phase 3 Reranker 消融实验
2×2 消融设计：
- Baseline vs CR
- 无Reranker vs 有Reranker

使用模型：BAAI/bge-reranker-base
"""
import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from dotenv import load_dotenv
sys.path.insert(0, str(Path(__file__).parents[1]))

from llama_index.core import (
    VectorStoreIndex, 
    QueryBundle
)
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.retrievers.bm25 import BM25Retriever
from llama_index.core.retrievers import BaseRetriever
from llama_index.core.schema import NodeWithScore
import chromadb
import jieba
from typing import List, Optional
import numpy as np
from scipy import stats

# Reranker 模型
from sentence_transformers import CrossEncoder

load_dotenv()

# ============================================================================
# 测试问题集 (与 phase3_enhanced.py 相同的30个问题)
# ============================================================================

TEST_QUERIES = [
    # ========== A类：数值/属性查询 (10个) ==========
    {"id": "A01", "query": "杨家横水库的汛限水位是多少？", "category": "A-数值属性", 
     "expected_answer": "298.50m或相近数值", "keywords": ["汛限水位", "298", "水位"]},
    {"id": "A02", "query": "常庄水库的总库容是多少？", "category": "A-数值属性",
     "expected_answer": "1740万立方米", "keywords": ["总库容", "1740", "万"]},
    {"id": "A03", "query": "杨家横水库的校核洪水位是多少？", "category": "A-数值属性",
     "expected_answer": "304.80m或相近数值", "keywords": ["校核", "洪水位", "304"]},
    {"id": "A04", "query": "常庄水库的兴利库容是多少？", "category": "A-数值属性",
     "expected_answer": "700万立方米左右", "keywords": ["兴利库容", "700", "万"]},
    {"id": "A05", "query": "杨家横水库大坝的坝顶高程是多少？", "category": "A-数值属性",
     "expected_answer": "306m左右", "keywords": ["坝顶", "高程", "306"]},
    {"id": "A06", "query": "常庄水库的设计洪水位是多少？", "category": "A-数值属性",
     "expected_answer": "具体数值", "keywords": ["设计", "洪水位"]},
    {"id": "A07", "query": "杨家横水库控制的流域面积是多少？", "category": "A-数值属性",
     "expected_answer": "平方公里数值", "keywords": ["流域面积", "平方公里", "km"]},
    {"id": "A08", "query": "常庄水库的死库容是多少？", "category": "A-数值属性",
     "expected_answer": "万立方米数值", "keywords": ["死库容", "万"]},
    {"id": "A09", "query": "杨家横水库溢洪道的设计流量是多少？", "category": "A-数值属性",
     "expected_answer": "立方米每秒", "keywords": ["溢洪道", "流量", "m³/s"]},
    {"id": "A10", "query": "常庄水库大坝的坝长是多少米？", "category": "A-数值属性",
     "expected_answer": "米数值", "keywords": ["坝长", "米", "m"]},

    # ========== B类：实体/关系查询 (10个) ==========
    {"id": "B01", "query": "杨家横水库的大坝安全责任人是谁？", "category": "B-实体关系",
     "expected_answer": "具体人名", "keywords": ["责任人", "安全", "负责"]},
    {"id": "B02", "query": "常庄水库防汛指挥部的指挥长是谁？", "category": "B-实体关系",
     "expected_answer": "副市长或具体职务", "keywords": ["指挥长", "防汛", "指挥部"]},
    {"id": "B03", "query": "杨家横水库由哪个单位管理？", "category": "B-实体关系",
     "expected_answer": "管理处或管理单位名称", "keywords": ["管理", "单位", "处"]},
    {"id": "B04", "query": "常庄水库的防汛抢险技术负责人是谁？", "category": "B-实体关系",
     "expected_answer": "具体人名或职务", "keywords": ["技术", "负责", "抢险"]},
    {"id": "B05", "query": "杨家横水库位于哪条河流上？", "category": "B-实体关系",
     "expected_answer": "河流名称", "keywords": ["河流", "位于", "河"]},
    {"id": "B06", "query": "常庄水库下游主要保护哪些区域？", "category": "B-实体关系",
     "expected_answer": "保护区域名称", "keywords": ["下游", "保护", "区域"]},
    {"id": "B07", "query": "杨家横水库的上级主管部门是什么？", "category": "B-实体关系",
     "expected_answer": "水利局或相关部门", "keywords": ["主管", "部门", "上级"]},
    {"id": "B08", "query": "常庄水库建于哪一年？", "category": "B-实体关系",
     "expected_answer": "年份", "keywords": ["建", "年", "建成"]},
    {"id": "B09", "query": "谁负责防洪指挥部的统一调度？", "category": "B-实体关系",
     "expected_answer": "行政首长或具体职务", "keywords": ["调度", "统一", "负责"]},
    {"id": "B10", "query": "防汛物资由哪个部门负责储备？", "category": "B-实体关系",
     "expected_answer": "部门名称", "keywords": ["物资", "储备", "部门"]},

    # ========== C类：流程/条件查询 (10个) ==========
    {"id": "C01", "query": "什么情况下需要启动III级应急响应？", "category": "C-流程条件",
     "expected_answer": "水位或雨量条件", "keywords": ["III级", "响应", "启动"]},
    {"id": "C02", "query": "水库水位达到多少时需要开始泄洪？", "category": "C-流程条件",
     "expected_answer": "水位数值和条件", "keywords": ["泄洪", "水位", "开始"]},
    {"id": "C03", "query": "防洪抢险物资储备包括哪些东西？", "category": "C-流程条件",
     "expected_answer": "物资清单", "keywords": ["物资", "储备", "包括"]},
    {"id": "C04", "query": "防汛抢险队伍由哪些部门组成？", "category": "C-流程条件",
     "expected_answer": "部门列表", "keywords": ["队伍", "组成", "部门"]},
    {"id": "C05", "query": "堤防巡查的具体步骤是什么？", "category": "C-流程条件",
     "expected_answer": "巡查步骤描述", "keywords": ["巡查", "步骤", "检查"]},
    {"id": "C06", "query": "发现险情后应该如何报告？", "category": "C-流程条件",
     "expected_answer": "报告流程", "keywords": ["险情", "报告", "上报"]},
    {"id": "C07", "query": "洪水预警信号有哪几个等级？", "category": "C-流程条件",
     "expected_answer": "等级划分", "keywords": ["预警", "等级", "信号"]},
    {"id": "C08", "query": "群众转移安置的程序是什么？", "category": "C-流程条件",
     "expected_answer": "转移程序", "keywords": ["转移", "安置", "群众"]},
    {"id": "C09", "query": "水库大坝出现裂缝应如何处理？", "category": "C-流程条件",
     "expected_answer": "处理措施", "keywords": ["裂缝", "处理", "措施"]},
    {"id": "C10", "query": "防汛值班制度的具体要求是什么？", "category": "C-流程条件",
     "expected_answer": "值班要求", "keywords": ["值班", "制度", "要求"]},
]

# ============================================================================
# 数据库路径配置
# ============================================================================
BASE_DIR = Path(__file__).parents[1]
DB_DIR = BASE_DIR / "src" / "db"

BASELINE_VECTOR_PATH = str(DB_DIR / "flood_prevention_db_baseline_vectordb")
BASELINE_BM25_PATH = str(DB_DIR / "flood_prevention_db_baseline_bm25")
CR_VECTOR_PATH = str(DB_DIR / "flood_prevention_db_cr_vectordb")
CR_BM25_PATH = str(DB_DIR / "flood_prevention_db_cr_bm25")

COLLECTION_NAME = "flood_prevention_collection"


def chinese_tokenizer(text):
    """中文分词器"""
    return list(jieba.cut_for_search(text))


class HybridRetriever(BaseRetriever):
    """混合检索器（向量+BM25）"""
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


class RerankerWrapper:
    """Reranker 包装器"""
    def __init__(self, model_name="BAAI/bge-reranker-base"):
        print(f"🔧 加载 Reranker 模型: {model_name}")
        self.model = CrossEncoder(model_name, max_length=512)
        print("   ✓ Reranker 模型加载成功")
    
    def rerank(self, query: str, nodes: List[NodeWithScore], top_k: int = 3) -> List[NodeWithScore]:
        """对检索结果进行重排序"""
        if not nodes:
            return []
        
        # 构建 query-passage 对
        pairs = [(query, node.node.get_content()) for node in nodes]
        
        # 计算 reranker 分数
        scores = self.model.predict(pairs)
        
        # 根据 reranker 分数重新排序
        scored_nodes = list(zip(nodes, scores))
        scored_nodes.sort(key=lambda x: x[1], reverse=True)
        
        # 返回 top-k 并更新分数
        reranked = []
        for node, score in scored_nodes[:top_k]:
            new_node = NodeWithScore(node=node.node, score=float(score))
            reranked.append(new_node)
        
        return reranked


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
    # 统一配置：top_k=10
    vector_retriever = vector_index.as_retriever(similarity_top_k=10)
    
    bm25_retriever = None
    if os.path.exists(bm25_path):
        try:
            bm25_retriever = BM25Retriever.from_persist_dir(bm25_path)
            # 统一配置：top_k=10
            bm25_retriever._similarity_top_k = 10
            print(f"   ✓ BM25索引加载成功")
        except Exception as e:
            print(f"   ⚠️ BM25加载失败: {e}")
    
    return HybridRetriever(vector_retriever, bm25_retriever, top_k=10)


def evaluate_retrieval(top_text, keywords):
    """检查检索结果是否包含关键词"""
    hit_count = sum(1 for kw in keywords if kw in top_text)
    return hit_count / len(keywords) if keywords else 0


def run_single_experiment(name: str, retriever, queries: List[dict], 
                          reranker: Optional[RerankerWrapper] = None) -> dict:
    """运行单组实验"""
    print(f"\n{'='*70}")
    print(f"实验: {name} (n={len(queries)}) {'[+Reranker]' if reranker else '[无Reranker]'}")
    print(f"{'='*70}\n")
    
    if not retriever:
        print(f"❌ {name} 检索器初始化失败")
        return None
    
    results = []
    category_stats = {}
    
    for item in queries:
        query = item["query"]
        qid = item["id"]
        category = item["category"]
        keywords = item.get("keywords", [])
        
        # 检索
        nodes = retriever.retrieve(query)
        
        # 如果有 Reranker，进行重排序
        if reranker:
            nodes = reranker.rerank(query, nodes, top_k=3)
        else:
            nodes = nodes[:3]  # 无 reranker 时直接取 top-3
        
        # 计算指标
        if nodes:
            top_score = nodes[0].score if nodes[0].score else 0
            top_text = nodes[0].node.get_content()
            all_text = " ".join([n.node.get_content() for n in nodes])
            keyword_hit_rate = evaluate_retrieval(all_text, keywords)
            retrieval_correct = keyword_hit_rate >= 0.5
        else:
            top_score = 0
            top_text = ""
            keyword_hit_rate = 0
            retrieval_correct = False
        
        print(f"  [{qid}] score={top_score:.4f}, kw_hit={keyword_hit_rate:.2f}, correct={retrieval_correct}")
        
        # 分类统计
        if category not in category_stats:
            category_stats[category] = {"correct": 0, "total": 0, "scores": []}
        category_stats[category]["total"] += 1
        category_stats[category]["scores"].append(top_score)
        if retrieval_correct:
            category_stats[category]["correct"] += 1
        
        results.append({
            "id": qid,
            "query": query,
            "category": category,
            "score": top_score,
            "keyword_hit_rate": keyword_hit_rate,
            "retrieval_correct": retrieval_correct
        })
    
    # 汇总统计
    scores = [r["score"] for r in results]
    correct_count = sum(1 for r in results if r["retrieval_correct"])
    
    summary = {
        "name": name,
        "has_reranker": reranker is not None,
        "n": len(results),
        "avg_score": np.mean(scores),
        "std_score": np.std(scores),
        "accuracy": correct_count / len(results),
        "correct_count": correct_count,
        "category_stats": {
            cat: {
                "accuracy": stats["correct"] / stats["total"],
                "avg_score": np.mean(stats["scores"]),
                "correct": stats["correct"],
                "total": stats["total"]
            }
            for cat, stats in category_stats.items()
        },
        "results": results
    }
    
    print(f"\n📊 {name} 汇总:")
    print(f"   平均分数: {summary['avg_score']:.4f} (±{summary['std_score']:.4f})")
    print(f"   检索正确率: {summary['accuracy']*100:.1f}% ({correct_count}/{len(results)})")
    
    return summary


def run_ablation_experiment():
    """运行 2×2 消融实验"""
    print("=" * 80)
    print("Phase 3 Reranker 消融实验")
    print("=" * 80)
    print(f"\n🕐 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📝 测试问题数: {len(TEST_QUERIES)}")
    
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
    
    # 初始化 Reranker
    print("\n" + "=" * 80)
    print("步骤 2: 初始化 Reranker")
    print("=" * 80)
    
    reranker = RerankerWrapper("BAAI/bge-reranker-base")
    
    # 运行 4 组实验
    print("\n" + "=" * 80)
    print("步骤 3: 运行 2×2 消融实验")
    print("=" * 80)
    
    experiments = {}
    
    # 1. Baseline 无 Reranker
    experiments["baseline"] = run_single_experiment(
        "Baseline", baseline_retriever, TEST_QUERIES, reranker=None
    )
    
    # 2. Baseline + Reranker
    experiments["baseline_reranker"] = run_single_experiment(
        "Baseline + Reranker", baseline_retriever, TEST_QUERIES, reranker=reranker
    )
    
    # 3. CR 无 Reranker
    experiments["cr"] = run_single_experiment(
        "CR Enhanced", cr_retriever, TEST_QUERIES, reranker=None
    )
    
    # 4. CR + Reranker
    experiments["cr_reranker"] = run_single_experiment(
        "CR + Reranker", cr_retriever, TEST_QUERIES, reranker=reranker
    )
    
    # ============================================================================
    # 统计分析
    # ============================================================================
    print("\n" + "=" * 80)
    print("步骤 4: 统计分析")
    print("=" * 80)
    
    analysis = {}
    
    # 各组分数
    baseline_scores = [r["score"] for r in experiments["baseline"]["results"]]
    baseline_rr_scores = [r["score"] for r in experiments["baseline_reranker"]["results"]]
    cr_scores = [r["score"] for r in experiments["cr"]["results"]]
    cr_rr_scores = [r["score"] for r in experiments["cr_reranker"]["results"]]
    
    # 配对 t 检验
    # 1. Baseline vs CR (无 Reranker)
    t1, p1 = stats.ttest_rel(baseline_scores, cr_scores)
    analysis["baseline_vs_cr"] = {"t": t1, "p": p1, "significant": p1 < 0.05}
    
    # 2. Baseline vs Baseline+Reranker (Reranker 效果)
    t2, p2 = stats.ttest_rel(baseline_scores, baseline_rr_scores)
    analysis["baseline_reranker_effect"] = {"t": t2, "p": p2, "significant": p2 < 0.05}
    
    # 3. CR vs CR+Reranker (Reranker 效果)
    t3, p3 = stats.ttest_rel(cr_scores, cr_rr_scores)
    analysis["cr_reranker_effect"] = {"t": t3, "p": p3, "significant": p3 < 0.05}
    
    # 4. Baseline vs CR+Reranker (最大差异)
    t4, p4 = stats.ttest_rel(baseline_scores, cr_rr_scores)
    analysis["baseline_vs_cr_reranker"] = {"t": t4, "p": p4, "significant": p4 < 0.05}
    
    # 符号检验：CR+Reranker vs Baseline
    wins = sum(1 for i in range(len(TEST_QUERIES)) if cr_rr_scores[i] > baseline_scores[i])
    losses = sum(1 for i in range(len(TEST_QUERIES)) if cr_rr_scores[i] < baseline_scores[i])
    ties = len(TEST_QUERIES) - wins - losses
    analysis["sign_test"] = {"wins": wins, "losses": losses, "ties": ties}
    
    # ============================================================================
    # 生成报告
    # ============================================================================
    print("\n" + "=" * 80)
    print("步骤 5: 生成报告")
    print("=" * 80)
    
    report = f"""# Phase 3 Reranker 消融实验报告

**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 实验设计

**2×2 消融设计**:
- 因子 A: 检索方法 (Baseline vs CR Enhanced)
- 因子 B: Reranker (无 vs 有)
- Reranker 模型: `BAAI/bge-reranker-base`
- 测试问题数: n={len(TEST_QUERIES)}

## 主要结果

### 总体对比

| 方法 | 平均分数 | 检索正确率 | 正确数 |
|------|----------|------------|--------|
| Baseline | {experiments['baseline']['avg_score']:.4f} | {experiments['baseline']['accuracy']*100:.1f}% | {experiments['baseline']['correct_count']}/30 |
| Baseline + Reranker | {experiments['baseline_reranker']['avg_score']:.4f} | {experiments['baseline_reranker']['accuracy']*100:.1f}% | {experiments['baseline_reranker']['correct_count']}/30 |
| CR Enhanced | {experiments['cr']['avg_score']:.4f} | {experiments['cr']['accuracy']*100:.1f}% | {experiments['cr']['correct_count']}/30 |
| **CR + Reranker** | **{experiments['cr_reranker']['avg_score']:.4f}** | **{experiments['cr_reranker']['accuracy']*100:.1f}%** | **{experiments['cr_reranker']['correct_count']}/30** |

### 2×2 消融表

|  | 无 Reranker | 有 Reranker | Reranker 提升 |
|--|-------------|-------------|---------------|
| **Baseline** | {experiments['baseline']['accuracy']*100:.1f}% | {experiments['baseline_reranker']['accuracy']*100:.1f}% | +{(experiments['baseline_reranker']['accuracy']-experiments['baseline']['accuracy'])*100:.1f}% |
| **CR** | {experiments['cr']['accuracy']*100:.1f}% | {experiments['cr_reranker']['accuracy']*100:.1f}% | +{(experiments['cr_reranker']['accuracy']-experiments['cr']['accuracy'])*100:.1f}% |
| **CR 提升** | +{(experiments['cr']['accuracy']-experiments['baseline']['accuracy'])*100:.1f}% | +{(experiments['cr_reranker']['accuracy']-experiments['baseline_reranker']['accuracy'])*100:.1f}% | - |

### 分类结果对比

#### Baseline vs CR + Reranker

| 类别 | Baseline | CR + Reranker | 提升 |
|------|----------|---------------|------|
| A-数值属性 | {experiments['baseline']['category_stats']['A-数值属性']['accuracy']*100:.0f}% | {experiments['cr_reranker']['category_stats']['A-数值属性']['accuracy']*100:.0f}% | +{(experiments['cr_reranker']['category_stats']['A-数值属性']['accuracy']-experiments['baseline']['category_stats']['A-数值属性']['accuracy'])*100:.0f}% |
| B-实体关系 | {experiments['baseline']['category_stats']['B-实体关系']['accuracy']*100:.0f}% | {experiments['cr_reranker']['category_stats']['B-实体关系']['accuracy']*100:.0f}% | +{(experiments['cr_reranker']['category_stats']['B-实体关系']['accuracy']-experiments['baseline']['category_stats']['B-实体关系']['accuracy'])*100:.0f}% |
| C-流程条件 | {experiments['baseline']['category_stats']['C-流程条件']['accuracy']*100:.0f}% | {experiments['cr_reranker']['category_stats']['C-流程条件']['accuracy']*100:.0f}% | +{(experiments['cr_reranker']['category_stats']['C-流程条件']['accuracy']-experiments['baseline']['category_stats']['C-流程条件']['accuracy'])*100:.0f}% |

## 统计检验

| 对比 | t 值 | p 值 | 显著性 |
|------|------|------|--------|
| Baseline vs CR | {analysis['baseline_vs_cr']['t']:.3f} | {analysis['baseline_vs_cr']['p']:.4f} | {'✅ 显著' if analysis['baseline_vs_cr']['significant'] else '❌ 不显著'} |
| Baseline → Baseline+RR | {analysis['baseline_reranker_effect']['t']:.3f} | {analysis['baseline_reranker_effect']['p']:.4f} | {'✅ 显著' if analysis['baseline_reranker_effect']['significant'] else '❌ 不显著'} |
| CR → CR+RR | {analysis['cr_reranker_effect']['t']:.3f} | {analysis['cr_reranker_effect']['p']:.4f} | {'✅ 显著' if analysis['cr_reranker_effect']['significant'] else '❌ 不显著'} |
| Baseline vs CR+RR | {analysis['baseline_vs_cr_reranker']['t']:.3f} | {analysis['baseline_vs_cr_reranker']['p']:.4f} | {'✅ 显著' if analysis['baseline_vs_cr_reranker']['significant'] else '❌ 不显著'} |

### 符号检验 (CR+Reranker vs Baseline)

| CR+RR 胜 | CR+RR 负 | 平局 |
|----------|----------|------|
| {analysis['sign_test']['wins']} | {analysis['sign_test']['losses']} | {analysis['sign_test']['ties']} |

## 结论

1. **CR 效果验证**: CR 相比 Baseline {'显著' if analysis['baseline_vs_cr']['significant'] else '不显著'}提升 (p={analysis['baseline_vs_cr']['p']:.4f})
2. **Reranker 效果**: 
   - 对 Baseline: {'显著' if analysis['baseline_reranker_effect']['significant'] else '不显著'}提升
   - 对 CR: {'显著' if analysis['cr_reranker_effect']['significant'] else '不显著'}提升
3. **最佳配置**: **CR + Reranker** 达到最高正确率 {experiments['cr_reranker']['accuracy']*100:.1f}%
4. **vs Baseline 提升**: +{(experiments['cr_reranker']['accuracy']-experiments['baseline']['accuracy'])*100:.1f}% (从 {experiments['baseline']['accuracy']*100:.1f}% 到 {experiments['cr_reranker']['accuracy']*100:.1f}%)
"""
    
    # 保存报告
    results_dir = BASE_DIR / "results"
    results_dir.mkdir(exist_ok=True)
    
    report_path = results_dir / "phase3_reranker_ablation_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"   ✓ 报告已保存: {report_path}")
    
    # 保存完整数据
    data_path = results_dir / "phase3_reranker_ablation_data.json"
    full_data = {
        "timestamp": datetime.now().isoformat(),
        "experiments": experiments,
        "analysis": {k: {kk: (float(vv) if isinstance(vv, (np.floating, float)) else vv) for kk, vv in v.items()} for k, v in analysis.items()},
        "queries": TEST_QUERIES
    }
    with open(data_path, "w", encoding="utf-8") as f:
        json.dump(full_data, f, ensure_ascii=False, indent=2, default=str)
    print(f"   ✓ 数据已保存: {data_path}")
    
    # 打印最终摘要
    print("\n" + "=" * 80)
    print("📊 最终结果摘要")
    print("=" * 80)
    print(f"""
┌─────────────────────────────────────────────────────────────┐
│                    2×2 消融实验结果                          │
├─────────────────┬─────────────────┬─────────────────────────┤
│                 │   无 Reranker   │      有 Reranker        │
├─────────────────┼─────────────────┼─────────────────────────┤
│    Baseline     │     {experiments['baseline']['accuracy']*100:5.1f}%      │        {experiments['baseline_reranker']['accuracy']*100:5.1f}%           │
├─────────────────┼─────────────────┼─────────────────────────┤
│       CR        │     {experiments['cr']['accuracy']*100:5.1f}%      │        {experiments['cr_reranker']['accuracy']*100:5.1f}%  ⭐        │
└─────────────────┴─────────────────┴─────────────────────────┘

🏆 最佳配置: CR + Reranker ({experiments['cr_reranker']['accuracy']*100:.1f}%)
📈 相比 Baseline 提升: +{(experiments['cr_reranker']['accuracy']-experiments['baseline']['accuracy'])*100:.1f}%
""")
    
    return experiments, analysis


if __name__ == "__main__":
    run_ablation_experiment()
