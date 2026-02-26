import sqlite3
from typing import Iterable, Dict, Any, List, Optional

TABLE_SCHEMA = """
CREATE TABLE IF NOT EXISTS attributes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_name TEXT,
    field TEXT,
    value REAL,
    value_text TEXT,
    unit TEXT,
    comparator TEXT,
    condition TEXT,
    source_doc TEXT,
    source_page TEXT,
    source_clause TEXT,
    evidence_text TEXT,
    confidence REAL,
    UNIQUE(entity_name, field, value_text, unit, condition, source_doc, source_page)
);
"""


def init_db(db_path: str) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(TABLE_SCHEMA)
        conn.commit()
    finally:
        conn.close()


def insert_facts(db_path: str, facts: Iterable[Dict[str, Any]]) -> int:
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(TABLE_SCHEMA)
        cur = conn.cursor()
        count = 0
        for f in facts:
            cur.execute(
                """
                INSERT OR IGNORE INTO attributes (
                    entity_name, field, value, value_text, unit, comparator,
                    condition, source_doc, source_page, source_clause,
                    evidence_text, confidence
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    f.get("entity_name"),
                    f.get("field"),
                    f.get("value"),
                    f.get("value_text"),
                    f.get("unit"),
                    f.get("comparator"),
                    f.get("condition"),
                    f.get("source_doc"),
                    f.get("source_page"),
                    f.get("source_clause"),
                    f.get("evidence_text"),
                    f.get("confidence"),
                ),
            )
            if cur.rowcount:
                count += 1
        conn.commit()
        return count
    finally:
        conn.close()


def query_facts(
    db_path: str,
    field: Optional[str] = None,
    entity_name: Optional[str] = None,
    condition: Optional[str] = None,
    limit: int = 5,
) -> List[Dict[str, Any]]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        sql = "SELECT * FROM attributes WHERE 1=1"
        params: list = []
        if field:
            sql += " AND field = ?"
            params.append(field)
        if entity_name:
            sql += " AND entity_name LIKE ?"
            params.append(f"%{entity_name}%")
        if condition:
            sql += " AND condition LIKE ?"
            params.append(f"%{condition}%")
        sql += " ORDER BY confidence DESC, id DESC LIMIT ?"
        params.append(limit)
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
