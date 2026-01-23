import subprocess
import pathlib
from typing import List

ROOT = pathlib.Path(__file__).resolve().parents[1] / 'data' / '防洪预案'
SOFFICE = r"C:\\Program Files\\LibreOffice\\program\\soffice.exe"

def convert(paths: List[pathlib.Path]) -> None:
    for path in paths:
        outdir = path.parent
        print(f'Converting {path.name} -> pdf')
        cmd = [SOFFICE, '--headless', '--convert-to', 'pdf', str(path), '--outdir', str(outdir)]
        try:
            subprocess.run(cmd, check=True)
        except Exception as e:
            print(f'Failed {path.name}: {e}')

def main() -> None:
    paths = sorted(p for p in ROOT.glob('*.doc*') if p.suffix.lower() in {'.doc', '.docx'})
    if not paths:
        print('No doc/docx found')
        return
    convert(paths)
    print('Done')

if __name__ == '__main__':
    main()
