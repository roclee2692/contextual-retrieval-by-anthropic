from src.contextual_retrieval import create_and_save_db
import os
from dotenv import load_dotenv
load_dotenv()

data_dir = os.getenv("DATA_DIR")
save_dir = os.getenv("SAVE_DIR")
collection_name = os.getenv("COLLECTION_NAME")
db_name = os.getenv("DB_NAME", "contextual_db") # Default fallback

# 如果是 Baseline 模式，自动添加后缀避免覆盖
skip_context = os.getenv("SKIP_CONTEXT_LLM", "0") == "1"
if skip_context and not db_name.endswith("_baseline"):
    db_name = db_name + "_baseline"
    print(f"🔹 Baseline模式: 数据库名称改为 {db_name}")

create_and_save_db(
    data_dir=data_dir, 
    save_dir=save_dir,
    collection_name=collection_name,
    db_name=db_name
    )