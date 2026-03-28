from pathlib import Path
import fitz


def extract_text_from_pdf(pdf_path: Path) -> dict:
    doc = fitz.open(pdf_path)
    pages = []

    for page_number, page in enumerate(doc, start=1):
        text = page.get_text("text")
        pages.append({
            "page": page_number,
            "text": text.strip()
        })

    doc.close()

    return {
        "source_file": str(pdf_path),
        "total_pages": len(pages),
        "pages": pages
    }