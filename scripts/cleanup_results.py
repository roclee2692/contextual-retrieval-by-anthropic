import os
import shutil
from pathlib import Path

def cleanup():
    base_dir = Path(__file__).parent.parent / "results"
    archive_dir = base_dir / "archive_old_experiments"
    archive_dir.mkdir(exist_ok=True)
    
    files_to_move = [
        "report_experiment_1_RAG_Chunked.json",
        "report_experiment_1_RAG_Chunked.txt",
        "report_experiment_2_CR_Prefixed.json",
        "report_experiment_2_CR_Prefixed.txt",
        "report_experiment_3_Jieba_KG.json",
        "report_experiment_3_Jieba_KG.txt",
        "summary_table.csv"
    ]
    
    for filename in files_to_move:
        src = base_dir / filename
        if src.exists():
            try:
                shutil.move(str(src), str(archive_dir / filename))
                print(f"Moved {filename}")
            except Exception as e:
                print(f"Error moving {filename}: {e}")

if __name__ == "__main__":
    cleanup()
