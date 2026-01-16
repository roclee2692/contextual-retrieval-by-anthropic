"""
简化版 A/B 对比测试
使用已创建的数据库进行测试，无需重新构建索引
"""
import os
import time
import json
import sys
from dotenv import load_dotenv
from llama_index.core import VectorStoreIndex
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.retrievers.bm25 import BM25Retriever
from llama_index.llms.ollama import Ollama
from llama_index.core import Settings
import chromadb
import jieba

load_dotenv()

# 中文分词器（必须与 save_bm25.py 中的完全一致）
def chinese_tokenizer(text):
    """增强型中文分词器，支持'包'、'包子'等词的模糊匹配"""
    tokens = list(jieba.cut_for_search(text))

    enhanced_tokens = []
    for token in tokens:
        enhanced_tokens.append(token)
        # 只要包含'包'字，就添加相关词（提高召回率）
        if '包' in token:
            enhanced_tokens.append('包')
            enhanced_tokens.append('包子')

    return enhanced_tokens

# 精心设计的测试问题（根据实际PDF内容）
# 问题分类：实体查找、价格查询、窗口定位、菜品推荐

TEST_QUESTIONS = [
    # === 实体查找类（测试精确匹配能力）===
    "一号餐厅有哪些窗口或档口？",  # 测试：能否列举所有窗口
    "二号餐厅一楼有哪些档口？",    # 测试：楼层+位置筛选
    "哪些窗口提供包子类食品？",    # 测试：按类别聚合

    # === 价格查询类（测试数值过滤）===
    "2元可以买到哪些食品？",       # 测试：精确价格查询
    "5元以下有什么早餐选择？",     # 测试：价格范围查询
    "一号餐厅最便宜的粥是多少钱？", # 测试：最小值查询

    # === 窗口定位类（测试关系查询）===
    "我爱我粥在哪个餐厅的哪个窗口？",      # 测试：档口归属查询
    "天津包子档口在几号窗口？",            # 测试：窗口号查询
    "二号餐厅10号窗口是什么档口？",        # 测试：反向查询

    # === 菜品推荐类（测试语义理解）===
    "早餐想喝粥，有哪些选择？",            # 测试：按需求推荐
    "哪里可以买到手工水饺？",              # 测试：特定食品定位
    "想吃面条，有哪些窗口？",              # 测试：类别检索

    # === 特色查询类（测试上下文理解）===
    "民族风味在哪个食堂？",                # 测试：特殊档口定位
    "有哪些窗口提供烧腊类食品？",          # 测试：菜系分类
    "哪个档口的包子种类最多？",            # 测试：数量统计

    # === 组合查询类（测试复杂推理）===
    "一号餐厅有哪些2元的粥？",             # 测试：餐厅+价格+类别
    "二号餐厅哪些窗口有1.5元的食品？",     # 测试：多条件筛选
    "我爱我粥都卖什么？价格是多少？",      # 测试：菜单展示

    # === 对比查询类（测试聚合能力）===
    "天津包子和香港九龙包，哪个更便宜？",  # 测试：价格对比
    "一号餐厅和二号餐厅，哪个档口更多？"   # 测试：数量对比（可能答不出，测试边界）
]

class SimpleABTester:
    def __init__(self):
        # 从环境变量读取配置
        self.ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.vector_db_path = os.getenv("VECTOR_DB_PATH", "./src/db/canteen_db_vectordb")
        self.bm25_db_path = os.getenv("BM25_DB_PATH", "./src/db/canteen_db_bm25")
        self.collection_name = os.getenv("COLLECTION_NAME", "ncwu_canteen_collection")

        print(f"配置信息:")
        print(f"  Ollama URL: {self.ollama_url}")
        print(f"  向量数据库: {self.vector_db_path}")
        print(f"  BM25 数据库: {self.bm25_db_path}")
        print(f"  Collection: {self.collection_name}")

        # 初始化 LLM
        self.llm = Ollama(
            model="gemma3:12b",
            base_url=self.ollama_url,
            request_timeout=120.0
        )

        # 初始化 Embedding - 必须使用与数据库创建时相同的模型（中文模型！）
        self.embed_model = HuggingFaceEmbedding(
            model_name="BAAI/bge-small-zh-v1.5",  # 中文模型
            device="cpu"
        )

        Settings.llm = self.llm
        Settings.embed_model = self.embed_model

        # 加载向量数据库
        print("\n加载向量数据库...")
        self.vectordb_client = chromadb.PersistentClient(path=self.vector_db_path)
        self.chroma_collection = self.vectordb_client.get_or_create_collection(self.collection_name)
        self.vector_store = ChromaVectorStore(chroma_collection=self.chroma_collection)
        self.vector_index = VectorStoreIndex.from_vector_store(
            self.vector_store,
            embed_model=self.embed_model
        )

        # 加载 BM25 数据库
        print("加载 BM25 数据库...")
        # 注意：必须重新指定分词器，因为persist不保存tokenizer
        import jieba
        def chinese_tokenizer(text):
            """增强型中文分词器，与创建时保持一致"""
            tokens = list(jieba.cut_for_search(text))
            enhanced_tokens = []
            for token in tokens:
                enhanced_tokens.append(token)
                if '包' in token:
                    enhanced_tokens.append('包')
                    enhanced_tokens.append('包子')
            return enhanced_tokens
        
        # 先加载基础BM25
        self.bm25_retriever = BM25Retriever.from_persist_dir(
            self.bm25_db_path
        )
        # 手动设置分词器（因为persist不保存）
        self.bm25_retriever._tokenizer = chinese_tokenizer

        print("✓ 数据库加载完成\n")

    def test_query(self, query, use_hybrid=True, top_k=5):  # 改为 5
        """测试单个查询"""
        start_time = time.time()

        try:
            if use_hybrid:
                # 混合检索（向量 + BM25）
                vector_retriever = self.vector_index.as_retriever(similarity_top_k=top_k)

                # 获取向量检索结果
                vector_nodes = vector_retriever.retrieve(query)
                bm25_nodes = self.bm25_retriever.retrieve(query)

                # 合并结果
                all_nodes = list({n.node.node_id: n for n in (vector_nodes + bm25_nodes)}.values())

                # 使用查询引擎生成答案
                query_engine = self.vector_index.as_query_engine(similarity_top_k=top_k)
                response = query_engine.query(query)
            else:
                # 仅向量检索
                query_engine = self.vector_index.as_query_engine(similarity_top_k=top_k)
                response = query_engine.query(query)

            end_time = time.time()

            return {
                "success": True,
                "response": str(response),
                "time": end_time - start_time,
                "method": "混合检索" if use_hybrid else "向量检索"
            }
        except Exception as e:
            end_time = time.time()
            return {
                "success": False,
                "response": f"错误: {e}",
                "time": end_time - start_time,
                "method": "混合检索" if use_hybrid else "向量检索"
            }

    def run_comparison(self, questions=None, max_questions=None):
        """运行对比测试"""
        if questions is None:
            questions = TEST_QUESTIONS

        if max_questions:
            questions = questions[:max_questions]

        print("=" * 80)
        print(f"开始 A/B 对比测试 (共 {len(questions)} 个问题)")
        print("=" * 80)

        results = []

        for i, question in enumerate(questions, 1):
            print(f"\n[{i}/{len(questions)}] 问题: {question}")
            print("-" * 60)

            # 测试向量检索
            print("  测试方法 A: 向量检索...")
            result_a = self.test_query(question, use_hybrid=False)

            # 测试混合检索
            print("  测试方法 B: 混合检索 (向量+BM25)...")
            result_b = self.test_query(question, use_hybrid=True)

            results.append({
                "question": question,
                "vector_only": result_a,
                "hybrid": result_b
            })

            # 打印结果
            if result_a["success"]:
                print(f"\n  方法 A 回答 (耗时 {result_a['time']:.2f}s):")
                print(f"  {result_a['response'][:200]}...")
            else:
                print(f"\n  方法 A 失败: {result_a['response']}")

            if result_b["success"]:
                print(f"\n  方法 B 回答 (耗时 {result_b['time']:.2f}s):")
                print(f"  {result_b['response'][:200]}...")
            else:
                print(f"\n  方法 B 失败: {result_b['response']}")

        # 保存结果
        self.save_results(results)

        # 打印总结
        self.print_summary(results)

        return results

    def save_results(self, results):
        """保存结果"""
        timestamp = time.strftime("%Y%m%d_%H%M%S")

        # 保存 JSON
        json_file = f"ab_test_results_{timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\n结果已保存到: {json_file}")

        # 保存文本报告
        txt_file = f"ab_test_report_{timestamp}.txt"
        with open(txt_file, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("向量检索 vs 混合检索 A/B 对比测试报告\n")
            f.write("=" * 80 + "\n\n")

            for i, r in enumerate(results, 1):
                f.write(f"\n问题 {i}: {r['question']}\n")
                f.write("-" * 80 + "\n")

                if r['vector_only']['success']:
                    f.write(f"\n【方法 A: 向量检索】 (耗时: {r['vector_only']['time']:.2f}s)\n")
                    f.write(r['vector_only']['response'] + "\n")
                else:
                    f.write(f"\n【方法 A 失败】: {r['vector_only']['response']}\n")

                if r['hybrid']['success']:
                    f.write(f"\n【方法 B: 混合检索】 (耗时: {r['hybrid']['time']:.2f}s)\n")
                    f.write(r['hybrid']['response'] + "\n")
                else:
                    f.write(f"\n【方法 B 失败】: {r['hybrid']['response']}\n")

                f.write("\n" + "=" * 80 + "\n")

        print(f"报告已保存到: {txt_file}")

    def print_summary(self, results):
        """打印总结"""
        print("\n" + "=" * 80)
        print("测试总结")
        print("=" * 80)

        successful_a = [r for r in results if r['vector_only']['success']]
        successful_b = [r for r in results if r['hybrid']['success']]

        print(f"\n总问题数: {len(results)}")
        print(f"方法 A 成功: {len(successful_a)}/{len(results)}")
        print(f"方法 B 成功: {len(successful_b)}/{len(results)}")

        if successful_a:
            times_a = [r['vector_only']['time'] for r in successful_a]
            print(f"\n方法 A (向量检索):")
            print(f"  - 平均响应时间: {sum(times_a)/len(times_a):.2f}s")
            print(f"  - 最快: {min(times_a):.2f}s")
            print(f"  - 最慢: {max(times_a):.2f}s")

        if successful_b:
            times_b = [r['hybrid']['time'] for r in successful_b]
            print(f"\n方法 B (混合检索):")
            print(f"  - 平均响应时间: {sum(times_b)/len(times_b):.2f}s")
            print(f"  - 最快: {min(times_b):.2f}s")
            print(f"  - 最慢: {max(times_b):.2f}s")


if __name__ == "__main__":
    print("=" * 80)
    print("龙子湖食堂 RAG 系统 - 简化版 A/B 测试")
    print("=" * 80)
    print("\n此脚本使用已创建的数据库进行测试")
    print("请确保:")
    print("1. 已运行 'python create_save_db.py' 创建数据库")
    print("2. WSL 中已启动 'ollama serve'")

    # 检查是否提供了问题数量参数
    max_questions = None
    if len(sys.argv) > 1:
        try:
            max_questions = int(sys.argv[1])
            print(f"\n将测试前 {max_questions} 个问题")
        except:
            print("\n参数无效，将测试所有 20 个问题")

    print("\n按 Enter 继续...")
    input()

    try:
        tester = SimpleABTester()
        results = tester.run_comparison(max_questions=max_questions)
        print("\n" + "=" * 80)
        print("测试完成！")
        print("=" * 80)
    except Exception as e:
        print(f"\n测试失败: {e}")
        import traceback
        traceback.print_exc()

