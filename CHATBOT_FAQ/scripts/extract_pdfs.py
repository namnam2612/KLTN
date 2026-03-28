import json
from pathlib import Path

from app.core.config import settings
from app.utils.file_paths import list_pdf_files
from app.ingest.pdf_reader import extract_text_from_pdf


def main():
    raw_dir = Path(settings.RAW_DIR)
    out_dir = Path(settings.EXTRACTED_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)

    pdf_files = list_pdf_files(str(raw_dir))
    print(f"Found {len(pdf_files)} PDF files")

    for pdf_path in pdf_files:
        rel_path = pdf_path.relative_to(raw_dir)
        out_path = out_dir / rel_path.with_suffix(".json")
        out_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            data = extract_text_from_pdf(pdf_path)
            out_path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
            print(f"[OK] {pdf_path}")
        except Exception as e:
            print(f"[ERROR] {pdf_path}: {e}")


if __name__ == "__main__":
    main()