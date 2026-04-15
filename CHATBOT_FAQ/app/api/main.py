from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.retrieval.retriever import retrieve_context
from app.llm.client import generate_answer

app = FastAPI(title=settings.APP_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AskRequest(BaseModel):
    question: str


def select_llm_contexts(question: str, contexts: list[str], sources: list[dict]):
    q = question.lower()

    pairs = list(zip(contexts, sources))

    if not pairs:
        return [], []

    # 1) Nhóm quy đổi chứng chỉ: ưu tiên đúng bảng chứng chỉ quốc tế
    if any(k in q for k in ["ielts", "toeic", "toefl", "hsk", "topik", "jlpt", "quy đổi"]):
        filtered = []
        for ctx, src in pairs:
            file_name = (src.get("file") or "").lower()
            ctx_lower = ctx.lower()
            score = 0

            # Ưu tiên đúng file quy đổi chứng chỉ
            if "ngoại ngữ quốc tế" in file_name:
                score += 100

            # Ưu tiên đúng từ khóa trong chunk
            if "ielts" in q and "ielts" in ctx_lower:
                score += 120
            if "toeic" in q and "toeic" in ctx_lower:
                score += 120
            if "toefl" in q and "toefl" in ctx_lower:
                score += 120
            if "hsk" in q and "hsk" in ctx_lower:
                score += 120
            if "topik" in q and "topik" in ctx_lower:
                score += 120
            if "jlpt" in q and "jlpt" in ctx_lower:
                score += 120

            # Ưu tiên chunk có nội dung bảng quy đổi
            if "điểm quy đổi" in ctx_lower:
                score += 80
            if "loại chứng chỉ quốc tế" in ctx_lower:
                score += 60

            # Phạt mạnh file xếp lớp tiếng Anh
            if "xếp lớp tiếng anh" in file_name:
                score -= 150

            # Phạt chunk mở đầu chung chung
            if "điều kiện chứng chỉ được công nhận quy đổi" in ctx_lower:
                score -= 100

            filtered.append((score, ctx, src))

        filtered.sort(key=lambda x: x[0], reverse=True)

        if filtered:
            best_ctx = filtered[0][1]
            best_src = filtered[0][2]
            return [best_ctx], [best_src]

        return [pairs[0][0]], [pairs[0][1]]

    # 2) Nhóm thủ tục: ưu tiên hồ sơ, điều kiện, bước
    if any(k in q for k in ["nghỉ học", "thực tập", "khóa luận", "đăng ký", "chuyển ngành", "chuyển trường", "tốt nghiệp"]):
        scored = []
        for ctx, src in pairs:
            section = (ctx.splitlines()[0] if ctx else "").lower()
            score = 0

            if "hồ sơ" in ctx.lower():
                score += 50
            if "điều kiện" in ctx.lower():
                score += 40
            if "bước" in ctx.lower():
                score += 30
            if "hướng dẫn" in ctx.lower():
                score += 20
            if "mẫu đơn" in ctx.lower():
                score += 10
            if "hồ sơ" in section:
                score += 10
            if "điều kiện" in section:
                score += 10

            scored.append((score, ctx, src))

        scored.sort(key=lambda x: x[0], reverse=True)
        top = scored[:2]
        return [x[1] for x in top], [x[2] for x in top]

    # 3) Mặc định: lấy 2 context đầu
    return contexts[:2], sources[:2]


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "env": settings.APP_ENV
    }


@app.post("/ask")
def ask(req: AskRequest):
    docs = retrieve_context(req.question, k=5)

    sources = []
    contexts = []

    for doc in docs:
        source_item = {
            "file": doc.metadata.get("filename"),
            "source_file": doc.metadata.get("source_file"),
            "page": doc.metadata.get("page"),
            "category": doc.metadata.get("category"),
            "sub_category": doc.metadata.get("sub_category"),
            "id": doc.metadata.get("id"),
        }
        sources.append(source_item)
        contexts.append(doc.page_content)

    llm_contexts, llm_sources = select_llm_contexts(req.question, contexts, sources)
    answer = generate_answer(req.question, llm_contexts, llm_sources)

    return {
        "question": req.question,
        "answer": answer,
        "sources": sources
    }