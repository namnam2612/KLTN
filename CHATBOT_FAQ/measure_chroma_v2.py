"""
Script đo số liệu hệ thống RAG dùng ChromaDB.
Đã sửa đúng theo cấu trúc thư mục thực tế của project CHATBOT_FAQ.

Chạy: python measure_chroma_v2.py
"""
import os, time, json
from pathlib import Path

# ============ CONFIG (đã sửa đúng theo project của bạn) ============
PROJECT_ROOT = Path(__file__).parent
PDF_SOURCE_DIR = PROJECT_ROOT / "data" / "raw"
EXTRACTED_DIR = PROJECT_ROOT / "data" / "extracted"
CLEANED_DIR = PROJECT_ROOT / "data" / "cleaned"
CHUNKS_JSONL = PROJECT_ROOT / "data" / "chunks" / "chunks.jsonl"
INDEX_DIR = PROJECT_ROOT / "data" / "indexes" / "chroma_db"
OUTPUT_CSV = PROJECT_ROOT / "he_thong_so_lieu.csv"


# Tên collection không cần biết trước — script sẽ tự tìm
# ====================================================================


def count_pdfs(d):
    if not d.exists(): return None
    return len(list(d.rglob("*.pdf"))) + len(list(d.rglob("*.PDF")))


def count_pages(d):
    try:
        import fitz
    except ImportError:
        return None
    if not d.exists(): return None
    total = 0
    for p in list(d.rglob("*.pdf")) + list(d.rglob("*.PDF")):
        try:
            doc = fitz.open(str(p))
            total += doc.page_count
            doc.close()
        except:
            pass
    return total


def count_chunks_from_jsonl(p):
    if not p.exists(): return None
    return sum(1 for _ in open(p, encoding='utf-8'))


def get_avg_chunk_length_from_jsonl(p, max_sample=500):
    """Tính độ dài chunk trung bình từ file jsonl."""
    if not p.exists(): return None
    lengths = []
    with open(p, encoding='utf-8') as f:
        for i, line in enumerate(f):
            if i >= max_sample: break
            try:
                obj = json.loads(line)
                # Tìm trường chứa text - đoán theo tên phổ biến
                text = obj.get('text') or obj.get('page_content') or obj.get('content') or ''
                if text:
                    lengths.append(len(text.split()))
            except:
                pass
    if not lengths: return None
    return round(sum(lengths) / len(lengths), 1)


def get_chroma_stats(persist_dir):
    """Tự liệt kê tất cả collection và lấy stats."""
    try:
        import chromadb
    except ImportError:
        return None, "Thiếu chromadb. Cài: pip install chromadb"
    if not persist_dir.exists():
        return None, f"Không có thư mục: {persist_dir}"
    try:
        client = chromadb.PersistentClient(path=str(persist_dir))
        collections = client.list_collections()
        if not collections:
            return None, "Không có collection nào trong ChromaDB"

        results = {}
        for col_info in collections:
            # ChromaDB phiên bản mới: col_info là Collection object hoặc tên (string)
            name = col_info.name if hasattr(col_info, 'name') else str(col_info)
            col = client.get_collection(name)
            count = col.count()

            # Lấy mẫu để xem vector_dim và độ dài chunk
            vector_dim = None
            avg_words = None
            try:
                peek = col.peek(limit=1)
                embeddings = peek.get('embeddings')
                if embeddings is not None and len(embeddings) > 0:
                    vector_dim = len(embeddings[0])

                # Lấy mẫu lớn hơn để tính avg
                peek_large = col.peek(limit=200)
                docs = peek_large.get('documents') or []
                if docs:
                    avg_words = round(sum(len(d.split()) for d in docs if d) / len([d for d in docs if d]), 1)
            except Exception as e:
                pass

            results[name] = {
                'count': count,
                'vector_dim': vector_dim,
                'avg_chunk_words': avg_words,
            }
        return results, None
    except Exception as e:
        return None, f"Lỗi: {e}"


def get_dir_size_mb(d):
    if not Path(d).exists(): return None
    total = sum(f.stat().st_size for f in Path(d).rglob('*') if f.is_file())
    return round(total / (1024 * 1024), 2)


def fmt(v):
    return "—" if v is None else str(v)


# ====================== ĐO ======================
print("=" * 70)
print(" ĐO SỐ LIỆU HỆ THỐNG ".center(70, "="))
print("=" * 70)

results = {}

# 1. PDF count
results['pdf'] = count_pdfs(PDF_SOURCE_DIR)
print(f"[1] Số file PDF: {fmt(results['pdf'])}")

# 2. Page count
results['pages'] = count_pages(PDF_SOURCE_DIR)
print(f"[2] Tổng số trang: {fmt(results['pages'])}")

# 3. Chunks từ jsonl
results['chunks_jsonl'] = count_chunks_from_jsonl(CHUNKS_JSONL)
print(f"[3a] Số chunk trong chunks.jsonl: {fmt(results['chunks_jsonl'])}")

# 4. Avg chunk length từ jsonl
results['avg_chunk_jsonl'] = get_avg_chunk_length_from_jsonl(CHUNKS_JSONL)
print(f"[3b] Độ dài chunk trung bình (từ jsonl): {fmt(results['avg_chunk_jsonl'])} từ")

# 5. Chroma stats
chroma_data, err = get_chroma_stats(INDEX_DIR)
if err:
    print(f"[4-5] Lỗi ChromaDB: {err}")
    results['chunks_db'] = None
    results['vector_dim'] = None
    results['avg_chunk_db'] = None
else:
    # Có thể có nhiều collection - in ra tất cả
    print(f"[4] Số collection trong ChromaDB: {len(chroma_data)}")
    for name, stats in chroma_data.items():
        print(f"    Collection '{name}':")
        print(f"      - Số chunk: {stats['count']}")
        print(f"      - Vector dim: {fmt(stats['vector_dim'])}")
        print(f"      - Độ dài chunk trung bình (từ DB): {fmt(stats['avg_chunk_words'])} từ")

    # Lấy collection lớn nhất làm số chính
    main_col = max(chroma_data.values(), key=lambda x: x['count'])
    results['chunks_db'] = main_col['count']
    results['vector_dim'] = main_col['vector_dim']
    results['avg_chunk_db'] = main_col['avg_chunk_words']

# 6. Dung lượng
results['db_size'] = get_dir_size_mb(INDEX_DIR)
print(f"[6] Dung lượng ChromaDB: {fmt(results['db_size'])} MB")

results['extracted_size'] = get_dir_size_mb(EXTRACTED_DIR)
print(f"[7] Dung lượng dữ liệu extracted: {fmt(results['extracted_size'])} MB")

results['cleaned_size'] = get_dir_size_mb(CLEANED_DIR)
print(f"[8] Dung lượng dữ liệu cleaned: {fmt(results['cleaned_size'])} MB")

results['chunks_jsonl_size'] = get_dir_size_mb(CHUNKS_JSONL.parent)
print(f"[9] Dung lượng folder chunks: {fmt(results['chunks_jsonl_size'])} MB")

# ====================== KẾT QUẢ ======================
print()
print("=" * 70)
print(" KẾT QUẢ — COPY VÀO LUẬN VĂN ".center(70, "="))
print("=" * 70)

# Ưu tiên số từ DB, fallback sang jsonl
final_chunks = results['chunks_db'] or results['chunks_jsonl']
final_avg = results['avg_chunk_db'] or results['avg_chunk_jsonl']

rows = [
    ("Số văn bản quy chế nguồn (PDF)", fmt(results['pdf'])),
    ("Tổng số trang văn bản đã xử lý", fmt(results['pages'])),
    ("Số chunk được sinh ra", fmt(final_chunks)),
    ("Độ dài chunk trung bình (từ)", fmt(final_avg)),
    ("Số chiều của vector embedding", fmt(results['vector_dim'])),
    ("Dung lượng ChromaDB trên đĩa (MB)", fmt(results['db_size'])),
    ("Dung lượng dữ liệu đã trích xuất (MB)", fmt(results['extracted_size'])),
]
for k, v in rows:
    print(f"  {k:<45} | {v}")

with open(OUTPUT_CSV, 'w', encoding='utf-8') as f:
    f.write("Thông số,Giá trị\n")
    for k, v in rows:
        f.write(f'"{k}","{v}"\n')

print(f"\nĐã lưu kết quả vào: {OUTPUT_CSV}")
print()
print("=" * 70)
print(" GHI CHÚ — ĐO THỜI GIAN INDEXING ".center(70, "="))
print("=" * 70)
print("""
Để đo thời gian indexing, chạy lại script build index của bạn với timer:

  Windows PowerShell:
    Measure-Command { python scripts/build_index.py }

  Hoặc cmd:
    python -c "import time; t=time.time(); exec(open('scripts/build_index.py').read()); print(f'Time: {time.time()-t:.1f}s')"

Nếu tên script build khác (không phải build_index.py), xem trong folder scripts/
""")
