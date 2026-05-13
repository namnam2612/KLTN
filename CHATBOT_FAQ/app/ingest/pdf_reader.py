import fitz
import pdfplumber
from pathlib import Path
import re


def extract_text_from_pdf(pdf_path: Path) -> dict:
    pages_data = []
    current_chapter = ""
    current_article = ""

    # Mở file bằng cả 2 thư viện cho Hybrid Extraction
    doc = fitz.open(pdf_path)
    pdf_plumb = pdfplumber.open(pdf_path)

    for page_number, page in enumerate(doc, start=1):
        # 1. Trích xuất luồng văn bản và phân tích khối (Text Block Analysis)
        blocks = page.get_text("blocks")
        page_text = ""

        for block in blocks:
            # Index 4 chứa nội dung text của block
            block_text = block[4].strip()
            if not block_text:
                continue

            # Làm giàu Metadata: Nhận diện Chương/Điều đang xử lý
            if re.match(r"^Chương [IVXLD]+", block_text, re.IGNORECASE):
                current_chapter = block_text
            elif re.match(r"^Điều \d+", block_text, re.IGNORECASE):
                current_article = block_text

            page_text += block_text + "\n"

        # 2. Trích xuất bảng biểu (Tabular Extraction) và chuyển sang Markdown
        tables_markdown = ""
        plumb_page = pdf_plumb.pages[page_number - 1]
        tables = plumb_page.extract_tables()

        for table in tables:
            if table:
                tables_markdown += "\n\n[BẢNG QUY ĐỊNH]:\n"
                for idx, row in enumerate(table):
                    # Xóa newline trong từng ô và bọc vào cột Markdown
                    clean_row = [str(cell).replace("\n", " ") if cell else "" for cell in row]
                    tables_markdown += "| " + " | ".join(clean_row) + " |\n"
                    # Thêm dòng phân cách cho Header của bảng
                    if idx == 0:
                        tables_markdown += "|---" * len(row) + "|\n"

        # Gộp Text và Markdown Table lại
        combined_content = page_text.strip()
        if tables_markdown:
            combined_content += tables_markdown

        pages_data.append({
            "page": page_number,
            "text": combined_content,
            "metadata_tags": {
                "chapter": current_chapter,
                "article": current_article
            }
        })

    doc.close()
    pdf_plumb.close()

    return {
        "source_file": str(pdf_path),
        "total_pages": len(pages_data),
        "pages": pages_data
    }