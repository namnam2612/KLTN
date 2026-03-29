from app.retrieval.vector_store import load_vector_store


def infer_filter(question: str):
    q = question.lower()

    keywords_quy_doi = [
        "quy đổi", "ielts", "toeic", "toefl",
        "hsk", "topik", "jlpt", "xếp lớp tiếng anh",
        "chứng chỉ ngoại ngữ"
    ]

    if any(k in q for k in keywords_quy_doi):
        return {"sub_category": "quy_doi_chung_chi_diem"}

    if "thực tập" in q or "khóa luận" in q or "kltn" in q:
        return {"sub_category": "thuc_tap_kltn"}

    if (
        "nghỉ học" in q
        or "chuyển ngành" in q
        or "chuyển chương trình" in q
        or "chuyển trường" in q
        or "đăng ký học" in q
        or "cảnh báo học tập" in q
        or "tốt nghiệp" in q
        or "sửa điểm" in q
    ):
        return {"sub_category": "quy_trinh_hoc_vu"}

    return None


def retrieve_context(query: str, k: int = 5):
    db = load_vector_store()
    meta_filter = infer_filter(query)

    if meta_filter:
        docs = db.similarity_search(query, k=k, filter=meta_filter)
        if docs:
            return docs

    return db.similarity_search(query, k=k)