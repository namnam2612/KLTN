from langchain_text_splitters import RecursiveCharacterTextSplitter

def build_text_splitter():
    # Áp dụng Rule-based Semantic Chunking với Regex-based Anchoring
    return RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        separators=[
            # Các ranh giới ngữ nghĩa ưu tiên cắt trước
            r"\n(?=Chương [IVXLD]+\.)", # Cắt trước tiêu đề Chương
            r"\n(?=Điều \d+\.)",        # Cắt trước Điều khoản
            r"\n(?=Bước \d+:)",         # Cắt trước các Bước trong quy trình phụ lục
            # Các ranh giới fallback dự phòng
            r"\n\n",
            r"\n",
            r"\.",
            " ",
            ""
        ],
        is_separator_regex=True
    )