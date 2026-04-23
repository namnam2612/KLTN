import csv
import json
from pathlib import Path

import requests


TEST_QUESTIONS_FILE = Path("tests/test_data/test_questions.txt")
OUTPUT_CSV_FILE = Path("tests/test_results_graded.csv")
API_URL = "http://127.0.0.1:8010/ask"


def parse_test_questions(file_path: Path):
    if not file_path.exists():
        raise FileNotFoundError(f"Không tìm thấy file: {file_path}")

    current_category = None
    questions = []

    content = file_path.read_text(encoding="utf-8")
    lines = [line.strip() for line in content.splitlines() if line.strip()]

    for line in lines:
        if line.startswith("[") and line.endswith("]"):
            current_category = line[1:-1]
            continue

        if current_category is None:
            continue

        questions.append({
            "category": current_category,
            "question": line
        })

    return questions


def call_ask_api(question: str):
    payload = {"question": question}

    response = requests.post(API_URL, json=payload, timeout=120)

    if not response.ok:
        return {
            "answer": f"API error {response.status_code}: {response.text}",
            "sources": []
        }

    data = response.json()

    return {
        "answer": data.get("answer", ""),
        "sources": data.get("sources", [])
    }


def flatten_sources(sources):
    if not sources:
        return ""

    simple_sources = []
    for src in sources:
        file_name = src.get("file", "")
        page = src.get("page", "")
        simple_sources.append(f"{file_name} (trang {page})")

    return " | ".join(simple_sources)


def main():
    questions = parse_test_questions(TEST_QUESTIONS_FILE)

    print(f"Tổng số câu hỏi sẽ test: {len(questions)}")
    print("-" * 80)

    OUTPUT_CSV_FILE.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_CSV_FILE.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "category",
                "question",
                "answer",
                "sources",
                "correct",
                "notes",
            ]
        )
        writer.writeheader()

        for idx, item in enumerate(questions, start=1):
            category = item["category"]
            question = item["question"]

            print(f"[{idx}/{len(questions)}] Đang test: {question}")

            try:
                result = call_ask_api(question)
                answer = result["answer"]
                sources = flatten_sources(result["sources"])
            except Exception as e:
                answer = f"Lỗi khi gọi API: {str(e)}"
                sources = ""

            writer.writerow({
                "category": category,
                "question": question,
                "answer": answer,
                "sources": sources,
                "correct": "",
                "notes": "",
            })

    print("-" * 80)
    print(f"Đã lưu kết quả test vào: {OUTPUT_CSV_FILE}")


if __name__ == "__main__":
    main()