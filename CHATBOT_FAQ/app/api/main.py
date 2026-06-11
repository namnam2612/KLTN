from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.conversations import router as conversations_router
from app.retrieval.retriever import retrieve_context
from app.retrieval.structured_lookup import (
    lookup_certificate_mapping,
    format_structured_certificate_answer,
)
from app.llm.client import generate_answer

app = FastAPI(title=settings.APP_NAME)

app.include_router(conversations_router)

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

    # 0) Case rất rõ: hồ sơ chuyển ngành / chuyển chương trình
    # Ưu tiên tuyệt đối Phụ lục 17, đặc biệt section "Hồ sơ gồm:"
    if "chuyển ngành" in q or "chuyển chương trình" in q:
        scored = []

        for ctx, src in pairs:
            ctx_lower = ctx.lower()
            file_name = (src.get("file") or src.get("filename") or src.get("source_file") or "").lower()
            section_title = (src.get("section_title") or "").lower()

            score = 0

            if "phụ lục 17" in file_name:
                score += 1000
            if "quy trình chuyển chương trình" in file_name:
                score += 1000
            if "chuyển chương trình" in ctx_lower:
                score += 300
            if "chuyển ngành" in ctx_lower:
                score += 300
            if "hồ sơ gồm" in ctx_lower or "hồ sơ gồm" in section_title:
                score += 800
            if "đơn đăng ký chuyển chương trình" in ctx_lower:
                score += 500
            if "bảng kết quả học tập" in ctx_lower:
                score += 400
            if "giấy báo trúng tuyển" in ctx_lower:
                score += 300

            # Trừ mạnh các nguồn dễ gây sai
            if "sổ tay sinh viên" in file_name:
                score -= 500
            if "phụ lục 19" in file_name:
                score -= 700
            if "chương trình thứ hai" in ctx_lower:
                score -= 700
            if "phụ lục 15" in file_name:
                score -= 500
            if "phụ lục 14" in file_name:
                score -= 500

            scored.append((score, ctx, src))

        scored.sort(key=lambda x: x[0], reverse=True)

        # Nếu tìm thấy Phụ lục 17 thì chỉ đưa Phụ lục 17 vào LLM
        pl17_items = [
            item for item in scored
            if "phụ lục 17" in (
                (item[2].get("file") or item[2].get("filename") or item[2].get("source_file") or "").lower()
            )
        ]

        if pl17_items:
            top = pl17_items[:4]
        else:
            top = scored[:4]

        return [x[1] for x in top], [x[2] for x in top]

    # =====================================================
    # 1) Nhóm quy đổi chứng chỉ: ưu tiên đúng bảng chứng chỉ quốc tế
    # =====================================================
    if any(k in q for k in ["ielts", "toeic", "toefl", "hsk", "topik", "jlpt", "quy đổi"]):
        filtered = []

        for ctx, src in pairs:
            file_name = (src.get("file") or "").lower()
            section_title = (src.get("section_title") or "").lower()
            ctx_lower = ctx.lower()
            score = 0

            if "ngoại ngữ quốc tế" in file_name:
                score += 100

            if "quy đổi chứng chỉ ngoại ngữ quốc tế" in file_name:
                score += 150

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

            if "điểm quy đổi" in ctx_lower:
                score += 80
            if "loại chứng chỉ quốc tế" in ctx_lower:
                score += 60

            if "xếp lớp tiếng anh" in file_name:
                score -= 150
            if "xếp lớp tiếng anh" in section_title:
                score -= 150

            if "điều kiện chứng chỉ được công nhận quy đổi" in ctx_lower:
                score -= 100

            filtered.append((score, ctx, src))

        filtered.sort(key=lambda x: x[0], reverse=True)

        if filtered:
            best_ctx = filtered[0][1]
            best_src = filtered[0][2]
            return [best_ctx], [best_src]

        return [pairs[0][0]], [pairs[0][1]]

    # =====================================================
    # 2) Nhóm mã học phần / CTĐT
    # =====================================================
    if any(k in q for k in [
        "mã học phần", "mã môn", "học phần", "tín chỉ",
        "chương trình đào tạo", "ctđt", "ctdt"
    ]):
        scored = []

        for ctx, src in pairs:
            file_name = (src.get("file") or "").lower()
            section_title = (src.get("section_title") or "").lower()
            ctx_lower = ctx.lower()
            score = 0

            if src.get("category") == "ctdt":
                score += 300

            if "sổ tay sinh viên" in file_name:
                score += 120

            if "chương trình đào tạo" in ctx_lower:
                score += 150
            if "mã học phần" in ctx_lower:
                score += 150
            if "học phần" in ctx_lower:
                score += 80
            if "tín chỉ" in ctx_lower:
                score += 80

            # Case cụ thể: quản trị thương hiệu
            if "quản trị thương hiệu" in q:
                if "quản trị thương hiệu" in ctx_lower:
                    score += 400
                if "mkt1408" in ctx_lower:
                    score += 400

            # Tránh kéo nhầm phụ lục học vụ/sửa điểm
            if "phụ lục 12" in file_name:
                score -= 300
            if "sửa điểm" in ctx_lower:
                score -= 200

            scored.append((score, ctx, src))

        scored.sort(key=lambda x: x[0], reverse=True)
        top = scored[:3]
        return [x[1] for x in top], [x[2] for x in top]

    # =====================================================
    # 3) Nhóm thẻ sinh viên
    # =====================================================
    if any(k in q for k in ["thẻ sinh viên", "mất thẻ", "làm lại thẻ", "cấp lại thẻ"]):
        scored = []

        for ctx, src in pairs:
            file_name = (src.get("file") or "").lower()
            section_title = (src.get("section_title") or "").lower()
            ctx_lower = ctx.lower()
            score = 0

            if "sổ tay sinh viên" in file_name:
                score += 300

            if "thẻ sinh viên" in ctx_lower:
                score += 300
            if "mất thẻ" in ctx_lower:
                score += 200
            if "làm lại thẻ" in ctx_lower:
                score += 200
            if "cấp lại thẻ" in ctx_lower:
                score += 200
            if "phòng" in ctx_lower:
                score += 50
            if "liên hệ" in ctx_lower:
                score += 50

            # Tránh kéo nhầm phụ lục sửa điểm/học vụ
            if "phụ lục 12" in file_name:
                score -= 300
            if "sửa điểm" in ctx_lower:
                score -= 200

            scored.append((score, ctx, src))

        scored.sort(key=lambda x: x[0], reverse=True)
        top = scored[:3]
        return [x[1] for x in top], [x[2] for x in top]

    # =====================================================
    # 4) Nhóm thủ tục: nghỉ học, chuyển ngành, thực tập, tốt nghiệp...
    # =====================================================
    if any(k in q for k in [
        "nghỉ học", "bảo lưu", "thực tập", "khóa luận",
        "đăng ký", "chuyển ngành", "chuyển chương trình",
        "chuyển trường", "tốt nghiệp", "thủ tục",
        "làm sao", "làm thế nào", "phải làm gì", "hồ sơ"
    ]):
        scored = []

        for ctx, src in pairs:
            ctx_lower = ctx.lower()
            file_name = (src.get("file") or "").lower()
            section_title = (src.get("section_title") or "").lower()

            score = 0

            # -----------------------------
            # Nghỉ học tạm thời / bảo lưu
            # -----------------------------
            if "nghỉ học" in q or "bảo lưu" in q:
                if "phụ lục 16" in file_name:
                    score += 400
                if "nghỉ học tạm thời" in file_name:
                    score += 400
                if "nghỉ học tạm thời" in ctx_lower:
                    score += 200
                if "quay trở lại học" in ctx_lower:
                    score += 120
                if "hồ sơ gồm" in ctx_lower or "hồ sơ gồm" in section_title:
                    score += 250

            # -----------------------------
            # Chuyển ngành / chuyển chương trình
            # -----------------------------
            if "chuyển ngành" in q or "chuyển chương trình" in q:
                if "phụ lục 17" in file_name:
                    score += 500
                if "quy trình chuyển chương trình" in file_name:
                    score += 500
                if "chuyển chương trình" in ctx_lower:
                    score += 200
                if "chuyển ngành" in ctx_lower:
                    score += 200
                if "hồ sơ gồm" in ctx_lower or "hồ sơ gồm" in section_title:
                    score += 300

                # Tránh lấy Sổ tay nếu đã có phụ lục thủ tục
                if "sổ tay sinh viên" in file_name:
                    score -= 150
                if "phụ lục 19" in file_name:
                    score -= 250

            # -----------------------------
            # Nội dung sinh viên thường cần
            # -----------------------------
            if "hồ sơ gồm" in ctx_lower or "hồ sơ gồm" in section_title:
                score += 200
            if "hồ sơ" in ctx_lower:
                score += 80
            if "đơn đăng ký" in ctx_lower or "đơn xin" in ctx_lower:
                score += 70
            if "phòng công tác chính trị" in ctx_lower:
                score += 60
            if "phòng tiếp sinh viên" in ctx_lower:
                score += 60
            if "cố vấn học tập" in ctx_lower:
                score += 50
            if "lệ phí" in ctx_lower:
                score += 40
            if "thời gian" in ctx_lower:
                score += 40
            if "điều kiện" in ctx_lower:
                score += 40
            if "bước" in ctx_lower:
                score += 30
            if "hướng dẫn" in ctx_lower:
                score += 20
            if "mẫu đơn" in ctx_lower:
                score += 20

            # Tránh chunk quá nội bộ nếu có chunk hồ sơ tốt hơn
            if "soạn và đăng tải thông báo" in ctx_lower:
                score -= 50

            scored.append((score, ctx, src))

        scored.sort(key=lambda x: x[0], reverse=True)

        # Lấy 4 context để LLM đủ dữ liệu trả lời
        top = scored[:4]
        return [x[1] for x in top], [x[2] for x in top]

    # =====================================================
    # 5) Mặc định
    # =====================================================
    return contexts[:3], sources[:3]


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "env": settings.APP_ENV
    }


@app.post("/ask")
def ask(req: AskRequest):
    # 1. Ưu tiên structured lookup trước cho case bảng quy đổi
    structured_result = lookup_certificate_mapping(req.question)
    if structured_result:
        answer = format_structured_certificate_answer(structured_result)

        rows = structured_result.get("rows", [])
        sources = []
        for row in rows:
            sources.append({
                "file": row.get("source_file"),
                "source_file": row.get("source_file"),
                "page": row.get("source_page"),
                "category": "structured",
                "sub_category": "certificate_mapping",
                "id": f"{row.get('certificate')}_{row.get('level')}_{row.get('group')}",
            })

        return {
            "question": req.question,
            "answer": answer,
            "sources": sources
        }

    # 2. Nếu không phải structured case thì dùng RAG + LLM như cũ
    docs = retrieve_context(req.question, k=5)

    print("ASK QUESTION =", req.question)
    print("DOC COUNT =", len(docs))

    for i, doc in enumerate(docs[:5], start=1):
        print("=" * 60)
        print("DOC", i)
        print("META =", doc.metadata)
        print("TEXT PREVIEW =", doc.page_content[:500])

    sources = []
    contexts = []

    for doc in docs:
        source_item = {
            "file": doc.metadata.get("filename") or doc.metadata.get("source_file"),
            "filename": doc.metadata.get("filename"),
            "source_file": doc.metadata.get("source_file"),
            "page": doc.metadata.get("page"),
            "category": doc.metadata.get("category"),
            "sub_category": doc.metadata.get("sub_category"),
            "section_title": doc.metadata.get("section_title"),
            "id": doc.metadata.get("id"),
        }
        sources.append(source_item)
        contexts.append(doc.page_content)

    llm_contexts, llm_sources = select_llm_contexts(req.question, contexts, sources)

    print("LLM CONTEXT COUNT =", len(llm_contexts))
    for i, ctx in enumerate(llm_contexts, start=1):
        print("-" * 60)
        print("LLM CTX", i)
        print(ctx[:700])

    answer = generate_answer(req.question, llm_contexts, llm_sources)

    return {
        "question": req.question,
        "answer": answer,
        "sources": sources
    }