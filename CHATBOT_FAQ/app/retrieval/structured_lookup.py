import json
from pathlib import Path
from typing import Any


STRUCTURED_MAPPING_PATH = Path("data/structured/quy_doi/english_certificate_mapping.json")


def load_english_certificate_mapping() -> list[dict[str, Any]]:
    if not STRUCTURED_MAPPING_PATH.exists():
        return []

    return json.loads(STRUCTURED_MAPPING_PATH.read_text(encoding="utf-8"))


def normalize_text(text: str) -> str:
    return text.strip().lower()


def lookup_certificate_mapping(question: str) -> dict[str, Any] | None:
    q = normalize_text(question)
    data = load_english_certificate_mapping()

    if not data:
        return None

    if "ielts" in q:
        rows = [item for item in data if normalize_text(item.get("certificate", "")) == "ielts"]

        if not rows:
            return None

        return {
            "type": "structured_certificate_mapping",
            "certificate": "IELTS",
            "rows": rows,
        }

    return None


def format_mapping_values(mappings: dict[str, Any]) -> str:
    parts = []

    for key, value in mappings.items():
        if value is None:
            continue

        label = key.replace("_", " ")
        parts.append(f"{label}: {value}")

    return "; ".join(parts)


def format_structured_certificate_answer(result: dict[str, Any]) -> str:
    if not result or "rows" not in result:
        return "Không tìm thấy thông tin phù hợp trong dữ liệu cấu trúc."

    certificate = result.get("certificate", "Không rõ chứng chỉ")
    rows = result["rows"]

    nhom_khong_chuyen = [r for r in rows if r.get("group") == "nganh_khong_chuyen"]
    nhom_ngon_ngu_anh = [r for r in rows if r.get("group") == "ngon_ngu_anh"]

    lines = [f"Quy đổi {certificate}:"]

    if nhom_khong_chuyen:
        lines.append("")
        lines.append("1. Nhóm ngành không chuyên")
        for row in nhom_khong_chuyen:
            level = row.get("level", "Không rõ mức")
            mapping_text = format_mapping_values(row.get("mappings", {}))
            lines.append(f"- IELTS {level}: {mapping_text}")

    if nhom_ngon_ngu_anh:
        lines.append("")
        lines.append("2. Nhóm ngành ngôn ngữ Anh")
        for row in nhom_ngon_ngu_anh:
            level = row.get("level", "Không rõ mức")
            mapping_text = format_mapping_values(row.get("mappings", {}))
            lines.append(f"- IELTS {level}: {mapping_text}")

    source_file = rows[0].get("source_file", "Không rõ file")
    source_page = rows[0].get("source_page", "Không rõ trang")

    lines.append("")
    lines.append(f"Nguồn: {source_file} (trang {source_page})")

    return "\n".join(lines)