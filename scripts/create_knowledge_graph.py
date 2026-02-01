"""
创建防洪预案知识图谱 - 基于 LlamaIndex
使用 LLM 自动从文档中抽取三元组
"""
import os
import sys

# Windows path fix & Encoding fix
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from typing import List, Tuple
from pathlib import Path
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
from llama_index.readers.file import PDFReader

# 导入自定义 Schema
sys.path.append(str(Path(__file__).resolve().parent.parent))
from src.schema.flood_schema import FloodSchema

# 使用 Schema 生成的 Prompt
KG_TRIPLET_EXTRACT_TMPL = FloodSchema.get_prompt_template()

def create_knowledge_graph():
    """创建知识图谱索引"""

    load_dotenv()

    print("="*80)
    print("  防洪预案知识图谱构建 (Phase 3) - OneKE Powered")
    print("="*80)

    # 配置
    # 强制使用 PDF 目录 (OneKE 需要原始 PDF 来保持表格结构)
    # 注意：之前的实验可能将 DATA_DIR 指向了 txt 目录，这里我们需要纠正
    DATA_DIR = "./data/防洪预案" 
    SAVE_DIR = "./src/db/knowledge_graph"
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    
    # 确保保存目录存在
    Path(SAVE_DIR).mkdir(parents=True, exist_ok=True)

    # 初始化组件
    print("\n[1/5] 初始化 LLM (OneKE) 和 Embedding...")
    llm = Ollama(
        model="oneke",  # 使用 OneKE 专用模型
        base_url=OLLAMA_BASE_URL,
        request_timeout=60.0, # 用户要求: 60秒超时
        context_window=1024, # 极限压缩 Context
        temperature=0.1      # 抽取任务需要低温度
    )

    embed_model = HuggingFaceEmbedding(
        model_name="BAAI/bge-small-zh-v1.5",
        device="cpu"
    )

    # 设置全局配置
    Settings.llm = llm
    Settings.embed_model = embed_model
    Settings.chunk_size = 512
    Settings.chunk_overlap = 50 

    print("✓ LLM 和 Embedding 初始化完成")
    
    # 定义自定义抽取函数 (Closure to capture OneKE prompt logic)
    def oneke_extract_fn(text: str) -> List[tuple]:
        try:
            # 经过测试，OneKE 对最简单的 Prompt 响应最好
            safe_text = text[:600]  # 稍微增加文本长度
            full_prompt = f"抽取实体关系：\n{safe_text}\n输出："
            
            response = llm.complete(full_prompt).text
            triplets = FloodSchema.parse_oneke_response(response)
            return triplets
        except Exception as e:
            # 静默失败，保证主循环不退
            print(f" [Ex:{str(e)[:20]}]", end="", flush=True) 
            return []

    import hashlib

    # 读取文档
    print(f"\n[2/5] 读取文档... (目录: {DATA_DIR})")
    
    # 强制使用显式 PDF 解析器以确保按页读取 (解决 Only 7 docs loaded 问题)
    parser = PDFReader(return_full_document=False)
    reader = SimpleDirectoryReader(DATA_DIR, file_extractor={".pdf": parser}, recursive=True)
    documents = reader.load_data()
    
    print(f"✓ 加载了 {len(documents)} 个文档对象 (预期应为 ~500+ 页)")
    
    # 彻底移除旧的 fallback 逻辑，既然显式解析已生效
    if len(documents) < 20:
        print("⚠️ 异常警告：文档数量仍然过少！请检查 data 目录下是否真的只有 7 个文件且没有页码信息。")
    else:
        print(f"✓ 文档分页正常 (Avg size: {len(documents[0].text) if documents else 0} chars)")

    # 【关键修正】强制统一 doc_id，防止每次运行ID变化导致重复计算
    for doc in documents:
        # 使用文件路径+文件内索引做hash作为ID
        # doc.metadata['file_path'] 是绝对路径，不同机器可能不同，但在同一机器上是稳定的
        unique_str = doc.metadata.get('file_path', '') + str(doc.metadata.get('page_label', ''))
        doc.id_ = hashlib.md5(unique_str.encode('utf-8')).hexdigest()

    print(f"✓ 加载了 {len(documents)} 个文档片段")

    # 创建图存储
    print("\n[3/5] 初始化图存储...")
    graph_store = SimpleGraphStore()
    storage_context = StorageContext.from_defaults(graph_store=graph_store)
    print("✓ 图存储创建完成")

    # 创建知识图谱（增量构建模式）
    print("\n[4/5] 从文档中提取知识图谱 (增量模式)...")
    print("⏱️  注意：每处理 5 个文档自动保存一次...")

    from llama_index.core import load_index_from_storage
    
    # 尝试加载已有索引
    try:
        if os.path.exists(SAVE_DIR) and os.listdir(SAVE_DIR):
            print("Found existing index, loading...", flush=True)
            storage_context = StorageContext.from_defaults(persist_dir=SAVE_DIR)
            print("Storage context loaded.", flush=True)
            kg_index = load_index_from_storage(storage_context)
            print("Index structure loaded from disk.", flush=True)
            already_processed = len(kg_index.docstore.docs)
            print(f"Loaded {already_processed} processed documents.", flush=True)
        else:
            kg_index = KnowledgeGraphIndex.from_documents(
                [],
                storage_context=storage_context,
                max_triplets_per_chunk=15, 
                kg_triplet_extract_fn=oneke_extract_fn,
                include_embeddings=True
            )
    except Exception as e:
        print(f"Could not load index, creating new: {e}")
        kg_index = KnowledgeGraphIndex.from_documents(
            [],
            storage_context=storage_context,
            max_triplets_per_chunk=15, 
            kg_triplet_extract_fn=oneke_extract_fn,
            include_embeddings=True
        )

    # 逐个/分批处理文档并保存
    total_docs = len(documents)
    
    # 获取已处理的文档ID列表 (简单去重逻辑)
    # 建立已处理文档的特征集合（基于文件路径+页码），用于不依赖 doc_id 的去重(Smart Resume)
    processed_signatures = set()
    if 'kg_index' in locals() and hasattr(kg_index, 'docstore'):
        print("Building index of processed documents for smart resume...", flush=True)
        for doc_id, doc in kg_index.docstore.docs.items():
            if hasattr(doc, 'metadata'):
                f_path = doc.metadata.get('file_path')
                p_label = doc.metadata.get('page_label')
                # 兼容部分没有 metadata 的情况
                if f_path: 
                    processed_signatures.add((str(f_path), str(p_label)))
        print(f"✓ Identify {len(processed_signatures)} processed pages (ignoring ID mismatch).", flush=True)

    batch_size = 5
    for i in range(0, total_docs, batch_size):
        batch_docs = documents[i : i + batch_size]
        
        # 检查是否已处理
        new_docs = []
        for doc in batch_docs:
            # 特征指纹: 用于跨 ID 匹配
            doc_sig = (str(doc.metadata.get('file_path')), str(doc.metadata.get('page_label')))
            
            # 如果 ID 存在 OR 指纹存在，都视为已处理
            if kg_index.docstore.document_exists(doc.doc_id):
                continue
            if doc_sig in processed_signatures:
                continue
                
            new_docs.append(doc)
        
        if not new_docs:
            print(f"Skipping batch {i} (already processed)", flush=True)
            continue
            
        print(f"Processing batch {i}/{total_docs} ({len(new_docs)} new docs)...", flush=True)
        
        # 插入新文档
        for doc in new_docs:
            try:
                kg_index.insert(doc)
            except Exception as e:
                print(f"Error inserting doc {doc.doc_id}: {e}")
        
        # 保存
        print(f"Saving progress to {SAVE_DIR}...")
        kg_index.storage_context.persist(persist_dir=SAVE_DIR)

    print("✓ 知识图谱提取完成")
    
    print("\n" + "="*80)
    print(f"✅ 完成！知识图谱已保存至: {SAVE_DIR}")
    print("现在可以使用 scripts/test_kg_retrieval.py (需创建) 进行测试")
    print("="*80)

if __name__ == "__main__":
    create_knowledge_graph()

