"""
OneKE Schema 设计 - 食堂领域知识图谱

导师的意思是：你需要预先定义"食堂领域"的实体类型和关系类型
这样 OneKE/LLM 才知道要抽取什么样的三元组
"""

# ============================================================================
# 第一部分：定义 Schema（概念模型）
# ============================================================================

# 食堂领域的实体类型（Entity Types）
ENTITY_TYPES = {
    "校区": "Campus",           # 例如：龙子湖校区
    "食堂": "Canteen",          # 例如：一号餐厅、二号餐厅
    "楼层": "Floor",            # 例如：一楼、二楼
    "窗口": "Window",           # 例如：19号我爱我粥
    "档口": "Stall",            # 例如：天津包子、烤盘饭
    "食品": "Food",             # 例如：小米南瓜粥、招牌鲜肉包
    "价格": "Price",            # 例如：2元、1.5元
    "类别": "Category"          # 例如：粥、包子、面条
}

# 关系类型（Relation Types）
RELATION_TYPES = {
    "有食堂": "has_canteen",         # 校区 → 食堂
    "有楼层": "has_floor",           # 食堂 → 楼层
    "有窗口": "has_window",          # 食堂/楼层 → 窗口
    "提供": "provides",              # 窗口/档口 → 食品
    "价格为": "priced_at",           # 食品 → 价格
    "属于类别": "belongs_to",        # 食品 → 类别
    "位于": "located_in"             # 窗口 → 楼层
}

# ============================================================================
# 第二部分：为 LlamaIndex 定义 Schema Prompt
# ============================================================================

from llama_index.core import PromptTemplate

# 定义知识抽取的 Schema 提示词
KG_EXTRACTION_PROMPT = """
你是一个专门从食堂菜单中提取知识图谱的助手。

请从以下文本中提取实体和关系，构建三元组 (头实体, 关系, 尾实体)。

【实体类型】
- 校区：如"龙子湖校区"
- 食堂：如"一号餐厅"、"二号餐厅"
- 楼层：如"一楼"、"二楼"
- 窗口：如"19号我爱我粥"、"21号天津包子"
- 档口：窗口的具体名称，如"我爱我粥"、"天津包子"
- 食品：具体菜品，如"小米南瓜粥"、"招牌鲜肉包"
- 价格：如"2元"、"1.5元"
- 类别：如"粥类"、"包子类"

【关系类型】
- has_canteen：校区拥有食堂
- has_floor：食堂有楼层
- has_window：食堂/楼层有窗口
- provides：窗口/档口提供食品
- priced_at：食品的价格
- belongs_to：食品属于某类别
- located_in：窗口位于某楼层

【示例】
文本：
"【一号餐厅】【窗口19】我爱我粥
- 小米南瓜粥：2元/杯
- 清火绿豆粥：2元/杯"

输出三元组：
1. (龙子湖校区, has_canteen, 一号餐厅)
2. (一号餐厅, has_window, 19号我爱我粥)
3. (我爱我粥, provides, 小米南瓜粥)
4. (小米南瓜粥, priced_at, 2元)
5. (小米南瓜粥, belongs_to, 粥类)
6. (我爱我粥, provides, 清火绿豆粥)
7. (清火绿豆粥, priced_at, 2元)
8. (清火绿豆粥, belongs_to, 粥类)

现在请处理以下文本：
{text}

请以 (头实体, 关系, 尾实体) 的格式输出，每行一个三元组。
"""

# ============================================================================
# 第三部分：实际代码 - 使用 LlamaIndex 提取知识图谱
# ============================================================================

from llama_index.core import KnowledgeGraphIndex, SimpleDirectoryReader
from llama_index.llms.ollama import Ollama
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core.graph_stores import SimpleGraphStore
from llama_index.core import StorageContext
import os
from dotenv import load_dotenv

def create_kg_with_custom_schema():
    """使用自定义 Schema 创建知识图谱"""

    load_dotenv()

    print("="*80)
    print("使用自定义 Schema 创建食堂知识图谱")
    print("="*80)

    # 1. 初始化 LLM
    llm = Ollama(
        model="gemma3:12b",
        base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        request_timeout=180.0
    )

    # 2. 初始化 Embedding
    embed_model = HuggingFaceEmbedding(
        model_name="BAAI/bge-base-en-v1.5"
    )

    # 3. 读取文档
    documents = SimpleDirectoryReader("./data").load_data()
    print(f"✓ 加载了 {len(documents)} 个文档")

    # 4. 创建自定义提示词模板
    kg_prompt = PromptTemplate(KG_EXTRACTION_PROMPT)

    # 5. 创建图存储
    graph_store = SimpleGraphStore()
    storage_context = StorageContext.from_defaults(graph_store=graph_store)

    # 6. 使用自定义 Schema 创建知识图谱
    print("\n开始提取知识图谱（使用自定义 Schema）...")

    kg_index = KnowledgeGraphIndex.from_documents(
        documents,
        llm=llm,
        embed_model=embed_model,
        storage_context=storage_context,
        max_triplets_per_chunk=10,      # 每个文本块最多提取10个三元组
        include_embeddings=True,
        show_progress=True,
        # 关键：使用自定义提示词
        kg_triplet_extract_template=kg_prompt
    )

    print("✓ 知识图谱创建完成")

    # 7. 保存
    kg_index.storage_context.persist(persist_dir="./src/db/knowledge_graph")
    print("✓ 已保存到 ./src/db/knowledge_graph")

    return kg_index


# ============================================================================
# 第四部分：如果使用 OneKE（外部工具）
# ============================================================================

"""
如果你要用 OneKE（而不是 LlamaIndex 内置抽取），流程如下：

步骤1：安装 OneKE
pip install oneke

步骤2：定义 Schema 给 OneKE
"""

# OneKE Schema 定义（JSON 格式）
ONEKE_SCHEMA = {
    "entity_types": [
        {"type": "校区", "description": "大学校区"},
        {"type": "食堂", "description": "学生食堂"},
        {"type": "窗口", "description": "食堂档口窗口"},
        {"type": "食品", "description": "菜品"},
        {"type": "价格", "description": "价格"}
    ],
    "relation_types": [
        {"type": "has_canteen", "head": "校区", "tail": "食堂"},
        {"type": "has_window", "head": "食堂", "tail": "窗口"},
        {"type": "provides", "head": "窗口", "tail": "食品"},
        {"type": "priced_at", "head": "食品", "tail": "价格"}
    ]
}

"""
步骤3：使用 OneKE 提取三元组
"""

def extract_with_oneke(text):
    """使用 OneKE 提取三元组"""

    # 注意：这是伪代码，OneKE 的实际 API 可能不同
    # 请参考 OneKE 官方文档

    from oneke import OneKE

    # 初始化 OneKE，传入 Schema
    extractor = OneKE(
        model="oneke-v1",
        schema=ONEKE_SCHEMA  # 关键：传入你定义的 Schema
    )

    # 提取三元组
    triplets = extractor.extract(text)

    # 返回格式：[(头实体, 关系, 尾实体), ...]
    return triplets


"""
步骤4：将 OneKE 的三元组导入 LlamaIndex
"""

def import_oneke_to_llamaindex(triplets):
    """将 OneKE 提取的三元组导入 LlamaIndex"""

    from llama_index.core import KnowledgeGraphIndex
    from llama_index.core.graph_stores import SimpleGraphStore

    # 创建图存储
    graph_store = SimpleGraphStore()

    # 添加三元组到图中
    for head, relation, tail in triplets:
        graph_store.add_triplet(head, relation, tail)

    # 创建索引
    kg_index = KnowledgeGraphIndex(
        nodes=[],  # 空节点，因为我们直接用三元组
        graph_store=graph_store
    )

    return kg_index


# ============================================================================
# 第五部分：完整示例 - OneKE + LlamaIndex 集成
# ============================================================================

def full_workflow_oneke_llamaindex():
    """完整流程：OneKE 提取 + LlamaIndex 索引"""

    print("="*80)
    print("OneKE + LlamaIndex 完整工作流")
    print("="*80)

    # Step 1: 读取 PDF
    from llama_index.core import SimpleDirectoryReader
    documents = SimpleDirectoryReader("./data").load_data()

    all_triplets = []

    # Step 2: 对每个文档用 OneKE 提取三元组
    print("\n[1/3] 使用 OneKE 提取三元组...")
    for doc in documents:
        triplets = extract_with_oneke(doc.text)
        all_triplets.extend(triplets)

    print(f"✓ 提取了 {len(all_triplets)} 个三元组")

    # Step 3: 导入到 LlamaIndex
    print("\n[2/3] 导入到 LlamaIndex 知识图谱...")
    kg_index = import_oneke_to_llamaindex(all_triplets)
    print("✓ 知识图谱创建完成")

    # Step 4: 保存
    print("\n[3/3] 保存知识图谱...")
    kg_index.storage_context.persist(persist_dir="./src/db/knowledge_graph")
    print("✓ 已保存")

    return kg_index


# ============================================================================
# 使用说明
# ============================================================================

if __name__ == "__main__":
    """
    方式1：使用 LlamaIndex 内置抽取（推荐，更简单）
    """
    # kg_index = create_kg_with_custom_schema()

    """
    方式2：使用 OneKE 外部抽取（更精确，需要额外安装）
    """
    # kg_index = full_workflow_oneke_llamaindex()

    print("""
    
    ========================================================================
    总结：Schema 的作用
    ========================================================================
    
    1. **定义实体类型**：告诉模型要抽取哪些类型的实体
       - 例如：食堂、窗口、食品、价格
    
    2. **定义关系类型**：告诉模型实体之间有哪些关系
       - 例如：has_window（食堂→窗口）、provides（窗口→食品）
    
    3. **提供领域知识**：让模型理解"食堂领域"的特定概念
       - 而不是通用的实体和关系
    
    4. **提高抽取质量**：有了 Schema，模型知道要找什么，准确率更高
    
    ========================================================================
    你需要做什么？
    ========================================================================
    
    1. 根据你的食堂数据，设计 Schema（已经帮你做好了）
    2. 选择一种方式：
       - 方式A：用 LlamaIndex 内置抽取（简单）
       - 方式B：用 OneKE 抽取（精确，需学习 OneKE API）
    3. 运行脚本，生成知识图谱
    4. 测试查询效果
    
    ========================================================================
    建议：先用方式A（LlamaIndex 内置），成功后再考虑 OneKE
    ========================================================================
    """)

