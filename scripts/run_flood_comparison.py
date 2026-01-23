"""
防洪预案 - Contextual Retrieval 效果对比脚本
对比 Baseline (无上下文) 和 Contextual (有上下文) 的检索结果
"""
import os
import sys
import json
import time
from pathlib import Path

# Fix Windows encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from dotenv import load_dotenv

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parents[1]))

from llama_index.core import VectorStoreIndex, QueryBundle
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.retrievers.bm25 import BM25Retriever
from llama_index.core.retrievers import BaseRetriever
from llama_index.core.schema import NodeWithScore
import chromadb
import jieba
from typing import List

load_dotenv()

# Configuration
DB_PATH = os.getenv("VECTOR_DB_PATH", "./src/db/flood_prevention_db_vectordb")
BM25_PATH = os.getenv("BM25_DB_PATH", "./src/db/flood_prevention_db_bm25")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "flood_prevention_collection")

BASELINE_REPORT = Path(__file__).parent.parent / "results" / "flood_retrieval_report.json"
COMPARISON_REPORT = Path(__file__).parent.parent / "results" / "flood_comparison_report.md"

def chinese_tokenizer(text):
    return list(jieba.cut_for_search(text))

class HybridRetriever(BaseRetriever):
    def __init__(self, vector_retriever, bm25_retriever):
        self.vector_retriever = vector_retriever
        self.bm25_retriever = bm25_retriever
        super().__init__()

    def _retrieve(self, query_bundle: QueryBundle) -> List[NodeWithScore]:
        if self.vector_retriever:
            vector_results = self.vector_retriever.retrieve(query_bundle)
        else:
            vector_results = []
            
        if self.bm25_retriever:
            bm25_results = self.bm25_retriever.retrieve(query_bundle)
        else:
            bm25_results = []
        
        # Combine by ID to deduplicate
        all_nodes = {node.node_id: node for node in vector_results + bm25_results}
        
        sorted_nodes = sorted(
            all_nodes.values(), 
            key=lambda x: x.score if x.score else 0, 
            reverse=True
        )
        return sorted_nodes[:10]

def init_retrievers():
    print(f"Loading DB from: {DB_PATH}")
    embed_model = HuggingFaceEmbedding(
        model_name="BAAI/bge-small-zh-v1.5",
        device="cpu"
    )
    
    if not os.path.exists(DB_PATH):
        print(f"Error: Vector DB Path does not exist: {DB_PATH}")
        return None

    db = chromadb.PersistentClient(path=DB_PATH)
    try:
        chroma_collection = db.get_collection(COLLECTION_NAME)
    except Exception as e:
        print(f"Error loading collection {COLLECTION_NAME}: {e}")
        return None

    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
    vector_index = VectorStoreIndex.from_vector_store(vector_store, embed_model=embed_model)
    vector_retriever = vector_index.as_retriever(similarity_top_k=10)
    
    if os.path.exists(BM25_PATH):
        bm25_retriever = BM25Retriever.from_persist_dir(BM25_PATH)
        bm25_retriever._similarity_top_k = 10
    else:
        print("Warning: BM25 index not found, using vector only.")
        bm25_retriever = None 
        
    return HybridRetriever(vector_retriever, bm25_retriever)

def main():
    if not BASELINE_REPORT.exists():
        print(f"❌ Baseline report not found at {BASELINE_REPORT}")
        return

    print("Loading Baseline Results...")
    try:
        with open(BASELINE_REPORT, 'r', encoding='utf-8') as f:
            baseline_data = json.load(f)
    except Exception as e:
        print(f"Failed to load baseline report: {e}")
        return

    # Check for empty baseline
    if not baseline_data:
        print("Baseline data is empty.")
        return

    print("Initializing Retrieval on Current DB (Contextual)...")
    retriever = init_retrievers()
    if not retriever:
        print("Failed to initialize retriever. Is the DB built?")
        return

    md_output = "# Flood Prevention: Baseline vs Contextual Retrieval Comparison\n\n"
    md_output += "| Query | Baseline Top 1 (Preview) | Contextual Top 1 (Preview) |\n"
    md_output += "|-------|--------------------------|----------------------------|\n"
    
    print("\nRunning Comparison Test...\n")

    for item in baseline_data:
        query = item.get('query', 'Unknown Query')
        
        # Get Baseline Top 1
        baseline_top1_text = "N/A"
        if item.get('top_results') and len(item['top_results']) > 0:
            baseline_top1_text = item['top_results'][0].get('preview', 'N/A')
        elif item.get('top_3') and len(item['top_3']) > 0:
             baseline_top1_text = item['top_3'][0].get('text', 'N/A')
            
        
        # Get Contextual Result
        try:
            nodes = retriever.retrieve(QueryBundle(query))
            contextual_top1_text = "N/A"
            if nodes:
                # Contextual chunks have context prepended.
                contextual_top1_text = nodes[0].text.replace('\n', ' ')
        except Exception as e:
            print(f"Error retrieving for '{query}': {e}")
            contextual_top1_text = "Error"

            
        print(f"Q: {query}")
        print(f"  [Base]: {baseline_top1_text[:50]}...")
        print(f"  [Cont]: {contextual_top1_text[:50]}...")
        
        # Escape pipes for markdown table
        b_clean = baseline_top1_text[:150].replace('|', '\|').replace('\n', ' ')
        c_clean = contextual_top1_text[:150].replace('|', '\|').replace('\n', ' ')
        
        md_output += f"| {query} | {b_clean} | **{c_clean}** |\n"

    try:
        with open(COMPARISON_REPORT, 'w', encoding='utf-8') as f:
            f.write(md_output)
        print(f"\n✅ Comparison saved to {COMPARISON_REPORT}")
    except Exception as e:
        print(f"Error saving report: {e}")

if __name__ == "__main__":
    main()
