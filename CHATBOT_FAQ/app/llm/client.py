import os
from typing import List, Dict

import httpx
from dotenv import load_dotenv

from app.llm.prompts import SYSTEM_PROMPT

load_dotenv()


def build_context_block(contexts: List[str], sources: List[Dict]) -> str:
    blocks = []

    for i, (ctx, src) in enumerate(zip(contexts, sources), start=1):
        file_name = src.get("file", "Không rõ file")
        page = src.get("page", "Không rõ trang")
        blocks.append(f"[Tài liệu {i}] File: {file_name} | Trang: {page}\n{ctx}")

    return "\n\n".join(blocks)


def generate_answer(question: str, contexts: List[str], sources: List[Dict]) -> str:
    api_key = os.getenv("LLM_API_KEY")
    model = os.getenv("LLM_MODEL")
    base_url = os.getenv("LLM_BASE_URL")

    if not api_key or not model or not base_url:
        return "Chưa cấu hình LLM_API_KEY, LLM_MODEL hoặc LLM_BASE_URL trong file .env."

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
    "- Nếu là bảng quy đổi, chỉ liệt kê đúng các mức xuất hiện trong bảng.\n"
    "- Không tự suy ra mức khác.\n"
    "- Không trộn bảng xếp lớp với bảng quy đổi chứng chỉ nếu chúng không cùng mục đích.\n"
    "- Nếu dữ liệu chưa đủ rõ để trả lời chính xác, nói: Không tìm thấy thông tin phù hợp trong tài liệu.\n"
),
            },
        ],
        "temperature": 0,
    }

    url = f"{base_url}/chat/completions"

    try:
        response = httpx.post(url, headers=headers, json=payload, timeout=60.0)
        response.raise_for_status()

        data = response.json()

        if "error" in data:
            error_message = data["error"].get("message", "Unknown error")
            error_code = data["error"].get("code", "")

            if str(error_code) == "429" or "rate limit" in error_message.lower():
                if contexts and sources:
                    file_name = sources[0].get("file", "Không rõ file")
                    page = sources[0].get("page", "Không rõ trang")
                    preview = contexts[0][:1000].strip()

                    return (
                        "Hệ thống AI tạm thời đã hết quota mô hình miễn phí hoặc đang quá tải.\n\n"
                        "Thông tin gần nhất tìm được trong tài liệu:\n"
                        f"{preview}\n\n"
                        f"Nguồn: {file_name} (trang {page})"
                    )

                return (
                    "Hệ thống AI tạm thời đã hết quota mô hình miễn phí hoặc đang quá tải. "
                    "Vui lòng thử lại sau."
                )

            return f"Lỗi LLM: {data}"

        if "choices" not in data:
            return f"Lỗi LLM: {data}"

        return data["choices"][0]["message"]["content"].strip()

    except httpx.HTTPStatusError as e:
        status_code = e.response.status_code
        response_text = e.response.text

        if status_code == 429:
            if contexts and sources:
                file_name = sources[0].get("file", "Không rõ file")
                page = sources[0].get("page", "Không rõ trang")
                preview = contexts[0][:1000].strip()

                return (
                    "Hệ thống AI tạm thời đã hết quota mô hình miễn phí hoặc đang quá tải.\n\n"
                    "Thông tin gần nhất tìm được trong tài liệu:\n"
                    f"{preview}\n\n"
                    f"Nguồn: {file_name} (trang {page})"
                )

            return (
                "Hệ thống AI tạm thời đã hết quota mô hình miễn phí hoặc đang quá tải. "
                "Vui lòng thử lại sau."
            )

        return f"Lỗi HTTP: {status_code} - {response_text}"

    except Exception as e:
        return f"Lỗi khi gọi LLM: {str(e)}"