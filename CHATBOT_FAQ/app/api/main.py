from fastapi import FastAPI
from pydantic import BaseModel

from app.core.config import settings
from app.retrieval.retriever import retrieve_context
from app.llm.answer_builder import build_mock_answer

app = FastAPI(title=settings.APP_NAME)


class AskRequest(BaseModel):
    question: str


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
        sources.append({
            "file": doc.metadata.get("filename"),
            "source_file": doc.metadata.get("source_file"),
            "page": doc.metadata.get("page"),
            "category": doc.metadata.get("category"),
            "sub_category": doc.metadata.get("sub_category"),
            "id": doc.metadata.get("id"),
        })
        contexts.append(doc.page_content)

    answer = build_mock_answer(req.question, contexts, sources)

    return {
        "question": req.question,
        "answer": answer,
        "retrieved_context": contexts,
        "sources": sources
    }