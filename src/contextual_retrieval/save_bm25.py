from llama_index.retrievers.bm25 import BM25Retriever
import Stemmer
import os

def save_BM25(nodes: list, 
              save_dir: str = "./", 
              db_name: str = "none") -> None:
    
    print("-:-:-:- BM25 [TF_IDF Database] creating ... -:-:-:-")

    # Initializing BM25 with Chinese support
    # 使用 jieba 分词，移除 stemmer（中文不需要词干提取）
    import jieba

    # 自定义分词函数
    def chinese_tokenizer(text):
        """增强型中文分词器，支持'包'、'包子'等词的模糊匹配"""
        # 使用搜索引擎模式
        tokens = list(jieba.cut_for_search(text))

        # 扩展：只要包含'包'，就添加'包'和'包子'（提高召回率）
        enhanced_tokens = []
        for token in tokens:
            enhanced_tokens.append(token)
            # 只要包含'包'字，就添加相关词
            if '包' in token:
                enhanced_tokens.append('包')
                enhanced_tokens.append('包子')

        return enhanced_tokens

    bm25_retriever = BM25Retriever.from_defaults(
        nodes=nodes,
        similarity_top_k=12,
        tokenizer=chinese_tokenizer,  # 使用中文分词
        # 移除 stemmer 和 language 参数
    )

    # Path to save BM25
    save_pth = os.path.join(save_dir, db_name)

    # Saving BM25
    bm25_retriever.persist(save_pth)

    print("-:-:-:- BM25 [TF_IDF Database] saved -:-:-:-")