"""
Generate a minimal OpenSPG pipeline template (JSON).
This template uses CSV source and a placeholder extract operator.
Output: data/openspg/pipeline_template.json
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT_PATH = ROOT / "data" / "openspg" / "pipeline_template.json"


def main() -> None:
    pipeline = {
        "nodes": [
            {
                "id": "source_csv",
                "name": "CSVSource",
                "nodeConfig": {
                    "@type": "CSV_SOURCE",
                    "startRow": 1,
                    "url": "data/openspg/kg_triples.csv",
                    "columns": ["subject", "predicate", "object"],
                },
            },
            {
                "id": "extract",
                "name": "UserDefinedExtract",
                "nodeConfig": {
                    "@type": "USER_DEFINED_EXTRACT",
                    "operatorConfig": {
                        "modulePath": "python/placeholder_operator.py",
                        "className": "PlaceholderOperator",
                        "method": "process",
                        "params": {},
                        "paramsPrefix": "",
                    },
                },
            },
            {
                "id": "sink",
                "name": "GraphSink",
                "nodeConfig": {"@type": "GRAPH_SINK", "isWriter": True},
            },
        ],
        "edges": [
            {"from": "source_csv", "to": "extract"},
            {"from": "extract", "to": "sink"},
        ],
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(pipeline, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote pipeline template: {OUT_PATH}")


if __name__ == "__main__":
    main()
