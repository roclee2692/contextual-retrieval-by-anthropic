"""
Phase 3 Enhanced: Baseline vs CR 对比实验 (n=30)
补强版本：
1. 扩展测试集从 n=10 到 n=30（三类问题，每类10个）
2. 增加人工二分类正确率评估（检索正确、答案正确）
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

# ============================================================================
# 扩展测试问题集 (n=30)
# 三类问题，每类10个：
#   A类：数值/属性查询（需要精确匹配）
#   B类：实体/关系查询（需要理解上下文关联）
#   C类：流程/条件查询（需要完整段落）
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

def evaluate_retrieval(top_text, keywords):
    """
    人工评估辅助：检查检索结果是否包含关键词
    返回：命中的关键词数量 / 总关键词数量
    """
    hit_count = sum(1 for kw in keywords if kw in top_text)
    return hit_count / len(keywords) if keywords else 0

def run_experiment(name, retriever, queries):
    """运行单组实验"""
    print(f"\n{'='*70}")
    print(f"实验: {name} (n={len(queries)})")
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
        
        print(f"🔍 [{qid}] {query}")
        
        try:
            start = time.time()
            nodes = retriever.retrieve(QueryBundle(query))
            elapsed = time.time() - start
            
            if nodes and len(nodes) > 0:
                top_text = nodes[0].text[:500].replace('\n', ' ')
                top_score = nodes[0].score if nodes[0].score else 0
                results_count = len(nodes)
                
                # 关键词命中率（辅助人工评估）
                keyword_hit_rate = evaluate_retrieval(top_text, keywords)
                # 简化判断：命中率>=50%认为检索正确
                retrieval_correct = keyword_hit_rate >= 0.5
            else:
                top_text = "无结果"
                top_score = 0
                results_count = 0
                keyword_hit_rate = 0
                retrieval_correct = False
            
            result = {
                "id": qid,
                "query": query,
                "category": category,
                "time": elapsed,
                "top_1_text": top_text,
                "top_1_score": top_score,
                "results_count": results_count,
                "keyword_hit_rate": keyword_hit_rate,
                "retrieval_correct": retrieval_correct,  # 检索是否正确（基于关键词）
                "answer_correct": None  # 预留：人工标注答案是否正确
            }
            results.append(result)
            
            # 分类统计
            if category not in category_stats:
                category_stats[category] = {"total": 0, "correct": 0, "scores": []}
            category_stats[category]["total"] += 1
            category_stats[category]["scores"].append(top_score)
            if retrieval_correct:
                category_stats[category]["correct"] += 1
            
            mark = "✓" if retrieval_correct else "✗"
            print(f"   ⏱️ {elapsed:.2f}s | 得分: {top_score:.3f} | 关键词命中: {keyword_hit_rate:.0%} {mark}")
            print(f"   📄 {top_text[:80]}...\n")
            
        except Exception as e:
            print(f"   ❌ 错误: {e}\n")
            results.append({
                "id": qid,
                "query": query,
                "category": category,
                "error": str(e)
            })
    
    # 打印分类统计
    print(f"\n{'='*70}")
    print(f"{name} - 分类统计")
    print(f"{'='*70}")
    for cat, stats in category_stats.items():
        avg_score = sum(stats["scores"]) / len(stats["scores"]) if stats["scores"] else 0
        acc = stats["correct"] / stats["total"] if stats["total"] > 0 else 0
        print(f"  {cat}: 准确率 {acc:.0%} ({stats['correct']}/{stats['total']}), 平均得分 {avg_score:.3f}")
    
    return results

def generate_report(baseline_results, cr_results, queries):
    """生成对比报告"""
    report_path = Path("results/phase3_enhanced_report.md")
    report_path.parent.mkdir(exist_ok=True)
    
    md = "# Phase 3 Enhanced: Baseline vs CR 对比实验报告\n\n"
    md += f"**测试时间**: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
    md += f"**测试问题数**: n={len(queries)}\n\n"
    
    md += "## 实验配置\n\n"
    md += "| 实验组 | 说明 |\n"
    md += "|--------|------|\n"
    md += "| **Baseline** | 原始文档分块直接检索（向量+BM25混合） |\n"
    md += "| **CR Enhanced** | 上下文增强检索（每个分块增加了LLM生成的上下文摘要） |\n\n"
    
    md += "## 问题分类说明\n\n"
    md += "| 类别 | 数量 | 说明 |\n"
    md += "|------|------|------|\n"
    md += "| A-数值属性 | 10 | 需要精确匹配数值的查询（如水位、库容） |\n"
    md += "| B-实体关系 | 10 | 需要理解实体关联的查询（如责任人、管理单位） |\n"
    md += "| C-流程条件 | 10 | 需要完整段落的查询（如操作步骤、条件触发） |\n\n"
    
    # 分类汇总
    md += "## 分类汇总结果\n\n"
    md += "| 类别 | Baseline准确率 | CR准确率 | Baseline得分 | CR得分 | 差异 |\n"
    md += "|------|----------------|----------|--------------|--------|------|\n"
    
    categories = ["A-数值属性", "B-实体关系", "C-流程条件"]
    
    for cat in categories:
        b_items = [r for r in baseline_results if r.get("category") == cat and "error" not in r]
        c_items = [r for r in cr_results if r.get("category") == cat and "error" not in r]
        
        b_correct = sum(1 for r in b_items if r.get("retrieval_correct"))
        c_correct = sum(1 for r in c_items if r.get("retrieval_correct"))
        b_acc = b_correct / len(b_items) if b_items else 0
        c_acc = c_correct / len(c_items) if c_items else 0
        
        b_score = sum(r.get("top_1_score", 0) for r in b_items) / len(b_items) if b_items else 0
        c_score = sum(r.get("top_1_score", 0) for r in c_items) / len(c_items) if c_items else 0
        
        diff = c_score - b_score
        indicator = "📈" if diff > 0.01 else ("📉" if diff < -0.01 else "➡️")
        
        md += f"| {cat} | {b_acc:.0%} ({b_correct}/{len(b_items)}) | {c_acc:.0%} ({c_correct}/{len(c_items)}) | {b_score:.3f} | {c_score:.3f} | {diff:+.3f} {indicator} |\n"
    
    # 总体统计
    md += "\n## 总体统计\n\n"
    
    if baseline_results and cr_results:
        b_scores = [r.get("top_1_score", 0) for r in baseline_results if "error" not in r]
        c_scores = [r.get("top_1_score", 0) for r in cr_results if "error" not in r]
        b_correct = sum(1 for r in baseline_results if r.get("retrieval_correct"))
        c_correct = sum(1 for r in cr_results if r.get("retrieval_correct"))
        
        avg_b_score = sum(b_scores) / len(b_scores) if b_scores else 0
        avg_c_score = sum(c_scores) / len(c_scores) if c_scores else 0
        b_acc = b_correct / len(baseline_results)
        c_acc = c_correct / len(cr_results)
        
        md += "| 指标 | Baseline | CR Enhanced | 差异 |\n"
        md += "|------|----------|-------------|------|\n"
        md += f"| 平均相似度得分 | {avg_b_score:.4f} | {avg_c_score:.4f} | {avg_c_score - avg_b_score:+.4f} |\n"
        md += f"| 检索正确率 | {b_acc:.1%} ({b_correct}/{len(baseline_results)}) | {c_acc:.1%} ({c_correct}/{len(cr_results)}) | {c_acc - b_acc:+.1%} |\n"
        
        # 统计检验
        import math
        n = len(b_scores)
        diffs = [c - b for b, c in zip(b_scores, c_scores)]
        mean_diff = sum(diffs) / n
        variance = sum((d - mean_diff)**2 for d in diffs) / (n - 1)
        std_diff = math.sqrt(variance)
        se = std_diff / math.sqrt(n)
        t_stat = mean_diff / se if se > 0 else 0
        
        md += f"\n### 统计检验 (配对t检验)\n\n"
        md += f"- 样本量 n = {n}\n"
        md += f"- 平均差异 = {mean_diff:+.4f}\n"
        md += f"- t 统计量 = {t_stat:.3f}\n"
        md += f"- 临界值 (α=0.05, df={n-1}) ≈ 2.045\n"
        
        if abs(t_stat) > 2.045:
            md += f"- **结论**: 差异显著 (p < 0.05) ✅\n"
        else:
            md += f"- **结论**: 差异不显著 (p > 0.05) ⚠️\n"
        
        # 符号检验
        pos = sum(1 for d in diffs if d > 0)
        neg = sum(1 for d in diffs if d < 0)
        tie = sum(1 for d in diffs if d == 0)
        md += f"\n### 符号检验\n\n"
        md += f"- CR > Baseline: {pos} 次\n"
        md += f"- CR < Baseline: {neg} 次\n"
        md += f"- CR = Baseline: {tie} 次\n"
    
    # 逐题详情（简化版）
    md += "\n## 逐题结果概览\n\n"
    md += "| ID | 问题 | 类别 | Baseline | CR | Winner |\n"
    md += "|----|----|------|----------|-----|--------|\n"
    
    for i, item in enumerate(queries):
        qid = item["id"]
        query_short = item["query"][:20] + "..." if len(item["query"]) > 20 else item["query"]
        cat = item["category"].split("-")[0]
        
        b_result = baseline_results[i] if baseline_results and i < len(baseline_results) else {}
        c_result = cr_results[i] if cr_results and i < len(cr_results) else {}
        
        b_score = b_result.get("top_1_score", 0)
        c_score = c_result.get("top_1_score", 0)
        b_mark = "✓" if b_result.get("retrieval_correct") else "✗"
        c_mark = "✓" if c_result.get("retrieval_correct") else "✗"
        
        if c_score > b_score + 0.01:
            winner = "CR"
        elif b_score > c_score + 0.01:
            winner = "Baseline"
        else:
            winner = "平局"
        
        md += f"| {qid} | {query_short} | {cat} | {b_score:.3f} {b_mark} | {c_score:.3f} {c_mark} | {winner} |\n"
    
    # 结论
    md += "\n## 结论\n\n"
    if avg_c_score > avg_b_score:
        improvement = ((avg_c_score - avg_b_score) / avg_b_score * 100) if avg_b_score > 0 else 0
        md += f"1. **CR Enhanced 相比 Baseline 平均相似度提升了 {improvement:.1f}%**\n"
    else:
        md += f"1. **CR Enhanced 与 Baseline 效果相近或略有下降**\n"
    
    md += f"2. **检索正确率**: Baseline {b_acc:.1%} vs CR {c_acc:.1%}\n"
    md += f"3. **符号检验**: CR在 {pos}/{n} 个问题上表现更好\n"
    
    report_path.write_text(md, encoding='utf-8')
    print(f"\n📊 对比报告已保存: {report_path}")
    
    # 保存 JSON 格式（包含完整数据供人工标注）
    json_path = Path("results/phase3_enhanced_data.json")
    json_data = {
        "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
        "config": {
            "n_questions": len(queries),
            "categories": ["A-数值属性", "B-实体关系", "C-流程条件"]
        },
        "summary": {
            "baseline_avg_score": avg_b_score,
            "cr_avg_score": avg_c_score,
            "baseline_accuracy": b_acc,
            "cr_accuracy": c_acc,
            "t_statistic": t_stat,
            "sign_test": {"cr_wins": pos, "baseline_wins": neg, "ties": tie}
        },
        "baseline": baseline_results,
        "cr_enhanced": cr_results
    }
    json_path.write_text(json.dumps(json_data, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"📊 JSON数据已保存: {json_path}")
    
    return json_data["summary"]

def main():
    print("="*80)
    print("  Phase 3 Enhanced: Baseline vs CR 对比实验 (n=30)")
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
        summary = generate_report(baseline_results, cr_results, TEST_QUERIES)
        
        print("\n" + "="*80)
        print("  实验完成 - 汇总结果")
        print("="*80)
        print(f"  样本量: n={len(TEST_QUERIES)}")
        print(f"  Baseline 平均得分: {summary['baseline_avg_score']:.4f}")
        print(f"  CR 平均得分: {summary['cr_avg_score']:.4f}")
        print(f"  Baseline 检索正确率: {summary['baseline_accuracy']:.1%}")
        print(f"  CR 检索正确率: {summary['cr_accuracy']:.1%}")
        print(f"  t 统计量: {summary['t_statistic']:.3f}")
        print(f"  符号检验: CR胜 {summary['sign_test']['cr_wins']}, Baseline胜 {summary['sign_test']['baseline_wins']}, 平局 {summary['sign_test']['ties']}")
    
    print("\n" + "="*80)
    print("✅ Phase 3 Enhanced 实验完成！")
    print("="*80)

if __name__ == "__main__":
    main()
