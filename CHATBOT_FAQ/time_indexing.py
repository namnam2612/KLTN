"""
Đo thời gian indexing bằng cách import trực tiếp từ project root,
bypass mọi xung đột với site-packages.

Đặt file này tại: C:\\HỌC\\KLTN\\CHATBOT_FAQ\\time_indexing.py
Chạy: python time_indexing.py
"""
import sys, time
from pathlib import Path

# Đảm bảo Python tìm folder app/ ở project root TRƯỚC site-packages
PROJECT_ROOT = Path(__file__).parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

# Loại bỏ bất kỳ package "app" nào đã được cache từ site-packages
modules_to_remove = [m for m in sys.modules if m == 'app' or m.startswith('app.')]
for m in modules_to_remove:
    del sys.modules[m]

print(f"Project root: {PROJECT_ROOT}")
print(f"sys.path[0]: {sys.path[0]}")
print()

# Bây giờ import sẽ đến từ folder app/ ở project root
from app.retrieval.vector_store import build_vector_store

print("Bắt đầu indexing...")
t0 = time.time()

try:
    build_vector_store()
    elapsed = time.time() - t0
    print()
    print("=" * 60)
    print(f"  Thời gian indexing: {elapsed:.2f} giây ({elapsed/60:.2f} phút)")
    print("=" * 60)
except Exception as e:
    elapsed = time.time() - t0
    print(f"\n[LỖI] sau {elapsed:.2f}s: {e}")
    import traceback
    traceback.print_exc()