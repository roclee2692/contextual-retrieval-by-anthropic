from llama_index.core import VectorStoreIndex
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.retrievers.bm25 import BM25Retriever
from llama_index.core import QueryBundle
from llama_index.core.schema import NodeWithScore
from llama_index.core.retrievers import BaseRetriever
import chromadb
import Stemmer
from typing import List
import os
from dotenv import load_dotenv
load_dotenv()


def chinese_tokenizer(text: str):
    """Tokenizer consistent with save_bm25.py (jieba search mode + simple expansion)."""
    import jieba
    tokens = list(jieba.cut_for_search(text))
    enhanced_tokens = []
    for token in tokens:
        enhanced_tokens.append(token)
        if "包" in token:
            enhanced_tokens.append("包")
            enhanced_tokens.append("包子")
    return enhanced_tokens

class SemanticBM25Retriever(BaseRetriever):
    def __init__(self, collection_name: str = "default", mode: str = "OR") -> None:

        self._mode = mode

        # Path to database directories
        VECTOR_DB_PATH = os.getenv("VECTOR_DB_PATH")
        BM25_DB_PATH = os.getenv("BM25_DB_PATH")

        # Embedding Model (must match build)
        self._embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-zh-v1.5")

        # Weights / thresholds
        self._vector_weight = float(os.getenv("VECTOR_WEIGHT", "1.0"))
        self._bm25_weight = float(os.getenv("BM25_WEIGHT", "1.3"))
        self._vector_min_score = float(os.getenv("VECTOR_MIN_SCORE", "0.3"))
        self._bm25_min_score = float(os.getenv("BM25_MIN_SCORE", "0.0"))
        self._merged_min_score = float(os.getenv("MERGED_MIN_SCORE", "0.0"))
        self._vector_top_k = int(os.getenv("VECTOR_TOP_K", "8"))
        self._bm25_top_k = int(os.getenv("BM25_TOP_K", "8"))

        # Read stored Vector Database
        if not VECTOR_DB_PATH:
            raise ValueError("VECTOR_DB_PATH is not set")
        self._vectordb = chromadb.PersistentClient(path=VECTOR_DB_PATH)
        # Do not auto-create; fail fast if collection is missing
        _chroma_collection = self._vectordb.get_collection(collection_name)
        if _chroma_collection.count() == 0:
            raise ValueError(f"Chroma collection '{collection_name}' is empty")
        self._vector_store = ChromaVectorStore(chroma_collection=_chroma_collection)
        self._index = VectorStoreIndex.from_vector_store(
            self._vector_store,
            embed_model=self._embed_model,
        )

        self._chromadb_retriever = self._index.as_retriever(similarity_top_k=self._vector_top_k)

        # Read stored BM25 Database
        if not BM25_DB_PATH:
            raise ValueError("BM25_DB_PATH is not set")
        self._bm25_retriever = BM25Retriever.from_persist_dir(BM25_DB_PATH)
        try:
            self._bm25_retriever._tokenizer = chinese_tokenizer
        except Exception:
            pass
        try:
            self._bm25_retriever._similarity_top_k = self._bm25_top_k
        except Exception:
            pass


    def _retrieve(self, query_bundle: QueryBundle) -> List[NodeWithScore]:

        # Retrieving Nodes from Database
        vector_nodes = [
            n for n in self._chromadb_retriever.retrieve(query_bundle)
            if (n.score or 0.0) >= self._vector_min_score
        ]
        bm25_nodes = [
            n for n in self._bm25_retriever.retrieve(query_bundle)
            if (n.score or 0.0) >= self._bm25_min_score
        ]

        # Merge with weighted scores
        combined = {}
        for n in vector_nodes:
            nid = n.node.node_id
            entry = combined.get(nid, {"node": n.node, "vec": 0.0, "bm": 0.0})
            entry["vec"] = max(entry["vec"], n.score or 0.0)
            combined[nid] = entry
        for n in bm25_nodes:
            nid = n.node.node_id
            entry = combined.get(nid, {"node": n.node, "vec": 0.0, "bm": 0.0})
            entry["bm"] = max(entry["bm"], n.score or 0.0)
            combined[nid] = entry

        merged_nodes: List[NodeWithScore] = []
        for entry in combined.values():
            score = self._vector_weight * entry["vec"] + self._bm25_weight * entry["bm"]
            if score >= self._merged_min_score:
                merged_nodes.append(NodeWithScore(node=entry["node"], score=score))

        merged_nodes.sort(key=lambda n: n.score or 0.0, reverse=True)
        return merged_nodes


if __name__ == "__main__":

    db = SemanticBM25Retriever(collection_name="cook_book")

    res = db.retrieve("List of all sandwich recipes.")

    print(len(res))


