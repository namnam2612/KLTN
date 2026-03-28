from pathlib import Path


def list_pdf_files(root_dir: str) -> list[Path]:
    root = Path(root_dir)
    return sorted(root.rglob("*.pdf"))