# OpenSPG Integration Notes (Local)

This repo includes OpenSPG source code under `third_party/openspg`. It is a **server-side** framework (Java + MySQL + Neo4j + MinIO), not a pip package.

## 1) Start OpenSPG (Docker)
OpenSPG provides a release `docker-compose.yml`:

```
third_party/openspg/dev/release/docker-compose.yml
```

Start from that directory:

```bash
cd third_party/openspg/dev/release
# docker compose up -d
```

Services: `openspg-server`, `mysql`, `neo4j`, `minio`.

## 2) Export data for ingestion
Use the export script to create CSVs:

```bash
python3 scripts/openspg/export_openspg_csv.py
```

Outputs:
- `data/openspg/kg_triples.csv`
- `data/openspg/attributes.csv`

These are **normalized** with the same entity fusion rules used in KG.

## 3) Build schema and pipeline
OpenSPG requires:
- schema definition (entities + relations + properties)
- ingestion pipeline (source -> extract -> align -> sink)

We keep schema in `src/schema/flood_schema.py` and can map it to OpenSPG types.

## 4) Next steps (to be implemented)
- Create OpenSPG schema mapping JSON/YAML from `flood_schema.py`
- Create ingestion pipeline JSON (CSV source)
- Run local builder or server-side builder job

## Notes
- If GPU usage is low, tune KG build with env vars in `scripts/create_knowledge_graph.py`:
  - `KG_CTX_WINDOW`, `KG_SAFE_TEXT_CHARS`, `KG_CHUNK_SIZE`, `KG_MAX_TRIPLETS`, `KG_INCLUDE_EMBEDDINGS`
