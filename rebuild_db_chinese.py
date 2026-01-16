"""
完整重建数据库
1. 清理旧数据库
2. 重新创建（使用中文embedding）
3. 验证
"""
import os
import shutil

print("=" * 80)
print("🔄 数据库重建流程")
print("=" * 80)

# Step 1: 清理旧数据库
print("\n【步骤 1/3】清理旧数据库...")
db_paths = [
    "./src/db/canteen_db_vectordb",
    "./src/db/canteen_db_bm25"
]

for path in db_paths:
    if os.path.exists(path):
        print(f"  删除: {path}")
        shutil.rmtree(path)
    else:
        print(f"  不存在: {path}")

print("✓ 清理完成")

# Step 2: 检查PDF文件
print("\n【步骤 2/3】检查数据文件...")
data_path = "./data"
if os.path.exists(data_path):
    pdfs = [f for f in os.listdir(data_path) if f.endswith('.pdf')]
    print(f"  找到 {len(pdfs)} 个PDF文件:")
    for pdf in pdfs:
        size = os.path.getsize(os.path.join(data_path, pdf)) / 1024
        print(f"    - {pdf} ({size:.1f} KB)")

    if len(pdfs) != 1:
        print("\n  ⚠️  警告: 建议只保留一个PDF文件！")
        print("  当前使用: CR_Prefixed_v2.pdf")
else:
    print("  ✗ 错误: data/ 目录不存在！")
    exit(1)

print("✓ 数据文件检查完成")

# Step 3: 创建数据库
print("\n【步��� 3/3】重新创建数据库...")
print("  这将花费 10-15 分钟...")
print("  使用中文Embedding模型: BAAI/bge-small-zh-v1.5")
print("\n开始创建...")
print("-" * 80)

# 运行创建脚本
import subprocess
result = subprocess.run(
    ["python", "create_save_db.py"],
    capture_output=False,
    text=True
)

if result.returncode == 0:
    print("\n✓ 数据库创建成功！")
else:
    print(f"\n✗ 数据库创建失败，错误码: {result.returncode}")
    exit(1)

print("\n" + "=" * 80)
print("✅ 重建完成！")
print("=" * 80)
print("\n下一步:")
print("  运行测试: python test_retrieval_only.py")
print("  或运行: python test_ab_simple.py 3")

