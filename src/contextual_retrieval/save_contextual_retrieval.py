from llama_index.core import SimpleDirectoryReader
from llama_index.core.node_parser import TokenTextSplitter
from llama_index.llms.ollama import Ollama
from .save_vectordb import save_chromadb
from .save_bm25 import save_BM25
import os

def create_and_save_db(
        data_dir: str, 
        collection_name : str, 
        save_dir: str, 
        db_name: str = "default",
        chunk_size: int = 512, 
        chunk_overlap: int =20
        ) -> None:

    # Path directory to data storage 
    DATA_DIR = data_dir

    # Hyperparameters for text splitting
    CHUNK_SIZE = chunk_size
    CHUNK_OVERLAP = chunk_overlap

    # 控制是否跳过LLM生成上下文（Windows上Ollama不一定可用）
    skip_llm = os.getenv("SKIP_CONTEXT_LLM", "0") == "1"

    llm = None
    if not skip_llm:
        # Initializing LLM for contextual retrieval
        # 支持从环境变量配置 Ollama 地址（用于连接 WSL）
        ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        llm = Ollama(
            model="gemma3:12b",
            base_url=ollama_base_url,
            request_timeout=120.0,
            context_window=8192
        )

    # Reading documents
    reader = SimpleDirectoryReader(input_dir=DATA_DIR)
    documents = reader.load_data()

    original_document_content = ""
    for page in documents:
        original_document_content += page.text

    # Initializing text splitter
    splitter = TokenTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separator=" ",
    )

    # Splitting documents to Nodes [text chunks]
    nodes = splitter.get_nodes_from_documents(documents)

    # Template referred from Anthropic Blog Post
    template = """
            <document> 
            {WHOLE_DOCUMENT} 
            </document> 
            Here is the chunk we want to situate within the whole document 
            <chunk> 
            {CHUNK_CONTENT} 
            </chunk> 
            Please give a short succinct context to situate this chunk within the overall document for the purposes of improving search retrieval of the chunk. 
            Answer only with the succinct context and nothing else. 
            """

    # Contextual Retrieval : Providing context to existing Nodes [text chunks]
    if llm:
        import hashlib
        import json
        
        # 缓存文件路径
        cache_file = os.path.join(save_dir, "context_cache.json")
        context_cache = {}
        
        # 加载已有缓存
        if os.path.exists(cache_file):
            print(f"Loading existing context cache from {cache_file}...")
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    context_cache = json.load(f)
                print(f"Loaded {len(context_cache)} cached items.")
            except Exception as e:
                print(f"Error loading cache: {e}")

        idx = 0
        nodes_count = len(nodes)
        
        for i, node in enumerate(nodes):
            content_body = node.text    
            
            # 使用内容哈希作为Key，确保稳定性
            content_hash = hashlib.md5(content_body.encode('utf-8')).hexdigest()

            if content_hash in context_cache:
                # 命中缓存
                print(f"[{i+1}/{nodes_count}] Using cached context for chunk.")
                contextual_text = context_cache[content_hash]
                node.text = contextual_text
            else:
                # 调用LLM
                print(f"[{i+1}/{nodes_count}] Generating context with LLM...")
                prompt = template.format(WHOLE_DOCUMENT=original_document_content, 
                                        CHUNK_CONTENT=content_body)
                
                try:
                    llm_response = llm.complete(prompt)
                    # 组合结果
                    contextual_text = llm_response.text + content_body
                    
                    # 更新节点
                    node.text = contextual_text
                    
                    # 写入缓存
                    context_cache[content_hash] = contextual_text
                    
                    # 实时打印（可选）
                    print(f'Context response => {llm_response.text[:100]}...')
                    
                    # 每生成 5 个就保存一次文件，防止全盘丢失
                    if i % 5 == 0:
                        with open(cache_file, 'w', encoding='utf-8') as f:
                            json.dump(context_cache, f, ensure_ascii=False, indent=2)
                            
                except Exception as e:
                    print(f"Error generating context for chunk {i}: {e}")
                    # 出错时跳过更新，保留原文本或处理异常
                    pass
            
            idx += 1
            
        # 最后再保存一次缓存
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(context_cache, f, ensure_ascii=False, indent=2)
            
    else:
        print("SKIP_CONTEXT_LLM=1: 跳过LLM上下文生成，直接使用原始分块构建索引")
    
    vectordb_name = db_name + "_vectordb"
    bm25db_name = db_name + "_bm25"
    
    # Saving the Vector Database and BM25 Database
    save_chromadb(nodes=nodes, 
                  save_dir=save_dir, 
                  db_name=vectordb_name, 
                  collection_name=collection_name)
    
    save_BM25(nodes=nodes, 
              save_dir=save_dir, 
              db_name=bm25db_name)
