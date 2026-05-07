import os
from typing import List, Dict

import httpx
from dotenv import load_dotenv

from app.llm.prompts import SYSTEM_PROMPT

load_dotenv()


def build_context_block(contexts: List[str], sources: List[Dict]) -> str:
    blocks = []

    for i, (ctx, src) in enumerate(zip(contexts, sources), start=1):
        file_name = (
            src.get("file")
            or src.get("filename")
            or src.get("source_file")
            or "Không rõ file"
        )
        page = src.get("page", "Không rõ trang")
        section_title = src.get("section_title", "")

        header = f"[Tài liệu {i}] File: {file_name} | Trang: {page}"

        if section_title:
            header += f" | Mục: {section_title}"

        blocks.append(f"{header}\n{ctx}")

    return "\n\n".join(blocks)


def build_extractive_fallback(contexts: List[str], sources: List[Dict]) -> str:
    if not contexts or not sources:
        return "Không tìm thấy thông tin phù hợp trong tài liệu."

    file_name = (
        sources[0].get("file")
        or sources[0].get("filename")
        or sources[0].get("source_file")
        or "Không rõ file"
    )
    page = sources[0].get("page", "Không rõ trang")

    combined_context = "\n\n".join(contexts[:4]).strip()

    return (
        "Tài liệu có thông tin liên quan. Nội dung tìm được:\n\n"
        f"{combined_context[:2200]}\n\n"
        f"Nguồn: {file_name}, trang {page}"
    )

def build_extractive_fallback(contexts: List[str], sources: List[Dict]) -> str:
    if not contexts or not sources:
        return "Không tìm thấy thông tin phù hợp trong tài liệu."

    file_name = (
        sources[0].get("file")
        or sources[0].get("filename")
        or sources[0].get("source_file")
        or "Không rõ file"
    )
    page = sources[0].get("page", "Không rõ trang")

    combined_context = "\n\n".join(contexts[:4]).strip()

    return (
        "Tài liệu có thông tin liên quan. Nội dung tìm được:\n\n"
        f"{combined_context[:2200]}\n\n"
        f"Nguồn: {file_name}, trang {page}"
    )

def generate_answer(question: str, contexts: List[str], sources: List[Dict]) -> str:
    api_key = os.getenv("LLM_API_KEY")
    model = os.getenv("LLM_MODEL")
    base_url = os.getenv("LLM_BASE_URL")

    if not api_key or not model or not base_url:
        return "Chưa cấu hình LLM_API_KEY, LLM_MODEL hoặc LLM_BASE_URL trong file .env."

    if not contexts:
        return "Không tìm thấy thông tin phù hợp trong tài liệu."

    context_block = build_context_block(contexts, sources)

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://127.0.0.1:8010",
        "X-OpenRouter-Title": "AI FAQ Project",
    }

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Câu hỏi:\n{question}\n\n"
                    f"Ngữ cảnh tài liệu:\n{context_block}\n\n"
                    "Yêu cầu rất quan trọng:\n"
                    "- Chỉ dùng thông tin nhìn thấy trực tiếp trong ngữ cảnh.\n"
                    "- Nếu ngữ cảnh có thông tin liên quan đến câu hỏi, hãy trả lời dựa trên ngữ cảnh đó.\n"
                    "- Không được trả lời 'Không tìm thấy thông tin phù hợp trong tài liệu' nếu ngữ cảnh có nhắc trực tiếp đến chủ đề người dùng hỏi.\n"
                    "- Nếu câu hỏi hỏi về thủ tục, hãy nêu hồ sơ, nơi xử lý/liên hệ, các bước hoặc lưu ý nếu có trong ngữ cảnh.\n"
                    "- Nếu câu hỏi hỏi về hồ sơ, hãy liệt kê đúng các giấy tờ có trong ngữ cảnh.\n"
                    "- Nếu là bảng quy đổi, chỉ liệt kê đúng các mức xuất hiện trong bảng.\n"
                    "- Không tự suy ra thông tin ngoài tài liệu.\n"
                    "- Chỉ nói 'Không tìm thấy thông tin phù hợp trong tài liệu.' khi toàn bộ ngữ cảnh không liên quan đến câu hỏi.\n"
                ),
            },
        ],
        "temperature": 0,
    }

    url = f"{base_url.rstrip('/')}/chat/completions"

    try:
        response = httpx.post(url, headers=headers, json=payload, timeout=60.0)
        response.raise_for_status()

        data = response.json()

        if "error" in data:
            error_message = data["error"].get("message", "Unknown error")
            error_code = data["error"].get("code", "")

            if str(error_code) == "429" or "rate limit" in error_message.lower():
                return (
                    "Hệ thống AI tạm thời đã hết quota mô hình miễn phí hoặc đang quá tải.\n\n"
                    + build_extractive_fallback(contexts, sources)
                )

            return f"Lỗi LLM: {data}"

        if "choices" not in data:
            return f"Lỗi LLM: {data}"

        answer = data["choices"][0]["message"]["content"].strip()

        # Fallback quan trọng:
        # Nếu LLM vẫn trả không tìm thấy trong khi retriever đã có context đúng,
        # trả trực tiếp nội dung tài liệu để tránh mất câu trả lời.
        if (
            "không tìm thấy thông tin phù hợp" in answer.lower()
            and contexts
            and sources
        ):
            return build_extractive_fallback(contexts, sources)

        return answer


    except httpx.HTTPStatusError as e:

        status_code = e.response.status_code

        response_text = e.response.text

        # Gemini/OpenRouter/Groq... có thể trả 429 hoặc 5xx khi quá tải.

        # Không hiện lỗi thô lên UI, fallback sang context đã retrieve được.

        if status_code in [429, 500, 502, 503, 504]:
            return (

                    "Hệ thống AI tạm thời đang quá tải hoặc không phản hồi ổn định.\n\n"

                    + build_extractive_fallback(contexts, sources)

            )

        return f"Lỗi HTTP: {status_code} - {response_text}"


    except Exception as e:

        return f"Lỗi khi gọi LLM: {str(e)}"