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
from src.contextual_retrieval.entity_fusion import normalize_triplets

# 使用 Schema 生成的 v2 Prompt（已传给 LLM，不再是摆设）
KG_TRIPLET_EXTRACT_TMPL = FloodSchema.get_prompt_template()


def rule_based_to_triplets(text: str) -> List[tuple]:
    """
    将 FloodSchema.extract_rule_based() 的结构化槽位转换为 v2 Schema 三元组。
    这是规则抽取的主路径：高召回、无需LLM、专攻数值/时限/响应级别。
    """
    import re
    # 直接使用 Schema 中的编译好的正则模式（避免 ctx.find 子串误配问题）
    from src.schema.flood_schema import (RULE_NUMERIC, RULE_DEADLINE,
                                          RULE_RESPONSE_LEVEL, RULE_TRIGGER)
    triplets = []

    # ── 1. 识别设施名（作为三元组主语）──────────────────────
    facility_pattern = re.compile(
        r'((?:常庄|杨家横|[^\s，。、]{2,6}?)(?:水库|水闸|堤防|堤坝|泵站|水文站|拦河坝))'
    )
    facilities = list({m.group(1) for m in facility_pattern.finditer(text)})

    # ── 2. 水位/库容数值 → (设施, has_threshold, 属性+值+单位) ──
    water_level_keywords = ["汛限水位", "正常蓄水位", "死水位", "校核洪水位",
                            "设计洪水位", "警戒水位", "保证水位", "坝顶高程"]
    capacity_keywords = ["总库容", "兴利库容", "调洪库容", "死库容", "防洪库容"]
    all_attr_kw = water_level_keywords + capacity_keywords

    for m in RULE_NUMERIC.finditer(text):
        abs_pos = m.start()                       # 数值在原文中的绝对位置
        ctx_s = max(0, abs_pos - 25)
        ctx_e = min(len(text), m.end() + 25)
        ctx = text[ctx_s:ctx_e]
        val_str = m.group(0)                      # e.g., "298.50m"
        val_pos_in_ctx = abs_pos - ctx_s          # 精确位置，不依赖 find()

        # 找距离数值最近（≤15字）的属性关键词
        best_attr, best_dist = None, 999
        for kw in all_attr_kw:
            kw_pos = ctx.find(kw)
            if kw_pos >= 0:
                dist = abs(kw_pos - val_pos_in_ctx)
                if dist < best_dist:
                    best_dist, best_attr = dist, kw
        attr_found = best_attr if best_dist <= 15 else None

        # 找当前 chunk 最近的设施名
        fac_in_ctx = next((f for f in facilities if f in ctx),
                          facilities[0] if facilities else None)

        if attr_found and fac_in_ctx:
            triplets.append((fac_in_ctx, "has_threshold", f"{attr_found}{val_str}"))
        elif fac_in_ctx and m.group(2) in ("米", "m", "m³", "万m³", "亿m³", "万方"):
            triplets.append((fac_in_ctx, "has_threshold", val_str))

    # ── 3. 响应级别 + 数值 → (响应级别, triggered_by, 阈值) ──
    slots = FloodSchema.extract_rule_based(text)
    for level in slots["response_levels"]:
        for m in RULE_NUMERIC.finditer(text):
            ctx_around = text[max(0, m.start()-40): m.end()+40]
            if level in ctx_around or any(kw in ctx_around for kw in ["达到", "超过", "水位", "雨量"]):
                triplets.append((level, "triggered_by", m.group(0)))
                break

    # ── 4. 时限 → (动作, deadline, 时限值) ──
    action_pattern = re.compile(r'(上报|报告|通知|转移|撤离|巡查|开闸|关闸|处置|处理|启动|发布|响应)')
    for m in RULE_DEADLINE.finditer(text):
        raw = m.group(0)
        ctx = text[max(0, m.start()-30): m.end()+10]
        action_m = action_pattern.search(ctx)
        if action_m:
            triplets.append((action_m.group(1), "deadline", raw))

    # ── 5. 响应级别 + 组织 → (组织, responsible, 响应级别) ──
    org_pattern = re.compile(
        r'(防汛指挥部|水利局|水务局|乡镇政府|村委会|应急管理局|[^\s，。]{2,8}?(?:局|部|办|委|组))'
    )
    for level in slots["response_levels"]:
        for m in org_pattern.finditer(text):
            org = m.group(1)
            sent_start = max(0, text.rfind("。", 0, m.start()) + 1)
            sent_end = text.find("。", m.end())
            sent_end = sent_end if sent_end > 0 else len(text)
            if level in text[sent_start:sent_end]:
                triplets.append((org, "responsible", level))
                break

    return triplets

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
    KG_CTX_WINDOW = int(os.getenv("KG_CTX_WINDOW", "1024"))
    KG_SAFE_TEXT_CHARS = int(os.getenv("KG_SAFE_TEXT_CHARS", "400"))
    KG_CHUNK_SIZE = int(os.getenv("KG_CHUNK_SIZE", "512"))
    KG_CHUNK_OVERLAP = int(os.getenv("KG_CHUNK_OVERLAP", "50"))
    KG_MAX_TRIPLETS = int(os.getenv("KG_MAX_TRIPLETS", "15"))
    KG_INCLUDE_EMBEDDINGS = os.getenv("KG_INCLUDE_EMBEDDINGS", "1") == "1"
    KG_ENABLE_LLM = os.getenv("KG_ENABLE_LLM", "1") == "1"
    
    # 确保保存目录存在
    Path(SAVE_DIR).mkdir(parents=True, exist_ok=True)

    # 初始化组件
    print("\n[1/5] 初始化 LLM (OneKE) 和 Embedding...")
    llm = Ollama(
        model="oneke",  # 使用 OneKE 专用模型
        base_url=OLLAMA_BASE_URL,
        request_timeout=60.0,  # 用户要求: 60秒超时
        context_window=KG_CTX_WINDOW,
        temperature=0.1      # 抽取任务需要低温度
    )

    embed_model = HuggingFaceEmbedding(
        model_name="BAAI/bge-small-zh-v1.5",
        device="cpu"
    )

    # 设置全局配置
    Settings.llm = llm
    Settings.embed_model = embed_model
    Settings.chunk_size = KG_CHUNK_SIZE
    Settings.chunk_overlap = KG_CHUNK_OVERLAP

    print(f"  KG_CTX_WINDOW={KG_CTX_WINDOW}")
    print(f"  KG_SAFE_TEXT_CHARS={KG_SAFE_TEXT_CHARS}")
    print(f"  KG_CHUNK_SIZE={KG_CHUNK_SIZE}")
    print(f"  KG_CHUNK_OVERLAP={KG_CHUNK_OVERLAP}")
    print(f"  KG_MAX_TRIPLETS={KG_MAX_TRIPLETS}")
    print(f"  KG_INCLUDE_EMBEDDINGS={KG_INCLUDE_EMBEDDINGS}")
    print(f"  KG_ENABLE_LLM={KG_ENABLE_LLM}")

    print("✓ LLM 和 Embedding 初始化完成")
    
    # 定义自定义抽取函数 - 双路径：规则（主）+ LLM（辅）
    def oneke_extract_fn(text: str) -> List[tuple]:
        all_triplets = []

        # ── 路径1（主）：规则抽取，专攻数值/时限/响应级别 ──────────
        # 不依赖模型能力，高召回，产出 v2 Schema 三元组
        try:
            rule_triplets = rule_based_to_triplets(text)
            all_triplets.extend(rule_triplets)
        except Exception as e:
            print(f" [Rule-Ex:{str(e)[:20]}]", end="", flush=True)

        # ── 路径2（辅）：LLM 用 v2 Schema Prompt 抽取非结构化关系 ──
        # 只对含有触发词/组织/动作的文本启用，减少模型调用次数
        try:
            import re as _re
            has_useful_content = _re.search(
                r'指挥|负责|启动|执行|应急|防汛|预警|上报|转移|巡查', text
            )
            if KG_ENABLE_LLM and has_useful_content:
                safe_text = text[:KG_SAFE_TEXT_CHARS]
                # 使用 v2 Schema Prompt（替换占位符）
                v2_prompt = KG_TRIPLET_EXTRACT_TMPL.replace("{text}", safe_text)
                response = llm.complete(v2_prompt).text
                llm_triplets = FloodSchema.parse_oneke_response(response)
                # 过滤掉无意义的 related_to
                llm_triplets = [t for t in llm_triplets if t[1] != "related_to"]
                all_triplets.extend(llm_triplets)
        except Exception as e:
            print(f" [LLM-Ex:{str(e)[:20]}]", end="", flush=True)

        # ── 合并：实体融合归一化 + 去重 ─────────────────────────
        if all_triplets:
            all_triplets = normalize_triplets(all_triplets)
            # 只过滤关系名完全不在 Schema 里的三元组
            # 不检查 domain/range 类型（实体识别启发式太严，会误杀人名/设施主语）
            valid_preds = set(FloodSchema.RELATION_TYPES.keys())
            all_triplets = [(s, p, o) for s, p, o in all_triplets
                            if p in valid_preds]
        return all_triplets

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
            # 确保 resume 时仍使用自定义抽取函数
            try:
                kg_index._kg_triplet_extract_fn = oneke_extract_fn
            except Exception:
                pass
        else:
            kg_index = KnowledgeGraphIndex.from_documents(
                [],
                storage_context=storage_context,
                max_triplets_per_chunk=KG_MAX_TRIPLETS,
                kg_triplet_extract_fn=oneke_extract_fn,
                include_embeddings=KG_INCLUDE_EMBEDDINGS
            )
    except Exception as e:
        print(f"Could not load index, creating new: {e}")
        kg_index = KnowledgeGraphIndex.from_documents(
            [],
            storage_context=storage_context,
            max_triplets_per_chunk=KG_MAX_TRIPLETS,
            kg_triplet_extract_fn=oneke_extract_fn,
            include_embeddings=KG_INCLUDE_EMBEDDINGS
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

