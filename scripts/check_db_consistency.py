"""检查 Baseline 和 CR 数据库的一致性"""
import chromadb

# 检查两个数据库的文档数量
baseline_db = chromadb.PersistentClient(path='src/db/flood_prevention_db_baseline_vectordb')
cr_db = chromadb.PersistentClient(path='src/db/flood_prevention_db_cr_vectordb')

baseline_col = baseline_db.get_collection('flood_prevention_collection')
cr_col = cr_db.get_collection('flood_prevention_collection')

print(f'Baseline 文档数: {baseline_col.count()}')
print(f'CR 文档数: {cr_col.count()}')

# 获取一些文档 ID 对比
baseline_sample = baseline_col.get(limit=5)
cr_sample = cr_col.get(limit=5)

print(f'\nBaseline 前5个ID: {baseline_sample["ids"]}')
print(f'CR 前5个ID: {cr_sample["ids"]}')

# 检查是否有重叠
baseline_all = baseline_col.get()
cr_all = cr_col.get()

baseline_ids = set(baseline_all["ids"])
cr_ids = set(cr_all["ids"])
overlap = baseline_ids.intersection(cr_ids)
print(f'\nID重叠数: {len(overlap)} / {len(baseline_ids)}')

# 对比同一个位置的文档内容
print('\n' + '='*80)
print('对比第一个文档的内容：')
print('='*80)

print('\n[Baseline 第1个文档]')
print(baseline_sample["documents"][0][:500] if baseline_sample["documents"] else "无")

print('\n[CR 第1个文档]')
print(cr_sample["documents"][0][:500] if cr_sample["documents"] else "无")
