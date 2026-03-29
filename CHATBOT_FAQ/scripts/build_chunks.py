import json
from pathlib import Path

from app.core.config import settings
from app.ingest.chunker import build_text_splitter


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


def build_search_text(source_file: str, page_text: str) -> str:
    filename = Path(source_file).stem
    boosted = f"{filename}\n{filename}\n{page_text}"
    return boosted.strip()


def main():
    cleaned_root = Path(settings.CLEANED_DIR)
    chunks_root = Path(settings.CHUNKS_DIR)
    chunks_root.mkdir(parents=True, exist_ok=True)

    splitter = build_text_splitter()
    all_chunks = []

    for json_file in cleaned_root.rglob("*.json"):
        data = json.loads(json_file.read_text(encoding="utf-8"))
        source_file = data["source_file"]
        filename = Path(source_file).name
        category, sub_category = infer_category_and_subcategory(source_file)

        for page in data["pages"]:
            page_text = page.get("text", "").strip()
            if not page_text:
                continue

            search_text = build_search_text(source_file, page_text)
            chunks = splitter.split_text(search_text)

            for idx, chunk in enumerate(chunks):
                all_chunks.append({
                    "id": f"{json_file.stem}_p{page['page']}_{idx}",
                    "text": chunk,
                    "metadata": {
                        "source_file": source_file,
                        "filename": filename,
                        "page": page["page"],
                        "category": category,
                        "sub_category": sub_category,
                    }
                })

    out_file = chunks_root / "chunks.jsonl"
    with out_file.open("w", encoding="utf-8") as f:
        for item in all_chunks:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    print(f"Saved {len(all_chunks)} chunks to {out_file}")


if __name__ == "__main__":
    main()