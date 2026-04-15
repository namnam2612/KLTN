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


def deduplicate_docs(docs):
    seen = set()
    filtered = []

    for doc in docs:
        key = (
            doc.metadata.get("filename"),
            doc.metadata.get("page"),
            doc.page_content[:200]
        )
        if key not in seen:
            seen.add(key)
            filtered.append(doc)

    return filtered


def score_doc_for_query(query: str, doc):
    q = query.lower()
    text = doc.page_content.lower()
    filename = (doc.metadata.get("filename") or "").lower()

    score = 0

    if "ielts" in q:
        if "ielts" in text:
            score += 100
        if "ngoại ngữ quốc tế" in filename:
            score += 80
        if "xếp lớp tiếng anh" in filename:
            score -= 50
        if "a1" in text or "a2" in text or "b1" in text:
            score -= 20

    if "toeic" in q and "toeic" in text:
        score += 100

    if "toefl" in q and "toefl" in text:
        score += 100

    return score


def rerank_docs(query: str, docs):
    return sorted(docs, key=lambda d: score_doc_for_query(query, d), reverse=True)


def filter_docs_by_query(docs, query: str):
    query_lower = query.lower()

    if "ielts" in query_lower:
        return [
            doc for doc in docs
            if "ielts" in doc.page_content.lower()
            or "tiếng anh" in doc.page_content.lower()
        ]

    if "toeic" in query_lower:
        return [
            doc for doc in docs
            if "toeic" in doc.page_content.lower()
        ]

    if "toefl" in query_lower:
        return [
            doc for doc in docs
            if "toefl" in doc.page_content.lower()
        ]

    return docs


def retrieve_context(query: str, k: int = 5):
    db = load_vector_store()
    meta_filter = infer_filter(query)

    if meta_filter:
        docs = db.similarity_search(query, k=8, filter=meta_filter)
    else:
        docs = db.similarity_search(query, k=8)

    docs = deduplicate_docs(docs)
    docs = rerank_docs(query, docs)
    docs = filter_docs_by_query(docs, query)

    return docs[:3]