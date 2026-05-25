import os, time, json
from pathlib import Path

# ============ CONFIG: chỉnh theo cấu trúc thư mục của bạn ============
PROJECT_ROOT     = Path(__file__).parent
PDF_SOURCE_DIR   = PROJECT_ROOT / "data" / "raw"           # nơi chứa PDF gốc
EXTRACTED_DIR    = PROJECT_ROOT / "data" / "extracted"     # sau pdf_reader.py
CLEANED_DIR      = PROJECT_ROOT / "data" / "cleaned"       # sau cleaner.py
CHUNKS_JSONL     = PROJECT_ROOT / "data" / "cleaned" / "chunks.jsonl"  # nếu có
INDEX_DIR        = PROJECT_ROOT / "data" / "index"         # ChromaDB persist dir
COLLECTION_NAME  = "tlu_regulations"                       # đổi tên thật

OUTPUT_CSV       = PROJECT_ROOT / "he_thong_so_lieu.csv"


def count_pdfs(d):
    if not d.exists(): return None
    return len(list(d.rglob("*.pdf"))) + len(list(d.rglob("*.PDF")))


def count_pages(d):
    try: import fitz
    except ImportError: return None
    if not d.exists(): return None
    total = 0
    for p in list(d.rglob("*.pdf")) + list(d.rglob("*.PDF")):
        try:
            doc = fitz.open(str(p))
            total += doc.page_count
            doc.close()
        except: pass
    return total


def count_chunks_from_jsonl(p):
    """Đếm chunk từ file chunks.jsonl nếu pipeline của bạn lưu chunk ra file."""
    if not p.exists(): return None
    return sum(1 for _ in open(p, encoding='utf-8'))


def get_chroma_stats(persist_dir, collection):
    """Lấy stats từ ChromaDB (phiên bản mới)."""
    try:
        import chromadb
    except ImportError:
        return None, "Thiếu chromadb"
    if not Path(persist_dir).exists():
        return None, f"Không có thư mục: {persist_dir}"
    try:
        client = chromadb.PersistentClient(path=str(persist_dir))
        col = client.get_collection(collection)
        count = col.count()
        # Lấy mẫu để check vector dim
        sample = col.peek(limit=1)
        vector_dim = len(sample['embeddings'][0]) if sample.get('embeddings') else None
        # Tính độ dài trung bình chunk
        sample_large = col.peek(limit=200)
        docs = sample_large.get('documents', [])
        avg_words = sum(len(d.split()) for d in docs if d) / max(len(docs), 1)
        return {
            'count': count,
            'vector_dim': vector_dim,
            'avg_chunk_words': round(avg_words, 1)
        }, None
    except Exception as e:
        return None, str(e)


def get_dir_size_mb(d):
    if not d.exists(): return None
    total = sum(f.stat().st_size for f in Path(d).rglob('*') if f.is_file())
    return round(total / (1024 * 1024), 2)


def fmt(v): return "—" if v is None else str(v)


# =========== Đo ===========
print("=" * 70)
print(" ĐO SỐ LIỆU HỆ THỐNG ".center(70, "="))
print("=" * 70)

results = {}
results['pdf'] = count_pdfs(PDF_SOURCE_DIR);            print(f"[1] Số file PDF: {fmt(results['pdf'])}")
results['pages'] = count_pages(PDF_SOURCE_DIR);         print(f"[2] Tổng số trang: {fmt(results['pages'])}")

# Đếm chunk từ jsonl HOẶC từ Chroma
results['chunks_jsonl'] = count_chunks_from_jsonl(CHUNKS_JSONL)
print(f"[3a] Số chunk trong chunks.jsonl: {fmt(results['chunks_jsonl'])}")

stats, err = get_chroma_stats(INDEX_DIR, COLLECTION_NAME)
if err:
    print(f"[3b-5] Lỗi đọc Chroma: {err}")
    results['chunks_db'] = None; results['vector_dim'] = None; results['avg_chunk'] = None
else:
    results['chunks_db'] = stats['count']
    results['vector_dim'] = stats['vector_dim']
    results['avg_chunk'] = stats['avg_chunk_words']
    print(f"[3b] Số chunk trong ChromaDB: {results['chunks_db']}")
    print(f"[4] Vector dim: {results['vector_dim']}")
    print(f"[5] Độ dài chunk trung bình (từ): {results['avg_chunk']}")

results['db_size'] = get_dir_size_mb(INDEX_DIR);        print(f"[6] Dung lượng ChromaDB: {fmt(results['db_size'])} MB")
results['extracted_size'] = get_dir_size_mb(EXTRACTED_DIR); print(f"[7] Dung lượng dữ liệu extracted: {fmt(results['extracted_size'])} MB")

# Ghi CSV
print()
print("=" * 70)
print(" KẾT QUẢ CUỐI — COPY VÀO LUẬN VĂN ".center(70, "="))
print("=" * 70)
rows = [
    ("Số văn bản quy chế nguồn (PDF)",       fmt(results['pdf'])),
    ("Tổng số trang văn bản đã xử lý",       fmt(results['pages'])),
    ("Số chunk được sinh ra",                fmt(results['chunks_db'] or results['chunks_jsonl'])),
    ("Độ dài chunk trung bình (từ)",         fmt(results['avg_chunk'])),
    ("Số chiều của vector embedding",        fmt(results['vector_dim'])),
    ("Dung lượng ChromaDB trên đĩa (MB)",    fmt(results['db_size'])),
    ("Dung lượng dữ liệu đã trích xuất (MB)", fmt(results['extracted_size'])),
]
for k, v in rows:
    print(f"  {k:<45} | {v}")

with open(OUTPUT_CSV, 'w', encoding='utf-8') as f:
    f.write("Thông số,Giá trị\n")
    for k, v in rows:
        f.write(f'"{k}","{v}"\n')
print(f"\nĐã lưu: {OUTPUT_CSV}")