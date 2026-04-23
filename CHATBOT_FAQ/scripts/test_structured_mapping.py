import json
from pathlib import Path


def main():
    file_path = Path("data/structured/quy_doi/english_certificate_mapping.json")

    if not file_path.exists():
        print("Không tìm thấy file dữ liệu cấu trúc.")
        return

    data = json.loads(file_path.read_text(encoding="utf-8"))

    print(f"Số record: {len(data)}")
    print("-" * 80)

    for item in data[:3]:
        print(item)


if __name__ == "__main__":
    main()