def build_mock_answer(question: str, contexts: list[str], sources: list[dict]) -> str:
    if not contexts:
        return "Chưa tìm thấy thông tin phù hợp trong tài liệu."

    top_context = contexts[0].strip()
    top_source = sources[0] if sources else {}

    file_name = top_source.get("file", "Không rõ file")
    page = top_source.get("page", "Không rõ trang")

    answer = (
        f"Câu hỏi: {question}\n\n"
        f"Thông tin gần nhất tìm được trong tài liệu:\n{top_context[:1200]}\n\n"
        f"Nguồn: {file_name} - trang {page}"
    )
    return answer