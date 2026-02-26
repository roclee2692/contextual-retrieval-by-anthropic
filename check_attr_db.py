#!/usr/bin/env python
import sqlite3
from pathlib import Path

db_path = Path('src/db/attribute_store.sqlite')
print(f'数据库存在: {db_path.exists()}')
if db_path.exists():
    conn = sqlite3.connect(str(db_path))
    tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    print(f'表: {tables}')
    for table in tables:
        count = conn.execute(f'SELECT COUNT(*) FROM {table[0]}').fetchone()[0]
        print(f'  {table[0]}: {count}行')
    conn.close()
else:
    print('属性库数据库不存在！')
