import json
from pathlib import Path

from app.core.config import settings
from app.ingest.cleaner import clean_text


def main():
    extracted_root = Path(settings.EXTRACTED_DIR)
    cleaned_root = Path(settings.CLEANED_DIR)
    cleaned_root.mkdir(parents=True, exist_ok=True)

    for json_file in extracted_root.rglob("*.json"):
        data = json.loads(json_file.read_text(encoding="utf-8"))

        for page in data["pages"]:
            page["text"] = clean_text(page.get("text", ""))

        rel_path = json_file.relative_to(extracted_root)
        out_path = cleaned_root / rel_path
        out_path.parent.mkdir(parents=True, exist_ok=True)

        out_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        print(f"[OK] {out_path}")


if __name__ == "__main__":
    main()