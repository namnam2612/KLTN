import re
import unicodedata

def clean_text(text: str) -> str:
    if not text:
        return ""

    # 1. Chuẩn hóa tiếng Việt (Unicode NFC)
    text = unicodedata.normalize("NFC", text)

    # 2. Khử nhiễu định kỳ (Denoising Strategy) - Xóa Header/Footer
    text = re.sub(r"Số:\s*\S+/QĐ-ĐHTL.*?\n", "", text, flags=re.IGNORECASE)
    text = re.sub(r"Quy chế đào tạo.*?\n", "", text, flags=re.IGNORECASE)
    text = re.sub(r"Trang\s*\d+.*?\n", "", text, flags=re.IGNORECASE)

    # 3. Xử lý khoảng trắng thực thể
    text = text.replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)

    # 4. Tái cấu trúc dòng (Sentence Recomposition)
    # Nối các dòng bị ngắt vật lý (kết thúc bằng chữ cái thường hoặc dấu phẩy)
    text = re.sub(r"([a-z,])\n([a-z])", r"\1 \2", text)

    # 5. Giữ lại ngắt đoạn logic
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r" +\n", "\n", text)
    text = re.sub(r"\n +", "\n", text)

    return text.strip()