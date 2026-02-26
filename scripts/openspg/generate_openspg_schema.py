"""
Generate a minimal OpenSPG schema mapping JSON from flood_schema.py.
This is a mapping artifact for later import via OpenSPG schema APIs.
Output: data/openspg/schema_flood.json
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.schema.flood_schema import NODE_TYPES, RELATION_TYPES
OUT_PATH = ROOT / "data" / "openspg" / "schema_flood.json"


def main() -> None:
    types = []
    for name, meta in NODE_TYPES.items():
        types.append(
            {
                "type_name": name,
                "name_zh": meta.get("label"),
                "description": meta.get("description"),
                "key_properties": meta.get("key_properties", []),
                "examples": meta.get("examples", []),
            }
        )

    relations = []
    for name, meta in RELATION_TYPES.items():
        relations.append(
            {
                "relation_name": name,
                "name_zh": meta.get("label"),
                "domain": meta.get("domain", []),
                "range": meta.get("range", []),
                "examples": meta.get("examples", []),
            }
        )

    payload = {
        "schema_name": "FloodPrevention",
        "types": types,
        "relations": relations,
        "notes": "Generated from src/schema/flood_schema.py for OpenSPG import.",
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote schema mapping: {OUT_PATH}")


if __name__ == "__main__":
    main()
