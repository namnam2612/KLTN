from app.retrieval.retriever import retrieve_context


def main():
    query = input("Nhập câu hỏi: ").strip()
    results = retrieve_context(query, k=5)

    for i, doc in enumerate(results, 1):
        print("=" * 80)
        print(f"Kết quả {i}")
        print("META:", doc.metadata)
        print("TEXT:", doc.page_content[:700])


if __name__ == "__main__":
    main()