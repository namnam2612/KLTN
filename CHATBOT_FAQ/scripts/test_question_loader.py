from pathlib import Path


def main():
    file_path = Path("tests/test_data/test_questions.txt")

    if not file_path.exists():
        print("Không tìm thấy file test questions.")
        return

    content = file_path.read_text(encoding="utf-8")
    lines = [line.strip() for line in content.splitlines() if line.strip()]

    print(f"Tổng số dòng: {len(lines)}")
    print("-" * 80)

    for line in lines[:15]:
        print(line)


if __name__ == "__main__":
    main()