import os
from typing import List, Dict

import httpx
from dotenv import load_dotenv

from app.llm.prompts import SYSTEM_PROMPT

load_dotenv()


# ===========================================================================
# Prompt cho câu hỏi NGOÀI phạm vi trường (loại B).
# Bạn có thể chuyển constant này sang app/llm/prompts.py rồi import vào.
# ===========================================================================
GENERAL_SYSTEM_PROMPT = """Bạn là trợ lý AI hữu ích, trả lời bằng tiếng Việt.
Đây là câu hỏi kiến thức chung / ngoài phạm vi Trường Đại học Thăng Long.
- Trả lời chính xác, ngắn gọn, đúng trọng tâm.
- Nếu có kết quả tìm kiếm web kèm theo, hãy dựa vào đó cho thông tin cập nhật.
- Không bịa. Nếu không chắc, hãy nói rõ là không chắc.
- KHÔNG cố ép câu trả lời vào tài liệu nội bộ của trường."""


# ===========================================================================
# Helpers: ghép ngữ cảnh & fallback trích nguyên văn (chỉ dùng cho loại A)
# ===========================================================================

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


# ===========================================================================
# Lớp gọi OpenRouter chung
# ===========================================================================

class LLMError(Exception):
    """Lỗi do API trả về trong body (HTTP 200 nhưng có key 'error')."""
    def __init__(self, message: str, status_code=None):
        super().__init__(message)
        self.status_code = status_code


def _get_config():
    return (
        os.getenv("LLM_API_KEY"),
        os.getenv("LLM_MODEL"),
        os.getenv("LLM_BASE_URL"),
    )


def _post_chat(payload: dict) -> dict:
    api_key, _, base_url = _get_config()
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://127.0.0.1:8010",
        "X-OpenRouter-Title": "AI FAQ Project",
    }
    url = f"{base_url.rstrip('/')}/chat/completions"

    response = httpx.post(url, headers=headers, json=payload, timeout=60.0)
    response.raise_for_status()
    data = response.json()

    # OpenRouter đôi khi trả HTTP 200 nhưng body chứa 'error' (vd hết quota).
    if "error" in data:
        err = data["error"]
        raise LLMError(err.get("message", "Unknown error"), err.get("code"))
    if "choices" not in data:
        raise LLMError(f"Phản hồi không hợp lệ: {data}")
    return data


def _content(data: dict) -> str:
    return data["choices"][0]["message"]["content"].strip()


# ===========================================================================
# Bước 1: phân loại câu hỏi A (về trường) / B (ngoài phạm vi)
# ---------------------------------------------------------------------------
# Có thể thay bằng phân loại theo từ khóa nếu muốn tiết kiệm 1 lượt gọi LLM.
# ===========================================================================

CLASSIFY_PROMPT = """Bạn là bộ phân loại câu hỏi cho chatbot Trường Đại học Thăng Long.
Phân loại câu hỏi vào đúng MỘT nhãn:
- A: liên quan đến trường (quy chế, quy định, thủ tục, học phí, điểm, học bổng,
  chương trình đào tạo, ký túc xá, phòng ban, chứng chỉ, hoặc thông tin riêng của trường).
- B: kiến thức chung / ngoài phạm vi trường (học thuật, đời sống, công nghệ, thời sự...).
Chỉ trả về đúng một ký tự: A hoặc B. Không giải thích."""


def classify_question(question: str) -> str:
    _, model, _ = _get_config()
    try:
        data = _post_chat({
            "model": model,
            "messages": [
                {"role": "system", "content": CLASSIFY_PROMPT},
                {"role": "user", "content": question},
            ],
            "temperature": 0,
            "max_tokens": 2,
        })
        label = _content(data).upper()
        return "B" if label.startswith("B") else "A"
    except Exception:
        # Phân loại lỗi -> mặc định coi như câu hỏi về trường (an toàn hơn).
        return "A"


# ===========================================================================
# Bước 2a: trả lời câu hỏi VỀ TRƯỜNG (RAG nghiêm ngặt)
# ===========================================================================

def _answer_school(question: str, contexts: List[str], sources: List[Dict]) -> str:
    if not contexts:
        return (
            "Không tìm thấy thông tin phù hợp trong tài liệu của trường. "
            "Bạn nên liên hệ phòng/ban phụ trách để được xác nhận chính xác."
        )

    context_block = build_context_block(contexts, sources)
    data = _post_chat({
        "model": os.getenv("LLM_MODEL"),
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": (
                f"Câu hỏi:\n{question}\n\n"
                f"Ngữ cảnh tài liệu:\n{context_block}\n\n"
                "Yêu cầu (câu hỏi về Trường Đại học Thăng Long):\n"
                "- Chỉ dùng thông tin nhìn thấy trực tiếp trong ngữ cảnh.\n"
                "- Nếu ngữ cảnh có thông tin liên quan, phải trả lời dựa trên ngữ cảnh đó.\n"
                "- Không bịa thông tin riêng của trường ngoài tài liệu.\n"
                "- Câu hỏi thủ tục: nêu hồ sơ, nơi xử lý/liên hệ, các bước, lưu ý nếu có.\n"
                "- Câu hỏi về hồ sơ: liệt kê đúng các giấy tờ có trong ngữ cảnh.\n"
                "- Bảng quy đổi: chỉ liệt kê đúng các mức xuất hiện trong bảng.\n"
                "- Chỉ nói 'Không tìm thấy thông tin phù hợp trong tài liệu.' "
                "khi toàn bộ ngữ cảnh không liên quan đến câu hỏi.\n"
            )},
        ],
        "temperature": 0,
    })

    answer = _content(data)

    # Fallback: nếu LLM nói không tìm thấy dù retriever đã có context đúng,
    # trả thẳng nội dung tài liệu để tránh mất câu trả lời.
    if "không tìm thấy thông tin phù hợp" in answer.lower() and contexts and sources:
        return build_extractive_fallback(contexts, sources)
    return answer


# ===========================================================================
# Bước 2b: trả lời câu hỏi NGOÀI phạm vi (kiến thức LLM + tùy chọn web search)
# ===========================================================================

def _gemini_native_base() -> str:
    """LLM_BASE_URL kết thúc bằng /v1beta/openai -> bỏ /openai để gọi API native."""
    base = (os.getenv("LLM_BASE_URL") or "").rstrip("/")
    if base.endswith("/openai"):
        base = base[: -len("/openai")]
    return base  # .../v1beta


def _answer_general_web(question: str) -> str:
    """Trả lời câu hỏi loại B kèm Google Search grounding qua API native Gemini.
    Phải dùng native vì endpoint OpenAI-compat chỉ hỗ trợ grounding trên Gemini 3+.
    """
    api_key, model, _ = _get_config()
    url = f"{_gemini_native_base()}/models/{model}:generateContent?key={api_key}"

    payload = {
        "system_instruction": {"parts": [{"text": GENERAL_SYSTEM_PROMPT}]},
        "contents": [{"role": "user", "parts": [{"text": question}]}],
        # Bật grounding với Google Search (Gemini 2.x trở lên dùng "google_search").
        "tools": [{"google_search": {}}],
    }

    resp = httpx.post(url, json=payload, timeout=60.0)
    resp.raise_for_status()
    data = resp.json()

    cand = data["candidates"][0]
    parts = cand.get("content", {}).get("parts", [])
    answer = "".join(p.get("text", "") for p in parts).strip()

    # Ghép nguồn từ groundingMetadata
    cites, seen = [], set()
    chunks = cand.get("groundingMetadata", {}).get("groundingChunks", []) or []
    for ch in chunks:
        web = ch.get("web", {})
        uri, title = web.get("uri"), web.get("title")
        if uri and uri not in seen:
            seen.add(uri)
            cites.append(f"- {title or uri} ({uri})")
    if cites:
        answer += "\n\nNguồn (web):\n" + "\n".join(cites)
    return answer


def _answer_general(question: str) -> str:
    use_web = os.getenv("USE_WEB_SEARCH", "false").lower() in ("1", "true", "yes")

    if use_web:
        try:
            return _answer_general_web(question)
        except Exception:
            # Web search lỗi -> rơi xuống dùng kiến thức của chính LLM.
            pass

    # Không web: dùng kiến thức của chính Gemini qua endpoint OpenAI-compat.
    data = _post_chat({
        "model": os.getenv("LLM_MODEL"),
        "messages": [
            {"role": "system", "content": GENERAL_SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ],
        "temperature": 0.2,
    })
    return _content(data)


# ===========================================================================
# Hàm chính: giữ nguyên chữ ký để không vỡ phần còn lại của repo
# ===========================================================================

def generate_answer(question: str, contexts: List[str], sources: List[Dict]) -> str:
    api_key, model, base_url = _get_config()
    if not api_key or not model or not base_url:
        return "Chưa cấu hình LLM_API_KEY, LLM_MODEL hoặc LLM_BASE_URL trong file .env."

    try:
        label = classify_question(question)
        if label == "B":
            return _answer_general(question)
        return _answer_school(question, contexts, sources)

    except LLMError as e:
        if str(e.status_code) == "429" or "rate limit" in str(e).lower():
            if contexts and sources:
                return (
                    "Hệ thống AI tạm thời hết quota/quá tải.\n\n"
                    + build_extractive_fallback(contexts, sources)
                )
            return "Hệ thống AI tạm thời hết quota hoặc quá tải, bạn thử lại sau ít phút nhé."
        return f"Lỗi LLM: {e}"

    except httpx.HTTPStatusError as e:
        status_code = e.response.status_code
        if status_code in (429, 500, 502, 503, 504):
            if contexts and sources:
                return (
                    "Hệ thống AI tạm thời đang quá tải hoặc không phản hồi ổn định.\n\n"
                    + build_extractive_fallback(contexts, sources)
                )
            return "Hệ thống AI tạm thời quá tải, bạn thử lại sau ít phút nhé."
        return f"Lỗi HTTP: {status_code} - {e.response.text}"

    except Exception as e:
        return f"Lỗi khi gọi LLM: {str(e)}"
