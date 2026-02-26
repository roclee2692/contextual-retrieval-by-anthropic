"""
构建数值属性层（Attribute Store）
- 从 PDF 文档中抽取字段-数值-单位-条件-来源
- 输出到 SQLite（默认: src/db/attribute_store.sqlite）
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from llama_index.core import SimpleDirectoryReader
from llama_index.readers.file import PDFReader

from src.attribute_store.store import init_db, insert_facts
from src.attribute_store.extract import extract_facts


def build_attribute_store():
    load_dotenv()

    data_dir = os.getenv("DATA_DIR", "./data/防洪预案")
    out_db = os.getenv("ATTRIBUTE_DB", str(ROOT / "src" / "db" / "attribute_store.sqlite"))

    print("=" * 72)
    print("构建数值属性层 (Attribute Store)")
    print("=" * 72)
    print(f"DATA_DIR: {data_dir}")
    print(f"DB: {out_db}")

    init_db(out_db)

    parser = PDFReader(return_full_document=False)
    reader = SimpleDirectoryReader(data_dir, file_extractor={".pdf": parser}, recursive=True)
    documents = reader.load_data()

    print(f"加载文档片段: {len(documents)}")

    total_facts = 0
    for doc in documents:
        text = doc.text or ""
        if not text.strip():
            continue
        meta = doc.metadata or {}
        file_path = meta.get("file_path", "")
        source_doc = os.path.basename(file_path) if file_path else "unknown"
        source_page = str(meta.get("page_label", ""))

        facts = extract_facts(text, source_doc=source_doc, source_page=source_page)
        if facts:
            inserted = insert_facts(out_db, facts)
            total_facts += inserted

    print(f"完成：新增 {total_facts} 条属性事实")
    print("=" * 72)


if __name__ == "__main__":
    build_attribute_store()
