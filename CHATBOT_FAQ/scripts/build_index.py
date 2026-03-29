from app.retrieval.vector_store import build_vector_store


def main():
    vectordb = build_vector_store()
    print(vectordb._collection.count())


if __name__ == "__main__":
    main()