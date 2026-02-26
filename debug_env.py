#!/usr/bin/env python
import os
from pathlib import Path
from dotenv import load_dotenv

# 加载.env
load_dotenv()

print("环境变量检查：")
print(f"DATA_DIR: {os.getenv('DATA_DIR')}")
print(f"VECTOR_DB_PATH: {os.getenv('VECTOR_DB_PATH')}")
print(f"BM25_DB_PATH: {os.getenv('BM25_DB_PATH')}")
print(f"COLLECTION_NAME: {os.getenv('COLLECTION_NAME')}")

# 检查路径是否存在
bm25_path = os.getenv('BM25_DB_PATH')
if bm25_path:
    p = Path(bm25_path)
    print(f"\nBM25_DB_PATH 路径：{p}")
    print(f"  是否存在: {p.exists()}")
    if p.exists():
        print(f"  目录内容: {list(p.iterdir())[:5]}")
