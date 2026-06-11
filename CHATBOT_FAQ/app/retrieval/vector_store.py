import json
import shutil
from pathlib import Path

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_community.embeddings import HuggingFaceEmbeddings

from app.core.config import settings


def get_embedding_model():
    return HuggingFaceEmbeddings(
        model_name=settings.EMBEDDING_MODEL
    )


def load_documents_from_jsonl(jsonl_path: Path) -> list[Document]:
    docs = []

    with jsonl_path.open("r", encoding="utf-8") as f:
        for line in f:
            item = json.loads(line)
            docs.append(
                Document(
                    page_content=item["text"],
                    metadata=item["metadata"] | {"id": item["id"]}
                )
            )

    return docs


def build_vector_store():
    chunks_file = Path(settings.CHUNKS_DIR) / "chunks.jsonl"
    persist_dir = Path(settings.INDEX_DIR)

    if not chunks_file.exists():
        raise FileNotFoundError(
            f"{chunks_file} does not exist. Run `python -m scripts.build_chunks` first."
        )

    docs = load_documents_from_jsonl(chunks_file)

    if not docs:
        raise ValueError(f"{chunks_file} does not contain any chunks.")

    embeddings = get_embedding_model()

    if persist_dir.exists():
        shutil.rmtree(persist_dir)
    persist_dir.parent.mkdir(parents=True, exist_ok=True)

    vectordb = Chroma.from_documents(
        documents=docs,
        embedding=embeddings,
        persist_directory=str(persist_dir)
    )
    return vectordb


def load_vector_store():
    embeddings = get_embedding_model()
    return Chroma(
        persist_directory=settings.INDEX_DIR,
        embedding_function=embeddings
    )
