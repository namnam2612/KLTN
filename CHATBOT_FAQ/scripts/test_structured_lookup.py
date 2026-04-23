from app.retrieval.structured_lookup import (
    lookup_certificate_mapping,
    format_structured_certificate_answer,
)


def main():
    question = input("Nhập câu hỏi: ").strip()

    result = lookup_certificate_mapping(question)

    if not result:
        print("Không tìm thấy dữ liệu cấu trúc phù hợp.")
        return

    print("=" * 80)
    print("Kết quả structured lookup:")
    print("=" * 80)
    print(format_structured_certificate_answer(result))


if __name__ == "__main__":
    main()