import csv
from collections import defaultdict

FILE_PATH = "tests/test_results_graded.csv"


def main():
    total = 0
    score_sum = 0

    category_scores = defaultdict(list)

    with open(FILE_PATH, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)

        for row in reader:
            correct = row.get("correct", "").strip()

            if correct == "":
                continue

            try:
                score = float(correct)
            except:
                continue

            category = row["category"]

            total += 1
            score_sum += score

            category_scores[category].append(score)

    print("=" * 60)
    print("📊 KẾT QUẢ ĐÁNH GIÁ HỆ THỐNG")
    print("=" * 60)

    if total == 0:
        print("Không có dữ liệu hợp lệ")
        return

    overall_accuracy = score_sum / total * 100
    print(f"\n👉 Accuracy tổng: {overall_accuracy:.2f}% ({total} câu)\n")

    print("👉 Accuracy theo từng category:\n")

    for category, scores in category_scores.items():
        acc = sum(scores) / len(scores) * 100
        print(f"{category:30} → {acc:.2f}% ({len(scores)} câu)")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()