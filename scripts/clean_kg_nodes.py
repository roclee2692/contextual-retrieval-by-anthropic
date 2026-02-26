"""
清洗 KG 图节点名（去路径前缀/文件后缀/别名归一）
- 只修改 graph_store.json，不重建数据库
- 会生成 graph_store.json.bak 备份
"""
import json
import os
import sys
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.contextual_retrieval.entity_fusion import normalize_entity
KG_DIR = ROOT / "src" / "db" / "knowledge_graph"
GRAPH_PATH = KG_DIR / "graph_store.json"
BACKUP_PATH = KG_DIR / "graph_store.json.bak"


def _normalize_node(name: str) -> str:
    return normalize_entity(name)


def _dedup_edges(edges: List[List[str]]) -> List[List[str]]:
    seen = set()
    out = []
    for rel, obj in edges:
        key = (rel, obj)
        if key not in seen:
            seen.add(key)
            out.append([rel, obj])
    return out


def clean_graph_store() -> None:
    if not GRAPH_PATH.exists():
        raise FileNotFoundError(f"graph_store.json not found: {GRAPH_PATH}")

    raw = json.loads(GRAPH_PATH.read_text(encoding="utf-8"))
    graph_dict: Dict[str, List[List[str]]] = raw.get("graph_dict", {})

    new_graph: Dict[str, List[List[str]]] = {}
    node_count_before = len(graph_dict)
    edge_count_before = sum(len(v) for v in graph_dict.values())

    for subj, edges in graph_dict.items():
        n_subj = _normalize_node(subj)
        for rel, obj in edges:
            n_obj = _normalize_node(obj)
            new_graph.setdefault(n_subj, []).append([rel, n_obj])

    # 去重
    for k in list(new_graph.keys()):
        new_graph[k] = _dedup_edges(new_graph[k])

    node_count_after = len(new_graph)
    edge_count_after = sum(len(v) for v in new_graph.values())

    # 备份
    if not BACKUP_PATH.exists():
        BACKUP_PATH.write_text(GRAPH_PATH.read_text(encoding="utf-8"), encoding="utf-8")

    GRAPH_PATH.write_text(
        json.dumps({"graph_dict": new_graph}, ensure_ascii=False),
        encoding="utf-8",
    )

    print("KG graph_store clean complete")
    print(f"nodes: {node_count_before} -> {node_count_after}")
    print(f"edges: {edge_count_before} -> {edge_count_after}")
    print(f"backup: {BACKUP_PATH}")


if __name__ == "__main__":
    clean_graph_store()
