import json
import re
from pathlib import Path

from app.core.config import settings
from app.ingest.chunker import build_text_splitter


def normalize_source_path(source_file: str) -> str:
    return source_file.replace("\\", "/")


def path_name(source_file: str) -> str:
    return re.split(r"[\\/]", source_file)[-1]


def path_stem(source_file: str) -> str:
    return Path(path_name(source_file)).stem


def infer_category_and_subcategory(source_file: str) -> tuple[str, str]:
    path_str = source_file.lower().replace("/", "\\")

    if "\\quy_che\\" in path_str:
        return "quy_che", "general"
    if "\\so_tay\\" in path_str:
        return "so_tay", "general"
    if "\\ke_hoach\\" in path_str:
        return "ke_hoach", "general"
    if "\\ctdt\\" in path_str:
        return "ctdt", "general"

    if "\\phu_luc\\quy_trinh_hoc_vu\\" in path_str:
        return "phu_luc", "quy_trinh_hoc_vu"
    if "\\phu_luc\\thuc_tap_kltn\\" in path_str:
        return "phu_luc", "thuc_tap_kltn"
    if "\\phu_luc\\quy_doi_chung_chi_diem\\" in path_str:
        return "phu_luc", "quy_doi_chung_chi_diem"
    if "\\phu_luc\\bieu_mau\\" in path_str:
        return "phu_luc", "bieu_mau"

    return "unknown", "unknown"


def infer_document_type(category: str, sub_category: str, filename: str) -> str:
    filename_lower = filename.lower()

    if sub_category == "quy_trinh_hoc_vu":
        return "quy_trinh_hoc_vu"
    if sub_category == "thuc_tap_kltn":
        return "thuc_tap_kltn"
    if sub_category == "quy_doi_chung_chi_diem":
        return "quy_doi_chung_chi_diem"
    if category == "quy_che":
        return "quy_che"
    if category == "so_tay":
        return "so_tay"
    if category == "ctdt":
        return "ctdt"
    if category == "ke_hoach":
        return "ke_hoach"

    if "quy đổi" in filename_lower:
        return "quy_doi_chung_chi_diem"

    return "general"


def split_by_structure(text: str, document_type: str):
    text = text.strip()
    if not text:
        return []

    patterns = {
        "quy_trinh_hoc_vu": r"(?=(Bước\s+\d+[:.]|BƯỚC\s+\d+[:.]|Hồ sơ gồm[:]?|Mẫu đơn[:]?))",
        "thuc_tap_kltn": r"(?=(Bước\s+\d+[:.]|BƯỚC\s+\d+[:.]|Hồ sơ gồm[:]?|Phiếu[:]?|Mẫu[:]?|Quy trình[:]?))",
        "quy_doi_chung_chi_diem": r"(?=(\d+\.\d+\.\s|IELTS|TOEIC|TOEFL|HSK|TOPIK|JLPT|Chứng chỉ))",
        "quy_che": r"(?=(Điều\s+\d+[.:]?|Chương\s+[IVXLC0-9]+))",
        "so_tay": r"(?=(Điều\s+\d+[.:]?|Chương\s+[IVXLC0-9]+|MỤC\s+\d+[.:]?))",
        "ctdt": r"(?=(CHƯƠNG TRÌNH ĐÀO TẠO|Học phần|Khối kiến thức|Mã học phần))",
        "ke_hoach": r"(?=(Học kỳ\s+[IVXLC0-9]+|Tuần\s+\d+|THỜI GIAN HỌC TẬP))",
    }

    pattern = patterns.get(document_type)
    if not pattern:
        return []

    parts = re.split(pattern, text)
    merged = []

    current = ""
    for part in parts:
        if not part or not part.strip():
            continue
        if re.match(pattern, part.strip()):
            if current.strip():
                merged.append(current.strip())
            current = part.strip()
        else:
            current += "\n" + part.strip()

    if current.strip():
        merged.append(current.strip())

    return [p for p in merged if len(p.strip()) > 50]


def extract_section_title(chunk_text: str) -> str:
    first_line = chunk_text.strip().splitlines()[0].strip()
    return first_line[:200]


def build_search_text(source_file: str, page_text: str, section_title: str) -> str:
    filename = path_stem(source_file)
    boosted = f"{filename}\n{section_title}\n{page_text}"
    return boosted.strip()


def main():
    cleaned_root = Path(settings.CLEANED_DIR)
    chunks_root = Path(settings.CHUNKS_DIR)
    chunks_root.mkdir(parents=True, exist_ok=True)

    splitter = build_text_splitter()
    all_chunks = []

    for json_file in sorted(cleaned_root.rglob("*.json"), key=lambda p: p.as_posix().lower()):
        data = json.loads(json_file.read_text(encoding="utf-8"))
        source_file = normalize_source_path(data["source_file"])
        filename = path_name(source_file)
        category, sub_category = infer_category_and_subcategory(source_file)
        document_type = infer_document_type(category, sub_category, filename)

        for page in data["pages"]:
            page_text = page.get("text", "").strip()
            if not page_text:
                continue

            structured_chunks = split_by_structure(page_text, document_type)

            if structured_chunks:
                chunks = structured_chunks
            else:
                chunks = splitter.split_text(page_text)

            for idx, raw_chunk in enumerate(chunks):
                section_title = extract_section_title(raw_chunk)
                search_text = build_search_text(source_file, raw_chunk, section_title)

                all_chunks.append({
                    "id": f"{json_file.stem}_p{page['page']}_{idx}",
                    "text": search_text,
                    "metadata": {
                        "source_file": source_file,
                        "filename": filename,
                        "page": page["page"],
                        "category": category,
                        "sub_category": sub_category,
                        "document_type": document_type,
                        "section_title": section_title,
                    }
                })

    out_file = chunks_root / "chunks.jsonl"
    with out_file.open("w", encoding="utf-8") as f:
        for item in all_chunks:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    print(f"Saved {len(all_chunks)} chunks to {out_file}")


if __name__ == "__main__":
    main()
