from llama_index.core import SimpleDirectoryReader
from llama_index.core.node_parser import TokenTextSplitter
from llama_index.llms.ollama import Ollama
from .save_vectordb import save_chromadb
from .save_bm25 import save_BM25
import os
import json
import hashlib
from collections import defaultdict

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
    print(f"Loading documents from {DATA_DIR}...")
    reader = SimpleDirectoryReader(input_dir=DATA_DIR)
    documents = reader.load_data()
    
    # Group documents by file_path to handle context correctly
    docs_by_file = defaultdict(list)
    for doc in documents:
        # Fallback to 'unknown' if metadata is missing
        file_path = doc.metadata.get('file_path', 'unknown_file')
        docs_by_file[file_path].append(doc)

    print(f"Loaded {len(documents)} pages from {len(docs_by_file)} files.")

    # Initializing text splitter
    splitter = TokenTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separator=" ",
    )

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

    # Setup Cache if LLM is active
    context_cache = {}
    cache_file = os.path.join(save_dir, "context_cache.json")
    
    if llm and os.path.exists(cache_file):
        print(f"Loading existing context cache from {cache_file}...")
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                context_cache = json.load(f)
            print(f"Loaded {len(context_cache)} cached items.")
        except Exception as e:
            print(f"Error loading cache: {e}")

    all_nodes = []
    
    processed_files_count = 0
    total_files = len(docs_by_file)
    
    # Process each file individually
    for file_path, file_docs in docs_by_file.items():
        processed_files_count += 1
        file_name = os.path.basename(file_path)
        
        # Construct WHOLE DOCUMENT context from this file only
        file_content = "\n".join([d.text for d in file_docs])
        
        # Split this file into nodes
        file_nodes = splitter.get_nodes_from_documents(file_docs)
        print(f"File [{processed_files_count}/{total_files}]: {file_name} -> {len(file_nodes)} chunks")
        
        if llm:
            for i, node in enumerate(file_nodes):
                content_body = node.text
                content_hash = hashlib.md5(content_body.encode('utf-8')).hexdigest()
                
                if content_hash in context_cache:
                    node.text = context_cache[content_hash]
                    # print(f"  [Cache] Chunk {i+1}")
                else:
                    print(f"  [LLM] Generating context for chunk {i+1}/{len(file_nodes)}...")
                    prompt = template.format(WHOLE_DOCUMENT=file_content, CHUNK_CONTENT=content_body)
                    
                    try:
                        llm_response = llm.complete(prompt)
                        # Ensure there is a separation between context and original content
                        contextual_text = llm_response.text + "\n\n" + content_body 
                        
                        node.text = contextual_text
                        context_cache[content_hash] = contextual_text
                        
                        # Save cache periodically
                        if len(context_cache) % 10 == 0:
                            with open(cache_file, 'w', encoding='utf-8') as f:
                                json.dump(context_cache, f, ensure_ascii=False, indent=2)
                                
                    except Exception as e:
                        print(f"  ❌ Error generating context: {e}")
        
        all_nodes.extend(file_nodes)

    # Final Save Cache
    if llm:
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(context_cache, f, ensure_ascii=False, indent=2)

    if not llm:
        print("SKIP_CONTEXT_LLM=1: Used raw chunks without context.")
    
    vectordb_name = db_name + "_vectordb"
    bm25db_name = db_name + "_bm25"
    
    # Saving the Vector Database and BM25 Database
    print(f"Saving ChromaDB: {vectordb_name} with {len(all_nodes)} nodes...")
    save_chromadb(nodes=all_nodes, 
                  save_dir=save_dir, 
                  db_name=vectordb_name, 
                  collection_name=collection_name)
    
    print(f"Saving BM25: {bm25db_name}...")
    save_BM25(nodes=all_nodes, 
              save_dir=save_dir, 
              db_name=bm25db_name)
