"""
完全重建数据库 - 解决embedding维度不匹配问题
"""
import os
import shutil
from pathlib import Path

print("=" * 80)
print("🔧 数据库重建工具")
print("=" * 80)

# 数据库路径
vector_db_path = "./src/db/canteen_db_vectordb"
bm25_db_path = "./src/db/canteen_db_bm25"

# 步骤1: 删除旧数据库
print("\n步骤 1: 删除旧数据库...")

if os.path.exists(vector_db_path):
    shutil.rmtree(vector_db_path)
    print(f"  ✓ 已删除向量数据库: {vector_db_path}")
else:
    print(f"  - 向量数据库不存在: {vector_db_path}")

if os.path.exists(bm25_db_path):
    shutil.rmtree(bm25_db_path)
    print(f"  ✓ 已删除BM25数据库: {bm25_db_path}")
else:
    print(f"  - BM25数据库不存在: {bm25_db_path}")

# 步骤2: 检查PDF文件
print("\n步骤 2: 检查PDF文件...")
data_dir = "./data"
pdf_files = list(Path(data_dir).glob("*.pdf"))

if len(pdf_files) == 0:
    print("  ❌ 错误: 没有找到PDF文件！")
    print(f"     请确保 {data_dir} 目录中有PDF文件")
    exit(1)
elif len(pdf_files) > 1:
    print(f"  ⚠️  警告: 找到 {len(pdf_files)} 个PDF文件:")
    for pdf in pdf_files:
        print(f"     - {pdf.name}")
    print("  建议: 只保留一个PDF文件以避免混淆")
else:
    print(f"  ✓ 找到PDF文件: {pdf_files[0].name}")

# 步骤3: 重新创建数据库
print("\n步骤 3: 开始重新创建数据库...")
print("  这将需要 10-15 分钟，请耐心等待...")
print("  确保 WSL 中的 Ollama 正在运行！")
print()

# 导入并运行创建函数
from dotenv import load_dotenv
load_dotenv()

data_dir = os.getenv("DATA_DIR", "./data")
save_dir = os.getenv("SAVE_DIR", "./src/db")
collection_name = os.getenv("COLLECTION_NAME", "ncwu_canteen_collection")
db_name = "canteen_db"

print(f"配置信息:")
print(f"  数据目录: {data_dir}")
print(f"  保存目录: {save_dir}")
print(f"  集合名称: {collection_name}")
print(f"  数据库名称: {db_name}")
print()

try:
    from src.contextual_retrieval import create_and_save_db

    create_and_save_db(
        data_dir=data_dir,
        save_dir=save_dir,
        collection_name=collection_name,
        db_name=db_name
    )

    print("\n" + "=" * 80)
    print("✅ 数据库重建成功！")
    print("=" * 80)
    print("\n下一步:")
    print("  1. 运行纯检索测试: python test_retrieval_only.py")
    print("  2. 运行A/B对比测试: python test_ab_simple.py 3")

except Exception as e:
    print("\n" + "=" * 80)
    print("❌ 数据库创建失败！")
    print("=" * 80)
    print(f"错误信息: {e}")
    import traceback
    traceback.print_exc()
    print("\n请检查:")
    print("  1. WSL 中 Ollama 是否正在运行")
    print("  2. 网络连接是否正常")
    print("  3. PDF 文件是否存在")

