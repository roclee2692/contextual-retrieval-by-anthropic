"""
Export current KG triples and attribute facts to CSV for OpenSPG ingestion.
- KG source: src/db/knowledge_graph/graph_store.json
- Attribute source: src/db/attribute_store.sqlite
Outputs:
  data/openspg/kg_triples.csv
  data/openspg/attributes.csv
"""
import csv
import json
import sqlite3
from pathlib import Path
from typing import Dict, List

from src.contextual_retrieval.entity_fusion import normalize_entity

ROOT = Path(__file__).resolve().parents[2]
KG_DIR = ROOT / "src" / "db" / "knowledge_graph"
ATTR_DB = ROOT / "src" / "db" / "attribute_store.sqlite"
OUT_DIR = ROOT / "data" / "openspg"


def export_kg_triples(out_path: Path) -> int:
    graph_path = KG_DIR / "graph_store.json"
    if not graph_path.exists():
        raise FileNotFoundError(f"graph_store.json not found: {graph_path}")

    raw = json.loads(graph_path.read_text(encoding="utf-8"))
    graph_dict: Dict[str, List[List[str]]] = raw.get("graph_dict", {})

    out_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["subject", "predicate", "object"])
        for subj, edges in graph_dict.items():
            n_subj = normalize_entity(subj)
            for pred, obj in edges:
                n_obj = normalize_entity(obj)
                writer.writerow([n_subj, pred, n_obj])
                count += 1
    return count


def export_attributes(out_path: Path) -> int:
    if not ATTR_DB.exists():
        raise FileNotFoundError(f"attribute_store.sqlite not found: {ATTR_DB}")

    conn = sqlite3.connect(ATTR_DB)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute("SELECT * FROM attributes").fetchall()
    finally:
        conn.close()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "entity_name",
            "field",
            "value",
            "value_text",
            "unit",
            "comparator",
            "condition",
            "source_doc",
            "source_page",
            "source_clause",
            "evidence_text",
            "confidence",
        ])
        for r in rows:
            writer.writerow([
                r.get("entity_name"),
                r.get("field"),
                r.get("value"),
                r.get("value_text"),
                r.get("unit"),
                r.get("comparator"),
                r.get("condition"),
                r.get("source_doc"),
                r.get("source_page"),
                r.get("source_clause"),
                r.get("evidence_text"),
                r.get("confidence"),
            ])
            count += 1
    return count


def main() -> None:
    kg_out = OUT_DIR / "kg_triples.csv"
    attr_out = OUT_DIR / "attributes.csv"

    kg_count = export_kg_triples(kg_out)
    attr_count = export_attributes(attr_out)

    print("Export complete")
    print(f"  KG triples: {kg_count} -> {kg_out}")
    print(f"  Attributes: {attr_count} -> {attr_out}")


if __name__ == "__main__":
    main()
