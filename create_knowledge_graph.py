"""
创建食堂知识图谱 - 基于 LlamaIndex
使用 LLM 自动从 PDF 中抽取三元组
"""
import os
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

# 自定义知识抽取 Schema（针对食堂领域）
KG_TRIPLET_EXTRACT_TMPL = """
你是一个专门从食堂菜单中提取知识图谱的助手。

请从以下文本中提取实体和关系，构建三元组。

【实体类型】
- 校区、食堂、楼层、窗口、档口、食品、价格、类别

【关系类型】
- has_canteen(有食堂)、has_floor(有楼层)、has_window(有窗口)
- provides(提供)、priced_at(价格)、belongs_to(属于)、located_in(位于)

【示例】
文本："【一号餐厅】【窗口19】我爱我粥 - 小米南瓜粥：2元/杯"
三元组：
(一号餐厅, has_window, 19号我爱我粥)
(我爱我粥, provides, 小米南瓜粥)
(小米南瓜粥, priced_at, 2元)

请处理以下文本：
{text}

输出格式：每行一个三元组 (头实体, 关系, 尾实体)
"""

def create_knowledge_graph():
    """创建知识图谱索引"""

    load_dotenv()

    print("="*80)
    print("  龙子湖食堂知识图谱构建")
    print("="*80)

    # 配置
    DATA_DIR = os.getenv("DATA_DIR", "./data")
    SAVE_DIR = "./src/db/knowledge_graph"
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    # 初始化组件
    print("\n[1/5] 初始化 LLM 和 Embedding...")
    llm = Ollama(
        model="gemma3:12b",
        base_url=OLLAMA_BASE_URL,
        request_timeout=180.0,
        context_window=8192
    )

    embed_model = HuggingFaceEmbedding(
        model_name="BAAI/bge-small-zh-v1.5"  # 使用已有的中文模型，无需下载
    )

    # 设置全局配置
    Settings.llm = llm
    Settings.embed_model = embed_model
    Settings.chunk_size = 512
    Settings.chunk_overlap = 20

    print("✓ LLM 和 Embedding 初始化完成")

    # 读取文档
    print("\n[2/5] 读取 PDF 文档...")
    documents = SimpleDirectoryReader(DATA_DIR).load_data()
    print(f"✓ 加载了 {len(documents)} 个文档")

    # 创建图存储
    print("\n[3/5] 初始化图存储...")
    graph_store = SimpleGraphStore()
    storage_context = StorageContext.from_defaults(graph_store=graph_store)
    print("✓ 图存储创建完成")

    # 创建知识图谱（耗时较长）
    print("\n[4/5] 从文档中提取知识图谱...")
    print("⏱️  预计耗时: 15-40 分钟（取决于文档大小和 LLM 速度）")
    print("提示: 使用自定义 Schema 提取食堂领域知识")

    # 创建自定义提示词模板
    kg_prompt = PromptTemplate(KG_TRIPLET_EXTRACT_TMPL)

    try:
        kg_index = KnowledgeGraphIndex.from_documents(
            documents,
            storage_context=storage_context,
            max_triplets_per_chunk=10,  # 增加到10个三元组（因为有明确 Schema）
            include_embeddings=True,    # 包含向量嵌入（混合检索）
            show_progress=True,         # 显示进度
            kg_triplet_extract_template=kg_prompt  # 使用自定义 Schema
        )
        print("✓ 知识图谱构建成功（已使用自定义 Schema）")
    except Exception as e:
        print(f"❌ 知识图谱构建失败: {e}")
        return None

    # 保存图谱
    print("\n[5/5] 保存知识图谱...")
    os.makedirs(SAVE_DIR, exist_ok=True)
    kg_index.storage_context.persist(persist_dir=SAVE_DIR)
    print(f"✓ 知识图谱已保存到: {SAVE_DIR}")

    print("\n" + "="*80)
    print("✅ 知识图谱创建完成！")
    print("="*80)

    return kg_index


def test_knowledge_graph():
    """测试知识图谱查询"""

    print("\n" + "="*80)
    print("  测试知识图谱查询")
    print("="*80)

    SAVE_DIR = "./src/db/knowledge_graph"

    # 检查是否存在
    if not os.path.exists(SAVE_DIR):
        print("❌ 知识图谱不存在，请先运行创建")
        return

    # 加载图谱
    print("\n[1/2] 加载知识图谱...")
    from llama_index.core import load_index_from_storage

    storage_context = StorageContext.from_defaults(persist_dir=SAVE_DIR)
    kg_index = load_index_from_storage(storage_context)
    print("✓ 知识图谱加载成功")

    # 创建查询引擎
    print("\n[2/2] 创建查询引擎...")
    query_engine = kg_index.as_query_engine(
        include_text=True,              # 包含原始文本
        response_mode="tree_summarize", # 树形总结模式
        embedding_mode="hybrid",        # 混合检索
        similarity_top_k=5
    )
    print("✓ 查询引擎创建成功")

    # 测试查询
    test_queries = [
        "龙子湖校区有几个食堂？",
        "一号餐厅有哪些窗口？",
        "哪里可以买到2元的粥？"
    ]

    print("\n" + "="*80)
    print("开始测试查询")
    print("="*80)

    for i, query in enumerate(test_queries, 1):
        print(f"\n【问题 {i}】{query}")
        print("-" * 80)

        try:
            response = query_engine.query(query)
            print(f"答案:\n{response}")
        except Exception as e:
            print(f"查询失败: {e}")

        print("-" * 80)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "test":
        # 测试模式
        test_knowledge_graph()
    else:
        # 创建模式
        print("\n提示: 知识图谱构建是计算密集型任务")
        print("如果你已经有向量数据库，建议先完成 A/B 测试")
        print("知识图谱可以作为进阶优化\n")

        user_input = input("是否继续创建知识图谱？(y/n): ")
        if user_input.lower() == 'y':
            kg_index = create_knowledge_graph()

            if kg_index:
                print("\n知识图谱创建成功！现在进行测试...")
                test_knowledge_graph()
        else:
            print("\n已取消。")
            print("你可以先运行: python test_ab_simple.py 3")
            print("完成向量检索测试后再回来构建知识图谱")

