from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from langchain_core.documents import Document

from app.retrieval.vector_store import load_vector_store
from app.core.config import settings


# =========================================================
# 1. Normalize tiếng Việt
# User vẫn hỏi tiếng Việt có dấu.
# Normalize chỉ dùng nội bộ để match cả có dấu / không dấu / OCR lỗi.
# =========================================================

def normalize(text: Optional[str]) -> str:
    if not text:
        return ""

    text = str(text).lower().strip()
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = text.replace("đ", "d")
    text = re.sub(r"[_\-–—/\\|]+", " ", text)
    text = re.sub(r"[^\w\s.]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def get_meta(doc: Document, key: str) -> str:
    return normalize(doc.metadata.get(key))


def doc_full_text(doc: Document) -> str:
    filename = doc.metadata.get("filename") or ""
    source_file = doc.metadata.get("source_file") or ""
    section_title = doc.metadata.get("section_title") or ""
    category = doc.metadata.get("category") or ""
    sub_category = doc.metadata.get("sub_category") or ""
    document_type = doc.metadata.get("document_type") or ""

    return normalize(
        f"{filename}\n"
        f"{source_file}\n"
        f"{section_title}\n"
        f"{category}\n"
        f"{sub_category}\n"
        f"{document_type}\n"
        f"{doc.page_content or ''}"
    )


# =========================================================
# 2. Optional fuzzy matching
# Có rapidfuzz trong requirements rồi. Nếu chưa có thì code vẫn chạy.
# =========================================================

try:
    from rapidfuzz import fuzz
except Exception:
    fuzz = None


def fuzzy_contains(term: str, text: str, threshold: int = 88) -> bool:
    term_n = normalize(term)
    text_n = normalize(text)

    if not term_n or not text_n:
        return False

    if term_n in text_n:
        return True

    if not fuzz:
        return False

    if len(term_n) < 6:
        return False

    return fuzz.partial_ratio(term_n, text_n) >= threshold


# =========================================================
# 3. Intent rule
# =========================================================

@dataclass
class IntentRule:
    name: str
    priority: int
    terms: List[str]
    meta_filter: Optional[Dict[str, str]] = None
    expansions: List[str] = field(default_factory=list)
    positives: List[str] = field(default_factory=list)
    negatives: List[str] = field(default_factory=list)
    hard_keep: List[str] = field(default_factory=list)


def R(
    name: str,
    priority: int,
    terms: List[str],
    meta_filter: Optional[Dict[str, str]] = None,
    expansions: Optional[List[str]] = None,
    positives: Optional[List[str]] = None,
    negatives: Optional[List[str]] = None,
    hard_keep: Optional[List[str]] = None,
) -> IntentRule:
    return IntentRule(
        name=name,
        priority=priority,
        terms=terms,
        meta_filter=meta_filter,
        expansions=expansions or [],
        positives=positives or [],
        negatives=negatives or [],
        hard_keep=hard_keep or [],
    )


# =========================================================
# 4. Phụ lục aliases 1–19
# Đây là lớp mở rộng mạnh nhất.
# Bất cứ câu hỏi nào chạm vào tên phụ lục sẽ được kéo về đúng file.
# =========================================================

APPENDIX_RULES: List[IntentRule] = [
    R(
        name="pl01_quy_trinh_dang_ky_hoc",
        priority=130,
        meta_filter={"sub_category": "quy_trinh_hoc_vu"},
        terms=[
            "phụ lục 1", "phụ lục số 1", "pl01",
            "quy trình đăng ký học", "đăng ký học", "đăng kí học",
            "đăng ký học phần", "đăng kí học phần", "đăng ký môn",
            "đăng ký tín chỉ", "cổng đăng ký học", "rút học phần",
            "hủy học phần", "bỏ môn", "rút môn",
        ],
        expansions=[
            "Phụ lục 1 quy trình đăng ký học đăng ký học phần rút học phần",
            "quy trình đăng ký học sinh viên cố vấn học tập phòng đào tạo",
        ],
        positives=[
            "Phụ lục 1", "quy trình đăng ký học", "đăng ký học phần",
            "rút học phần", "cố vấn học tập", "Phòng Đào tạo",
        ],
        negatives=[
            "thực tập tốt nghiệp", "chương trình thứ hai",
        ],
        hard_keep=[
            "Phụ lục 1", "quy trình đăng ký học", "đăng ký học phần",
        ],
    ),
    R(
        name="pl02_dang_ky_thuc_tap_tot_nghiep",
        priority=130,
        meta_filter={"sub_category": "thuc_tap_kltn"},
        terms=[
            "phụ lục 2", "phụ lục số 2", "pl02",
            "thủ tục đăng ký thực tập tốt nghiệp", "đăng ký thực tập",
            "đăng kí thực tập", "thực tập tốt nghiệp", "đi thực tập",
            "điều kiện thực tập", "hồ sơ thực tập",
        ],
        expansions=[
            "Phụ lục 2 thủ tục đăng ký thực tập tốt nghiệp điều kiện hồ sơ",
            "đăng ký thực tập tốt nghiệp sinh viên điều kiện thực tập",
        ],
        positives=[
            "Phụ lục 2", "thủ tục đăng ký thực tập tốt nghiệp",
            "đăng ký thực tập", "thực tập tốt nghiệp", "hồ sơ", "điều kiện",
        ],
        negatives=[
            "xét tốt nghiệp", "khóa luận tốt nghiệp",
        ],
        hard_keep=[
            "Phụ lục 2", "đăng ký thực tập", "thực tập tốt nghiệp",
        ],
    ),
    R(
        name="pl03_mau_bao_cao_thuc_tap",
        priority=125,
        meta_filter={"sub_category": "thuc_tap_kltn"},
        terms=[
            "phụ lục 3", "phụ lục số 3", "pl03",
            "mẫu báo cáo thực tập", "báo cáo thực tập tốt nghiệp",
            "viết báo cáo thực tập", "nộp báo cáo thực tập",
            "bố cục báo cáo thực tập", "mẫu bìa thực tập",
        ],
        expansions=[
            "Phụ lục 3 mẫu báo cáo thực tập tốt nghiệp bố cục nội dung",
        ],
        positives=[
            "Phụ lục 3", "mẫu báo cáo thực tập tốt nghiệp",
            "báo cáo thực tập", "mẫu", "nội dung", "bố cục",
        ],
        hard_keep=[
            "Phụ lục 3", "báo cáo thực tập",
        ],
    ),
    R(
        name="pl04_quy_doi_giai_thuong_am_nhac",
        priority=120,
        meta_filter={"sub_category": "quy_doi_chung_chi_diem"},
        terms=[
            "phụ lục 4", "phụ lục số 4", "pl04",
            "giải thưởng âm nhạc", "sản phẩm âm nhạc",
            "quy đổi điểm âm nhạc", "điểm giải thưởng âm nhạc",
            "cuộc thi âm nhạc", "thành tích âm nhạc",
        ],
        expansions=[
            "Phụ lục 4 bảng quy đổi điểm từ các giải thưởng âm nhạc và sản phẩm âm nhạc",
        ],
        positives=[
            "Phụ lục 4", "giải thưởng âm nhạc", "sản phẩm âm nhạc",
            "quy đổi điểm",
        ],
        hard_keep=[
            "Phụ lục 4", "giải thưởng âm nhạc", "sản phẩm âm nhạc",
        ],
    ),
    R(
        name="pl05_doi_nguoi_huong_dan_kltn",
        priority=135,
        meta_filter={"sub_category": "thuc_tap_kltn"},
        terms=[
            "phụ lục 5", "phụ lục số 5", "pl05",
            "thay đổi người hướng dẫn", "đổi người hướng dẫn",
            "đổi giảng viên hướng dẫn", "đổi gvhd",
            "người hướng dẫn khóa luận", "giảng viên hướng dẫn khóa luận",
        ],
        expansions=[
            "Phụ lục 5 thủ tục thay đổi người hướng dẫn khóa luận tốt nghiệp",
            "đổi giảng viên hướng dẫn KLTN thủ tục hồ sơ",
        ],
        positives=[
            "Phụ lục 5", "thay đổi người hướng dẫn",
            "người hướng dẫn", "khóa luận tốt nghiệp", "KLTN",
        ],
        hard_keep=[
            "Phụ lục 5", "thay đổi người hướng dẫn", "người hướng dẫn",
        ],
    ),
    R(
        name="pl06_phieu_theo_doi_tien_do_kltn",
        priority=120,
        meta_filter={"sub_category": "thuc_tap_kltn"},
        terms=[
            "phụ lục 6", "phụ lục số 6", "pl06",
            "phiếu theo dõi tiến độ", "tiến độ khóa luận",
            "theo dõi tiến độ kltn", "tiến độ hoàn thiện khóa luận",
            "xác nhận tiến độ khóa luận",
        ],
        expansions=[
            "Phụ lục 6 phiếu theo dõi tiến độ hoàn thiện thực hiện KLTN",
        ],
        positives=[
            "Phụ lục 6", "phiếu theo dõi tiến độ", "KLTN",
            "tiến độ hoàn thiện",
        ],
        hard_keep=[
            "Phụ lục 6", "phiếu theo dõi tiến độ", "KLTN",
        ],
    ),
    R(
        name="pl07_the_thuc_trinh_bay_kltn",
        priority=135,
        meta_filter={"sub_category": "thuc_tap_kltn"},
        terms=[
            "phụ lục 7", "phụ lục số 7", "pl07",
            "thể thức trình bày khóa luận", "trình bày khóa luận",
            "format khóa luận", "font chữ khóa luận", "căn lề khóa luận",
            "giãn dòng khóa luận", "số trang khóa luận", "bố cục khóa luận",
            "mục lục khóa luận", "tài liệu tham khảo khóa luận",
        ],
        expansions=[
            "Phụ lục 7 quy định thể thức trình bày khóa luận tốt nghiệp font căn lề bố cục",
            "thể thức trình bày KLTN font chữ căn lề giãn dòng tài liệu tham khảo",
        ],
        positives=[
            "Phụ lục 7", "thể thức trình bày", "khóa luận tốt nghiệp",
            "font", "căn lề", "giãn dòng", "bố cục", "tài liệu tham khảo",
        ],
        hard_keep=[
            "Phụ lục 7", "thể thức trình bày", "khóa luận tốt nghiệp",
        ],
    ),
    R(
        name="pl08_phieu_cham_tieu_luan",
        priority=115,
        meta_filter={"sub_category": "bieu_mau"},
        terms=[
            "phụ lục 8", "phụ lục số 8", "pl08",
            "phiếu chấm tiểu luận", "chấm thi môn tiểu luận",
            "chấm tiểu luận", "rubric tiểu luận", "điểm tiểu luận",
        ],
        expansions=[
            "Phụ lục 8 phiếu chấm thi môn tiểu luận",
        ],
        positives=[
            "Phụ lục 8", "phiếu chấm thi môn tiểu luận", "tiểu luận",
        ],
        hard_keep=[
            "Phụ lục 8", "tiểu luận",
        ],
    ),
    R(
        name="pl09_phieu_danh_gia_thuc_tap",
        priority=120,
        meta_filter={"sub_category": "thuc_tap_kltn"},
        terms=[
            "phụ lục 9", "phụ lục số 9", "pl09",
            "phiếu đánh giá thực tập", "đánh giá thực tập tốt nghiệp",
            "điểm thực tập", "cơ sở thực tập đánh giá",
            "đơn vị thực tập đánh giá", "nhận xét thực tập",
        ],
        expansions=[
            "Phụ lục 9 phiếu đánh giá thực tập tốt nghiệp",
        ],
        positives=[
            "Phụ lục 9", "phiếu đánh giá thực tập tốt nghiệp",
            "đánh giá thực tập", "thực tập tốt nghiệp",
        ],
        hard_keep=[
            "Phụ lục 9", "đánh giá thực tập",
        ],
    ),
    R(
        name="pl10_quy_doi_chung_chi_ngoai_ngu",
        priority=140,
        meta_filter={"sub_category": "quy_doi_chung_chi_diem"},
        terms=[
            "phụ lục 10", "phụ lục số 10", "pl10",
            "quy đổi chứng chỉ ngoại ngữ quốc tế",
            "chứng chỉ ngoại ngữ quốc tế", "quy đổi ngoại ngữ",
            "ielts", "toeic", "toefl", "hsk", "hskk",
            "jlpt", "topik", "aptis", "cambridge", "vstep",
            "delf", "dalf", "dele", "miễn học phần tiếng anh",
        ],
        expansions=[
            "Phụ lục 10 bản quy đổi chứng chỉ ngoại ngữ quốc tế IELTS TOEIC TOEFL HSK HSKK JLPT TOPIK",
            "quy đổi chứng chỉ ngoại ngữ quốc tế miễn học phần tiếng Anh",
        ],
        positives=[
            "Phụ lục 10", "Bản quy đổi chứng chỉ ngoại ngữ quốc tế",
            "IELTS", "TOEIC", "TOEFL", "HSK", "HSKK", "JLPT", "TOPIK",
            "chứng chỉ ngoại ngữ quốc tế",
        ],
        negatives=[
            "Phụ lục 11", "xếp lớp tiếng Anh", "A1", "A2", "B1",
        ],
        hard_keep=[
            "Phụ lục 10", "quy đổi chứng chỉ ngoại ngữ quốc tế",
            "IELTS", "TOEIC", "TOEFL", "HSK", "JLPT", "TOPIK",
        ],
    ),
    R(
        name="pl11_xep_lop_tieng_anh",
        priority=130,
        meta_filter={"sub_category": "quy_doi_chung_chi_diem"},
        terms=[
            "phụ lục 11", "phụ lục số 11", "pl11",
            "bản quy đổi điểm và xếp lớp tiếng anh",
            "xếp lớp tiếng anh", "xếp lớp anh văn", "đầu vào tiếng anh",
            "trình độ tiếng anh", "a1", "a2", "b1",
            "học tiếng anh mấy", "được xếp lớp nào",
        ],
        expansions=[
            "Phụ lục 11 bản quy đổi điểm và xếp lớp tiếng Anh A1 A2 B1",
            "xếp lớp tiếng Anh theo điểm đầu vào",
        ],
        positives=[
            "Phụ lục 11", "Bản quy đổi điểm và xếp lớp tiếng Anh",
            "xếp lớp tiếng Anh", "A1", "A2", "B1",
        ],
        negatives=[
            "Phụ lục 10", "quy đổi chứng chỉ ngoại ngữ quốc tế",
        ],
        hard_keep=[
            "Phụ lục 11", "xếp lớp tiếng Anh", "A1", "A2", "B1",
        ],
    ),
    R(
        name="pl12_sua_diem_qua_trinh_diem_thi",
        priority=130,
        meta_filter={"sub_category": "quy_trinh_hoc_vu"},
        terms=[
            "phụ lục 12", "phụ lục số 12", "pl12",
            "nhận xử lý và sửa điểm", "sửa điểm quá trình",
            "sửa điểm thi", "sai điểm", "nhầm điểm", "điểm bị sai",
            "điểm quá trình", "điểm thi", "điểm học phần",
            "khiếu nại điểm", "phúc khảo", "chưa có điểm", "thiếu điểm",
        ],
        expansions=[
            "Phụ lục 12 quy trình nhận xử lý và sửa điểm quá trình điểm thi",
            "sửa điểm quá trình điểm thi điểm học phần sinh viên",
        ],
        positives=[
            "Phụ lục 12", "sửa điểm", "điểm quá trình",
            "điểm thi", "nhận xử lý và sửa điểm",
        ],
        hard_keep=[
            "Phụ lục 12", "sửa điểm", "điểm quá trình", "điểm thi",
        ],
    ),
    R(
        name="pl13_danh_gia_khoa_luan_tot_nghiep",
        priority=130,
        meta_filter={"sub_category": "thuc_tap_kltn"},
        terms=[
            "phụ lục 13", "phụ lục số 13", "pl13",
            "quy trình đánh giá khóa luận tốt nghiệp",
            "đánh giá khóa luận", "bảo vệ khóa luận",
            "hội đồng khóa luận", "chấm khóa luận", "điểm khóa luận",
            "kltn đạt", "kltn không đạt",
        ],
        expansions=[
            "Phụ lục 13 quy trình đánh giá khóa luận tốt nghiệp hội đồng chấm điểm bảo vệ",
            "đánh giá KLTN quy trình bảo vệ khóa luận tốt nghiệp",
        ],
        positives=[
            "Phụ lục 13", "quy trình đánh giá khóa luận tốt nghiệp",
            "đánh giá khóa luận", "hội đồng", "bảo vệ", "KLTN",
        ],
        negatives=[
            "thực tập tốt nghiệp",
        ],
        hard_keep=[
            "Phụ lục 13", "đánh giá khóa luận", "KLTN",
        ],
    ),
    R(
        name="pl14_canh_bao_hoc_tap_buoc_thoi_hoc",
        priority=135,
        meta_filter={"sub_category": "quy_trinh_hoc_vu"},
        terms=[
            "phụ lục 14", "phụ lục số 14", "pl14",
            "cảnh báo học tập", "buộc thôi học", "xét cảnh báo",
            "bị cảnh báo", "bị buộc thôi học", "học lực yếu",
            "kết quả học tập yếu", "gpa thấp", "cpa thấp",
        ],
        expansions=[
            "Phụ lục 14 quy trình xét cảnh báo học tập buộc thôi học",
            "cảnh báo học tập buộc thôi học kết quả học tập sinh viên",
        ],
        positives=[
            "Phụ lục 14", "cảnh báo học tập", "buộc thôi học",
            "xét cảnh báo", "kết quả học tập",
        ],
        negatives=[
            "Phụ lục 18", "đơn xin thôi học", "thôi học/chuyển trường",
        ],
        hard_keep=[
            "Phụ lục 14", "cảnh báo học tập", "buộc thôi học",
        ],
    ),
    R(
        name="pl15_xet_tot_nghiep_cap_van_bang",
        priority=135,
        meta_filter={"sub_category": "quy_trinh_hoc_vu"},
        terms=[
            "phụ lục 15", "phụ lục số 15", "pl15",
            "xét tốt nghiệp", "cấp phát văn bằng", "cấp bằng",
            "nhận bằng", "lấy bằng", "văn bằng", "bằng tốt nghiệp",
            "đăng ký xét tốt nghiệp", "hồ sơ tốt nghiệp",
            "đủ điều kiện tốt nghiệp", "hội đồng xét tốt nghiệp",
        ],
        expansions=[
            "Phụ lục 15 quy trình xét tốt nghiệp và cấp phát văn bằng hồ sơ điều kiện",
            "xét tốt nghiệp cấp phát văn bằng bằng tốt nghiệp sinh viên",
        ],
        positives=[
            "Phụ lục 15", "xét tốt nghiệp", "cấp phát văn bằng",
            "văn bằng", "bằng tốt nghiệp", "hồ sơ", "điều kiện tốt nghiệp",
        ],
        negatives=[
            "thực tập tốt nghiệp", "khóa luận tốt nghiệp",
        ],
        hard_keep=[
            "Phụ lục 15", "xét tốt nghiệp", "cấp phát văn bằng",
        ],
    ),
    R(
        name="pl16_nghi_hoc_tam_thoi_quay_lai_hoc",
        priority=145,
        meta_filter={"sub_category": "quy_trinh_hoc_vu"},
        terms=[
            "phụ lục 16", "phụ lục số 16", "pl16",
            "nghỉ học tạm thời", "xin nghỉ học", "bảo lưu",
            "bảo lưu kết quả", "tạm dừng học", "dừng học một kỳ",
            "nghỉ một học kỳ", "nghỉ học rồi quay lại",
            "quay trở lại học", "trở lại học", "học lại sau bảo lưu",
        ],
        expansions=[
            "Phụ lục 16 thủ tục xét nghỉ học tạm thời và quay trở lại học hồ sơ đơn xét duyệt",
            "nghỉ học tạm thời bảo lưu quay trở lại học hồ sơ lệ phí phòng đào tạo",
        ],
        positives=[
            "Phụ lục 16", "nghỉ học tạm thời", "quay trở lại học",
            "hồ sơ", "đơn", "tiếp nhận hồ sơ", "xét duyệt",
            "phê duyệt", "thời gian tiếp nhận", "lệ phí",
        ],
        negatives=[
            "Phụ lục 18", "chuyển cơ sở đào tạo", "chuyển trường",
            "thôi học/chuyển trường", "đơn xin thôi học",
        ],
        hard_keep=[
            "Phụ lục 16", "nghỉ học tạm thời", "quay trở lại học",
        ],
    ),
    R(
        name="pl17_chuyen_chuong_trinh_chuyen_nganh",
        priority=135,
        meta_filter={"sub_category": "quy_trinh_hoc_vu"},
        terms=[
            "phụ lục 17", "phụ lục số 17", "pl17",
            "chuyển chương trình", "chuyển ngành", "đổi ngành",
            "đổi chương trình", "chuyển sang ngành khác",
            "hồ sơ chuyển ngành", "điều kiện chuyển ngành",
        ],
        expansions=[
            "Phụ lục 17 quy trình chuyển chương trình chuyển ngành hồ sơ điều kiện",
            "thủ tục chuyển ngành chuyển chương trình đào tạo sinh viên",
        ],
        positives=[
            "Phụ lục 17", "chuyển chương trình", "chuyển ngành",
            "hồ sơ", "đơn", "điều kiện",
        ],
        negatives=[
            "Phụ lục 18", "chuyển cơ sở đào tạo", "chuyển trường",
            "chương trình thứ hai",
        ],
        hard_keep=[
            "Phụ lục 17", "chuyển chương trình", "chuyển ngành",
        ],
    ),
    R(
        name="pl18_chuyen_co_so_dao_tao_thoi_hoc",
        priority=135,
        meta_filter={"sub_category": "quy_trinh_hoc_vu"},
        terms=[
            "phụ lục 18", "phụ lục số 18", "pl18",
            "chuyển cơ sở đào tạo", "chuyển trường", "chuyển đến",
            "chuyển đi", "xin chuyển trường", "rút hồ sơ",
            "xin thôi học", "đơn xin thôi học", "thôi học",
            "nghỉ hẳn", "rút khỏi trường",
        ],
        expansions=[
            "Phụ lục 18 thủ tục chuyển cơ sở đào tạo chuyển trường đi chuyển đến hồ sơ",
            "đơn xin thôi học rút hồ sơ chuyển trường đi",
        ],
        positives=[
            "Phụ lục 18", "chuyển cơ sở đào tạo", "chuyển trường",
            "chuyển đến", "chuyển đi", "rút hồ sơ",
            "đơn xin thôi học/chuyển trường",
        ],
        negatives=[
            "Phụ lục 16", "nghỉ học tạm thời",
            "Phụ lục 17", "chuyển chương trình", "chuyển ngành",
        ],
        hard_keep=[
            "Phụ lục 18", "chuyển cơ sở đào tạo", "chuyển trường",
            "đơn xin thôi học", "rút hồ sơ",
        ],
    ),
    R(
        name="pl19_hoc_chuong_trinh_thu_hai",
        priority=135,
        meta_filter={"sub_category": "quy_trinh_hoc_vu"},
        terms=[
            "phụ lục 19", "phụ lục số 19", "pl19",
            "chương trình thứ hai", "học chương trình thứ hai",
            "học ngành thứ hai", "học bằng hai", "học hai ngành",
            "học cùng lúc hai chương trình", "song ngành", "ngành 2",
        ],
        expansions=[
            "Phụ lục 19 thủ tục đăng ký học chương trình thứ hai hồ sơ điều kiện",
            "học chương trình thứ hai học ngành thứ hai sinh viên",
        ],
        positives=[
            "Phụ lục 19", "chương trình thứ hai",
            "đăng ký học chương trình thứ hai", "hồ sơ", "đơn",
        ],
        negatives=[
            "đăng ký học phần", "chuyển chương trình",
        ],
        hard_keep=[
            "Phụ lục 19", "chương trình thứ hai",
        ],
    ),
]


# =========================================================
# 5. Rule theo dạng câu hỏi
# Lớp này giúp retriever hiểu user hỏi "hồ sơ", "điều kiện",
# "quy trình", "thời hạn", "lệ phí", "điểm", "bao nhiêu".
# =========================================================

QUESTION_TYPE_RULES: List[IntentRule] = [
    R(
        name="hoi_ho_so",
        priority=80,
        terms=[
            "hồ sơ", "giấy tờ", "cần nộp gì", "nộp những gì",
            "mẫu đơn", "đơn xin", "bản gốc", "bản sao",
            "xác nhận", "minh chứng", "file gì", "biểu mẫu",
        ],
        expansions=[
            "hồ sơ gồm đơn mẫu giấy tờ bản gốc bản sao xác nhận",
        ],
        positives=[
            "hồ sơ gồm", "hồ sơ", "đơn", "mẫu", "bản gốc",
            "bản sao", "xác nhận", "giấy",
        ],
        hard_keep=[
            "hồ sơ", "đơn", "mẫu",
        ],
    ),
    R(
        name="hoi_dieu_kien",
        priority=80,
        terms=[
            "điều kiện", "đủ điều kiện", "không đủ điều kiện",
            "yêu cầu", "đối tượng", "ai được", "ai không được",
            "cần đạt", "phải đạt", "được phép",
        ],
        expansions=[
            "điều kiện đối tượng yêu cầu được phép không đủ điều kiện",
        ],
        positives=[
            "điều kiện", "đối tượng", "yêu cầu", "đủ điều kiện",
            "không đủ điều kiện",
        ],
        hard_keep=[
            "điều kiện", "đối tượng", "yêu cầu",
        ],
    ),
    R(
        name="hoi_quy_trinh_thu_tuc",
        priority=78,
        terms=[
            "quy trình", "thủ tục", "làm thế nào", "làm sao",
            "phải làm gì", "các bước", "bước nào", "xử lý thế nào",
            "quy định xử lý", "trình tự",
        ],
        expansions=[
            "quy trình thủ tục các bước tiếp nhận xét duyệt phê duyệt xử lý",
        ],
        positives=[
            "quy trình", "thủ tục", "bước", "tiếp nhận",
            "xét duyệt", "phê duyệt", "xử lý",
        ],
        hard_keep=[
            "bước", "quy trình", "thủ tục",
        ],
    ),
    R(
        name="hoi_thoi_gian_thoi_han",
        priority=78,
        terms=[
            "khi nào", "bao giờ", "thời gian", "thời hạn",
            "hạn nộp", "deadline", "trước ngày", "sau ngày",
            "trong bao lâu", "mấy ngày", "mấy tuần",
            "lịch", "ngày bắt đầu", "ngày kết thúc",
        ],
        expansions=[
            "thời gian thời hạn hạn nộp trước ngày sau ngày ngày bắt đầu ngày kết thúc",
        ],
        positives=[
            "thời gian", "thời hạn", "hạn", "trước ngày",
            "sau ngày", "ngày", "tuần", "lịch",
        ],
        hard_keep=[
            "thời gian", "thời hạn", "ngày", "tuần",
        ],
    ),
    R(
        name="hoi_le_phi_hoc_phi",
        priority=78,
        terms=[
            "lệ phí", "phí", "học phí", "đóng tiền", "nộp tiền",
            "mức phí", "bao nhiêu tiền", "hoàn phí", "miễn giảm",
        ],
        expansions=[
            "lệ phí học phí mức phí đóng tiền nộp tiền miễn giảm hoàn phí",
        ],
        positives=[
            "lệ phí", "phí", "học phí", "đóng", "nộp",
            "miễn giảm", "hoàn",
        ],
        hard_keep=[
            "lệ phí", "học phí", "phí",
        ],
    ),
    R(
        name="hoi_diem_so",
        priority=78,
        terms=[
            "điểm", "bao nhiêu điểm", "điểm tối đa", "điểm tối thiểu",
            "điểm đạt", "điểm không đạt", "điểm f", "điểm chữ",
            "điểm số", "gpa", "cpa", "thang điểm", "xếp loại",
        ],
        expansions=[
            "điểm số điểm chữ thang điểm GPA CPA điểm đạt điểm không đạt",
        ],
        positives=[
            "điểm", "điểm chữ", "thang điểm", "GPA", "CPA",
            "xếp loại", "đạt", "không đạt",
        ],
        hard_keep=[
            "điểm", "thang điểm", "xếp loại",
        ],
    ),
    R(
        name="hoi_so_luong_tin_chi",
        priority=78,
        terms=[
            "bao nhiêu tín chỉ", "số tín chỉ", "tín chỉ",
            "tối thiểu", "tối đa", "bao nhiêu môn", "mấy môn",
            "khối lượng học tập",
        ],
        expansions=[
            "số tín chỉ tối thiểu tối đa khối lượng học tập học phần",
        ],
        positives=[
            "tín chỉ", "tối thiểu", "tối đa", "khối lượng học tập",
            "học phần",
        ],
        hard_keep=[
            "tín chỉ", "tối thiểu", "tối đa",
        ],
    ),
]


# =========================================================
# 6. Rule quy chế / sổ tay / CTĐT / kế hoạch
# =========================================================

ACADEMIC_RULES: List[IntentRule] = [
    R(
        name="quy_che_dao_tao_chung",
        priority=90,
        meta_filter={"category": "quy_che"},
        terms=[
            "quy chế đào tạo", "quy định đào tạo", "đào tạo đại học",
            "học chế tín chỉ", "quy định sinh viên", "điều khoản",
            "chương", "điều", "khoản",
        ],
        expansions=[
            "quy chế đào tạo trình độ đại học học chế tín chỉ điều khoản",
        ],
        positives=[
            "quy chế đào tạo", "đào tạo trình độ đại học",
            "điều", "khoản", "học chế tín chỉ",
        ],
        hard_keep=[
            "quy chế đào tạo", "điều", "khoản",
        ],
    ),
    R(
        name="dang_ky_tin_chi_khoi_luong_hoc_tap",
        priority=100,
        meta_filter={"category": "quy_che"},
        terms=[
            "tín chỉ tối thiểu", "tín chỉ tối đa",
            "đăng ký tối thiểu", "đăng ký tối đa",
            "một học kỳ đăng ký bao nhiêu tín chỉ",
            "khối lượng học tập", "học kỳ chính", "học kỳ phụ",
        ],
        expansions=[
            "quy chế đào tạo khối lượng học tập đăng ký tối thiểu tối đa tín chỉ học kỳ",
        ],
        positives=[
            "tín chỉ", "tối thiểu", "tối đa", "khối lượng học tập",
            "học kỳ chính", "học kỳ phụ",
        ],
        hard_keep=[
            "tín chỉ", "tối thiểu", "tối đa", "khối lượng học tập",
        ],
    ),
    R(
        name="dieu_kien_du_thi_ket_thuc_hoc_phan",
        priority=105,
        meta_filter={"category": "quy_che"},
        terms=[
            "điều kiện dự thi", "được dự thi", "không được dự thi",
            "thi kết thúc học phần", "thi cuối kỳ", "cấm thi",
            "vắng quá số buổi", "đủ điều kiện thi", "điều kiện thi",
        ],
        expansions=[
            "quy chế đào tạo điều kiện dự thi thi kết thúc học phần",
            "điều kiện được dự thi kết thúc học phần sinh viên",
        ],
        positives=[
            "điều kiện dự thi", "thi kết thúc học phần",
            "không được dự thi", "vắng",
        ],
        hard_keep=[
            "điều kiện dự thi", "thi kết thúc học phần",
        ],
    ),
    R(
        name="thi_lai_hoc_lai_cai_thien_diem",
        priority=105,
        meta_filter={"category": "quy_che"},
        terms=[
            "thi lại", "học lại", "cải thiện điểm", "học cải thiện",
            "điểm f", "rớt môn", "trượt môn", "qua môn",
            "điểm học lại", "điểm cải thiện", "thi lại tối đa",
        ],
        expansions=[
            "quy chế đào tạo thi lại học lại cải thiện điểm điểm F",
            "thi lại học lại cải thiện điểm kết quả học phần",
        ],
        positives=[
            "thi lại", "học lại", "cải thiện điểm", "điểm F",
            "kết quả học phần",
        ],
        hard_keep=[
            "thi lại", "học lại", "cải thiện điểm", "điểm F",
        ],
    ),
    R(
        name="diem_chu_gpa_cpa_xep_loai",
        priority=95,
        meta_filter={"category": "quy_che"},
        terms=[
            "điểm chữ", "điểm số", "thang điểm", "điểm 4",
            "gpa", "cpa", "điểm trung bình", "điểm trung bình tích lũy",
            "xếp loại học lực", "xếp loại tốt nghiệp", "loại giỏi",
            "loại khá", "xuất sắc", "trung bình",
        ],
        expansions=[
            "quy chế đào tạo thang điểm điểm chữ điểm trung bình tích lũy xếp loại",
            "GPA CPA điểm trung bình tích lũy xếp loại học lực tốt nghiệp",
        ],
        positives=[
            "điểm chữ", "thang điểm", "điểm trung bình",
            "tích lũy", "xếp loại", "GPA", "CPA",
        ],
        hard_keep=[
            "điểm chữ", "thang điểm", "điểm trung bình", "xếp loại",
        ],
    ),
    R(
        name="vang_thi_vang_hoc_chuyen_can",
        priority=95,
        meta_filter={"category": "quy_che"},
        terms=[
            "vắng thi", "không đi thi", "bỏ thi", "vắng học",
            "nghỉ quá số buổi", "điểm chuyên cần", "đủ số buổi",
            "đi học bao nhiêu buổi", "nghỉ học bị sao",
        ],
        expansions=[
            "quy chế đào tạo vắng thi vắng học điều kiện dự thi nghỉ quá số buổi",
        ],
        positives=[
            "vắng thi", "vắng học", "điều kiện dự thi",
            "nghỉ học", "số buổi", "chuyên cần",
        ],
        hard_keep=[
            "vắng thi", "vắng học", "điều kiện dự thi",
        ],
    ),
    R(
        name="tot_nghiep_khoa_luan_hoc_phan_thay_the",
        priority=95,
        meta_filter={"category": "quy_che"},
        terms=[
            "khóa luận tốt nghiệp", "học phần thay thế khóa luận",
            "điều kiện làm khóa luận", "đủ điều kiện làm khóa luận",
            "thực tập tốt nghiệp", "đồ án tốt nghiệp",
        ],
        expansions=[
            "quy chế đào tạo khóa luận tốt nghiệp học phần thay thế khóa luận điều kiện",
        ],
        positives=[
            "khóa luận tốt nghiệp", "học phần thay thế",
            "điều kiện", "thực tập tốt nghiệp",
        ],
        hard_keep=[
            "khóa luận tốt nghiệp", "học phần thay thế",
        ],
    ),
    R(
        name="hoc_phi_hoc_bong",
        priority=90,
        meta_filter={"category": "so_tay"},
        terms=[
            "học phí", "đóng học phí", "nộp học phí",
            "chậm học phí", "miễn giảm học phí", "hoàn học phí",
            "học bổng", "điều kiện học bổng", "xét học bổng",
            "mức học bổng", "học bổng khuyến khích", "học phí học lại",
        ],
        expansions=[
            "sổ tay sinh viên học phí học bổng miễn giảm hoàn học phí điều kiện học bổng",
        ],
        positives=[
            "học phí", "học bổng", "miễn giảm", "hoàn học phí",
            "sổ tay sinh viên",
        ],
        hard_keep=[
            "học phí", "học bổng",
        ],
    ),
    R(
        name="the_sinh_vien_thu_vien_tai_khoan",
        priority=85,
        meta_filter={"category": "so_tay"},
        terms=[
            "thẻ sinh viên", "mất thẻ", "làm lại thẻ",
            "thư viện", "mượn sách", "nợ sách",
            "phòng thông tin tư liệu", "email sinh viên",
            "tài khoản sinh viên", "cổng sinh viên",
        ],
        expansions=[
            "sổ tay sinh viên thẻ sinh viên thư viện mượn sách tài khoản email sinh viên",
        ],
        positives=[
            "thẻ sinh viên", "thư viện", "mượn sách",
            "tài khoản", "sổ tay sinh viên",
        ],
        hard_keep=[
            "thẻ sinh viên", "thư viện", "mượn sách",
        ],
    ),
    R(
        name="phong_ban_lien_he",
        priority=85,
        meta_filter={"category": "so_tay"},
        terms=[
            "liên hệ phòng nào", "phòng đào tạo",
            "phòng công tác sinh viên", "phòng công tác chính trị",
            "khoa bộ môn", "cố vấn học tập", "nộp hồ sơ ở đâu",
            "hỏi ai", "gửi cho ai", "email phòng đào tạo",
        ],
        expansions=[
            "sổ tay sinh viên phòng đào tạo phòng công tác sinh viên cố vấn học tập khoa bộ môn liên hệ",
        ],
        positives=[
            "Phòng Đào tạo", "Phòng Công tác", "cố vấn học tập",
            "khoa", "bộ môn", "liên hệ",
        ],
        hard_keep=[
            "Phòng Đào tạo", "Phòng Công tác", "cố vấn học tập",
        ],
    ),
]


CTDT_RULES: List[IntentRule] = [
    R(
        name="ctdt_chung_hoc_phan_tin_chi",
        priority=100,
        meta_filter={"category": "ctdt"},
        terms=[
            "chương trình đào tạo", "ctđt", "ctdt",
            "học phần", "mã học phần", "mã môn", "tín chỉ",
            "số tín chỉ", "môn bắt buộc", "môn tự chọn",
            "học phần bắt buộc", "học phần tự chọn", "khối kiến thức",
            "tiên quyết", "học trước", "song hành",
        ],
        expansions=[
            "chương trình đào tạo mã học phần số tín chỉ học phần bắt buộc tự chọn",
            "CTĐT ngành học khối kiến thức học phần tín chỉ",
        ],
        positives=[
            "chương trình đào tạo", "mã học phần", "tín chỉ",
            "học phần bắt buộc", "học phần tự chọn", "khối kiến thức",
        ],
        hard_keep=[
            "chương trình đào tạo", "mã học phần", "tín chỉ",
        ],
    ),
    R(
        name="ctdt_cong_nghe_thong_tin",
        priority=105,
        meta_filter={"category": "ctdt"},
        terms=[
            "công nghệ thông tin", "cntt", "ngành cntt", "it",
            "khoa công nghệ thông tin", "lập trình", "hệ thống thông tin",
            "khoa học máy tính", "trí tuệ nhân tạo", "mạng máy tính",
            "an toàn thông tin", "phần mềm", "dữ liệu",
        ],
        expansions=[
            "chương trình đào tạo ngành công nghệ thông tin CNTT mã học phần tín chỉ",
            "CTĐT công nghệ thông tin hệ thống thông tin khoa học máy tính trí tuệ nhân tạo",
        ],
        positives=[
            "công nghệ thông tin", "CNTT", "hệ thống thông tin",
            "khoa học máy tính", "trí tuệ nhân tạo", "tín chỉ", "mã học phần",
        ],
        hard_keep=[
            "công nghệ thông tin", "CNTT", "hệ thống thông tin",
        ],
    ),
    R(
        name="ctdt_kinh_te_marketing_quan_tri",
        priority=100,
        meta_filter={"category": "ctdt"},
        terms=[
            "marketing", "kinh tế quốc tế", "quản trị kinh doanh",
            "logistics", "thương mại điện tử", "quản trị thương hiệu",
            "digital marketing", "kinh doanh quốc tế", "thương mại",
            "chuỗi cung ứng",
        ],
        expansions=[
            "chương trình đào tạo marketing kinh tế quốc tế quản trị kinh doanh logistics thương mại điện tử tín chỉ mã học phần",
        ],
        positives=[
            "marketing", "kinh tế quốc tế", "quản trị kinh doanh",
            "quản trị thương hiệu", "logistics", "tín chỉ", "mã học phần",
        ],
        hard_keep=[
            "marketing", "kinh tế quốc tế", "quản trị kinh doanh",
        ],
    ),
    R(
        name="ctdt_ngon_ngu",
        priority=100,
        meta_filter={"category": "ctdt"},
        terms=[
            "ngôn ngữ anh", "ngôn ngữ trung", "ngôn ngữ nhật",
            "ngôn ngữ hàn", "tiếng anh", "tiếng trung",
            "tiếng nhật", "tiếng hàn", "biên phiên dịch",
            "ngôn ngữ học", "văn hóa", "phiên dịch",
        ],
        expansions=[
            "chương trình đào tạo ngành ngôn ngữ Anh Trung Nhật Hàn tín chỉ học phần",
        ],
        positives=[
            "ngôn ngữ Anh", "ngôn ngữ Trung", "ngôn ngữ Nhật",
            "ngôn ngữ Hàn", "biên phiên dịch", "tín chỉ", "học phần",
        ],
        hard_keep=[
            "ngôn ngữ Anh", "ngôn ngữ Trung", "ngôn ngữ Nhật", "ngôn ngữ Hàn",
        ],
    ),
    R(
        name="ctdt_tai_chinh_ke_toan_luat",
        priority=95,
        meta_filter={"category": "ctdt"},
        terms=[
            "tài chính", "ngân hàng", "kế toán", "luật",
            "luật kinh tế", "kiểm toán", "thuế",
            "tài chính ngân hàng", "phân tích tài chính",
        ],
        expansions=[
            "chương trình đào tạo tài chính ngân hàng kế toán luật kinh tế tín chỉ học phần",
        ],
        positives=[
            "tài chính", "ngân hàng", "kế toán",
            "luật kinh tế", "tín chỉ", "mã học phần",
        ],
        hard_keep=[
            "tài chính", "ngân hàng", "kế toán", "luật",
        ],
    ),
    R(
        name="ctdt_truyen_thong_da_phuong_tien_am_nhac",
        priority=95,
        meta_filter={"category": "ctdt"},
        terms=[
            "truyền thông đa phương tiện", "truyền thông", "đa phương tiện",
            "âm nhạc", "thanh nhạc", "sản xuất âm nhạc",
            "thiết kế", "mỹ thuật", "đồ họa",
        ],
        expansions=[
            "chương trình đào tạo truyền thông đa phương tiện âm nhạc thiết kế tín chỉ học phần",
        ],
        positives=[
            "truyền thông đa phương tiện", "âm nhạc",
            "thiết kế", "tín chỉ", "mã học phần",
        ],
        hard_keep=[
            "truyền thông", "âm nhạc", "thiết kế",
        ],
    ),
]


SCHEDULE_RULES: List[IntentRule] = [
    R(
        name="ke_hoach_nam_hoc_hoc_ky_tuan",
        priority=105,
        meta_filter={"category": "ke_hoach"},
        terms=[
            "kế hoạch năm học", "kế hoạch đào tạo", "năm học",
            "học kỳ 1", "học kỳ i", "học kỳ 2", "học kỳ ii",
            "học kỳ phụ", "hk1", "hk2", "hk phụ",
            "tuần học", "tuần thi", "lịch học vụ", "mốc thời gian",
        ],
        expansions=[
            "kế hoạch đào tạo năm học học kỳ tuần học tuần thi lịch học vụ",
            "thời gian học tập kế hoạch năm học học kỳ chính học kỳ phụ",
        ],
        positives=[
            "kế hoạch", "năm học", "học kỳ", "tuần",
            "lịch học vụ", "học kỳ phụ", "thời gian học tập",
        ],
        hard_keep=[
            "kế hoạch", "năm học", "học kỳ", "tuần",
        ],
    ),
    R(
        name="lich_thi_lich_hoc_nghi_le",
        priority=100,
        meta_filter={"category": "ke_hoach"},
        terms=[
            "lịch thi", "thi cuối kỳ", "thi kết thúc học phần",
            "lịch học", "lịch nghỉ", "nghỉ lễ", "tuần thi",
            "học bù", "nghỉ tết", "nghỉ hè", "thi học kỳ",
        ],
        expansions=[
            "kế hoạch năm học lịch thi tuần thi lịch học nghỉ lễ nghỉ tết",
        ],
        positives=[
            "lịch thi", "tuần thi", "lịch học", "nghỉ lễ",
            "học kỳ", "kế hoạch",
        ],
        hard_keep=[
            "lịch thi", "tuần thi", "lịch học", "nghỉ lễ",
        ],
    ),
    R(
        name="gio_hoc_tiet_hoc",
        priority=110,
        meta_filter={"category": "ke_hoach"},
        terms=[
            "tiết 1", "tiết 2", "tiết 3", "tiết 4", "tiết 5",
            "tiết 6", "tiết 7", "tiết 8", "tiết 9", "tiết 10",
            "tiết 11", "tiết 12", "tiết 13", "giờ học", "ca học",
            "thời gian học hàng ngày", "mấy giờ vào học", "mấy giờ tan học",
            "tiết học bắt đầu", "tiết học kết thúc",
        ],
        expansions=[
            "thời gian học hàng ngày tiết 1 tiết 2 tiết 3 tiết 7 tiết 13 giờ học",
            "bảng giờ học tiết học bắt đầu kết thúc",
        ],
        positives=[
            "thời gian học hàng ngày", "tiết", "giờ",
            "bắt đầu", "kết thúc",
        ],
        hard_keep=[
            "thời gian học hàng ngày", "tiết", "giờ",
        ],
    ),
]


# =========================================================
# 7. Gom toàn bộ rules
# =========================================================

INTENT_RULES: List[IntentRule] = (
    APPENDIX_RULES
    + QUESTION_TYPE_RULES
    + ACADEMIC_RULES
    + CTDT_RULES
    + SCHEDULE_RULES
)


# =========================================================
# 8. Detect intent
# =========================================================

def term_hit_score(query_norm: str, terms: List[str]) -> int:
    score = 0

    for term in terms:
        term_norm = normalize(term)

        if not term_norm:
            continue

        if term_norm in query_norm:
            score += 15 + min(len(term_norm), 50)

        tokens = [t for t in term_norm.split() if len(t) >= 3]

        if tokens:
            hit = sum(1 for t in tokens if t in query_norm)
            ratio = hit / len(tokens)

            if ratio >= 0.75:
                score += hit * 8
            elif ratio >= 0.5:
                score += hit * 4

    return score


def infer_intents(question: str, max_intents: int = 8) -> List[Tuple[IntentRule, int]]:
    q = normalize(question)
    matched: List[Tuple[IntentRule, int]] = []

    for rule in INTENT_RULES:
        hit = term_hit_score(q, rule.terms)

        if hit > 0:
            matched.append((rule, hit))

    matched.sort(
        key=lambda item: (item[0].priority, item[1]),
        reverse=True,
    )

    return matched[:max_intents]


def infer_filter(question: str):
    intents = infer_intents(question, max_intents=1)

    if not intents:
        return None

    return intents[0][0].meta_filter


# =========================================================
# 9. Query expansion
# =========================================================

def extract_dynamic_terms(question: str) -> List[str]:
    q = normalize(question)
    terms = []

    certificate_terms = [
        "ielts", "toeic", "toefl", "hsk", "hskk", "jlpt",
        "topik", "aptis", "cambridge", "vstep", "delf", "dalf", "dele",
    ]

    for cert in certificate_terms:
        if cert in q:
            terms.append(f"{cert} quy đổi chứng chỉ ngoại ngữ quốc tế")

    appendix_match = re.findall(r"(?:phu luc|pl)\s*0?(\d{1,2})", q)
    for number in appendix_match:
        terms.append(f"Phụ lục {int(number)}")

    course_codes = re.findall(r"\b[A-Z]{2,5}\d{2,5}\b", question.upper())
    for code in course_codes:
        terms.append(code)

    if re.search(r"\btiet\s*\d{1,2}\b", q):
        terms.append("thời gian học hàng ngày tiết học bắt đầu kết thúc")

    if "nghi hoc" in q or "bao luu" in q:
        terms.append("nghỉ học tạm thời quay trở lại học hồ sơ thủ tục")

    if "chuyen nganh" in q or "doi nganh" in q:
        terms.append("chuyển ngành chuyển chương trình hồ sơ điều kiện")

    if "thuc tap" in q:
        terms.append("đăng ký thực tập tốt nghiệp điều kiện hồ sơ")

    if "khoa luan" in q or "kltn" in q:
        terms.append("khóa luận tốt nghiệp đánh giá bảo vệ trình bày")

    if "xet tot nghiep" in q or "cap bang" in q or "van bang" in q:
        terms.append("xét tốt nghiệp cấp phát văn bằng hồ sơ điều kiện")

    return terms


def build_search_queries(question: str) -> List[str]:
    queries = [question]

    intents = infer_intents(question, max_intents=6)

    for rule, _hit in intents:
        queries.extend(rule.expansions)

        # Tạo query từ positive terms để kéo đúng filename/section
        if rule.positives:
            queries.append(" ".join(rule.positives[:8]))

    queries.extend(extract_dynamic_terms(question))

    unique = []
    seen = set()

    for q in queries:
        qn = normalize(q)
        if qn and qn not in seen:
            seen.add(qn)
            unique.append(q)

    return unique[:12]


# =========================================================
# 10. Deduplicate
# =========================================================

def deduplicate_docs(docs: List[Document]) -> List[Document]:
    seen = set()
    filtered = []

    for doc in docs:
        key = (
            doc.metadata.get("filename"),
            doc.metadata.get("page"),
            doc.metadata.get("section_title"),
            normalize((doc.page_content or "")[:350]),
        )

        if key in seen:
            continue

        seen.add(key)
        filtered.append(doc)

    return filtered


# =========================================================
# 11. Scoring
# =========================================================

STOPWORDS = {
    "toi", "minh", "em", "ban", "cho", "hoi", "muon", "can",
    "thi", "la", "gi", "nhu", "the", "nao", "phai", "lam",
    "sao", "co", "duoc", "khong", "neu", "trong", "ve", "cua",
    "o", "va", "hoac", "hay", "voi", "khi", "nao", "mot",
    "nay", "do", "de", "den", "tu", "se", "bi",
}


def keyword_overlap_score(question: str, full_text: str) -> int:
    q = normalize(question)
    t = normalize(full_text)

    tokens = [
        token for token in re.findall(r"[a-zA-Z0-9]+", q)
        if len(token) >= 3 and token not in STOPWORDS
    ]

    score = 0

    for token in tokens:
        if token in t:
            score += 7

    # Bigram bonus
    for i in range(len(tokens) - 1):
        phrase = f"{tokens[i]} {tokens[i + 1]}"
        if phrase in t:
            score += 15

    return score


def score_doc_for_query(question: str, doc: Document) -> int:
    qn = normalize(question)
    full_text = doc_full_text(doc)

    filename = get_meta(doc, "filename")
    source_file = get_meta(doc, "source_file")
    section_title = get_meta(doc, "section_title")
    category = get_meta(doc, "category")
    sub_category = get_meta(doc, "sub_category")
    document_type = get_meta(doc, "document_type")

    score = 0

    score += keyword_overlap_score(question, full_text)

    intents = infer_intents(question, max_intents=8)

    for rule, hit in intents:
        score += hit

        meta_filter = rule.meta_filter or {}

        if meta_filter.get("category") and normalize(meta_filter["category"]) == category:
            score += 100

        if meta_filter.get("sub_category") and normalize(meta_filter["sub_category"]) == sub_category:
            score += 140

        for term in rule.positives:
            tn = normalize(term)

            if not tn:
                continue

            if fuzzy_contains(tn, filename):
                score += 130

            if fuzzy_contains(tn, source_file):
                score += 100

            if fuzzy_contains(tn, section_title):
                score += 85

            if fuzzy_contains(tn, full_text):
                score += 40

        for term in rule.negatives:
            tn = normalize(term)

            if not tn:
                continue

            if fuzzy_contains(tn, filename):
                score -= 180

            if fuzzy_contains(tn, source_file):
                score -= 140

            if fuzzy_contains(tn, full_text):
                score -= 80

    # Exact certificate control
    certificate_terms = [
        "ielts", "toeic", "toefl", "hsk", "hskk", "jlpt",
        "topik", "aptis", "cambridge", "vstep", "delf", "dalf", "dele",
    ]

    for cert in certificate_terms:
        if cert in qn:
            if cert in full_text:
                score += 300
            else:
                score -= 120

    # Exact appendix control
    appendix_match = re.findall(r"(?:phu luc|pl)\s*0?(\d{1,2})", qn)
    for number in appendix_match:
        phrase = f"phu luc {int(number)}"
        if phrase in full_text:
            score += 500
        else:
            score -= 100

    # Chống các nhầm lẫn lớn
    if "ielts" in qn:
        if "xep lop tieng anh" in filename:
            score -= 350
        if "quy doi chung chi ngoai ngu quoc te" in filename:
            score += 350

    if "nghi hoc" in qn or "bao luu" in qn:
        if "phu luc 16" in filename or "nghi hoc tam thoi" in filename:
            score += 350
        if "phu luc 18" in filename or "chuyen co so dao tao" in filename:
            score -= 300
        if "thoi hoc/chuyen truong" in full_text:
            score -= 180

    if "xet tot nghiep" in qn or "cap bang" in qn or "van bang" in qn:
        if "phu luc 15" in filename:
            score += 300
        if "thuc tap tot nghiep" in filename:
            score -= 220

    if "chuyen nganh" in qn or "chuyen chuong trinh" in qn:
        if "phu luc 17" in filename:
            score += 300
        if "phu luc 18" in filename:
            score -= 200

    if "chuyen truong" in qn or "chuyen co so dao tao" in qn:
        if "phu luc 18" in filename:
            score += 300
        if "phu luc 17" in filename:
            score -= 200

    if "chuong trinh thu hai" in qn or "hoc hai nganh" in qn:
        if "phu luc 19" in filename:
            score += 300
        if "phu luc 1" in filename:
            score -= 150

    # Boost action sections
    action_terms = [
        "ho so", "don", "thu tuc", "buoc", "tiep nhan",
        "xet duyet", "phe duyet", "dieu kien", "thoi gian",
        "le phi", "ket qua", "quy trinh", "thong bao",
    ]

    for term in action_terms:
        if term in section_title:
            score += 25

    if document_type and document_type in full_text:
        score += 10

    return score


def rerank_docs(question: str, docs: List[Document]) -> List[Document]:
    return sorted(
        docs,
        key=lambda d: score_doc_for_query(question, d),
        reverse=True,
    )


# =========================================================
# 12. Soft filter
# Chỉ filter nếu có đủ kết quả. Tránh mất sạch context.
# =========================================================

def soft_filter_docs(question: str, docs: List[Document], min_keep: int = 2) -> List[Document]:
    intents = infer_intents(question, max_intents=2)

    if not intents:
        return docs

    hard_terms = []

    for rule, _hit in intents:
        hard_terms.extend(rule.hard_keep)

    if not hard_terms:
        return docs

    filtered = []

    for doc in docs:
        text = doc_full_text(doc)

        if any(fuzzy_contains(term, text) for term in hard_terms):
            filtered.append(doc)

    if len(filtered) >= min_keep:
        return filtered

    return docs


# =========================================================
# 13. Diversify
# Với câu hỏi thủ tục, giữ nhiều chunk cùng file hơn.
# Với câu hỏi rộng, tránh trùng page/section.
# =========================================================

def is_procedure_question(question: str) -> bool:
    q = normalize(question)
    return any(
        term in q
        for term in [
            "thu tuc", "quy trinh", "lam sao", "lam the nao",
            "phai lam gi", "ho so", "dieu kien", "dang ky",
            "xin", "nop",
        ]
    )


def diversify_docs(question: str, docs: List[Document], k: int) -> List[Document]:
    if is_procedure_question(question):
        return docs[:k]

    selected = []
    used_keys = set()

    for doc in docs:
        key = (
            doc.metadata.get("source_file"),
            doc.metadata.get("page"),
            doc.metadata.get("section_title"),
        )

        if key in used_keys:
            continue

        used_keys.add(key)
        selected.append(doc)

        if len(selected) >= k:
            return selected

    for doc in docs:
        if doc in selected:
            continue

        selected.append(doc)

        if len(selected) >= k:
            return selected

    return selected


# =========================================================
# 14. Main retriever
# =========================================================

# =========================================================
# 14.5. Strict router
# Chặn các intent rõ ràng khỏi bị loãng bởi rule rộng.
# =========================================================

def get_strict_route(query: str):
    q = normalize(query)

    # 1. Nghỉ học tạm thời / bảo lưu
    if (
        "nghi hoc tam thoi" in q
        or "bao luu" in q
        or ("nghi hoc" in q and "tam thoi" in q)
        or "quay tro lai hoc" in q
    ):
        return {
            "name": "strict_nghi_hoc_tam_thoi",
            "filters": [
                {"sub_category": "quy_trinh_hoc_vu"},
                {"category": "phu_luc"},
            ],
            "queries": [
                query,
                "Phụ lục 16",
                "Phụ lục số 16",
                "THỦ TỤC XÉT NGHỈ HỌC TẠM THỜI VÀ QUAY TRỞ LẠI HỌC",
                "nghỉ học tạm thời",
                "quay trở lại học",
                "nghỉ học tạm thời hồ sơ đơn xét duyệt phê duyệt",
            ],
            "preferred_file_terms": [
                "phụ lục 16",
                "thủ tục xét nghỉ học tạm thời",
                "nghỉ học tạm thời và quay trở lại học",
            ],
            "required_any": [
                "phụ lục 16",
                "phụ lục số 16",
                "nghỉ học tạm thời",
                "quay trở lại học",
                "thủ tục xét nghỉ học tạm thời",
            ],
            "negative": [
                "phụ lục 12",
                "phụ lục 14",
                "phụ lục 15",
                "phụ lục 17",
                "phụ lục 18",
                "phụ lục 19",
                "sửa điểm",
                "cảnh báo học tập",
                "buộc thôi học",
                "xét tốt nghiệp",
                "chuyển chương trình",
                "chuyển ngành",
                "chuyển cơ sở đào tạo",
                "chương trình thứ hai",
            ],
        }

    # 2. Chuyển ngành / chuyển chương trình
    if (
        "chuyen nganh" in q
        or "doi nganh" in q
        or "chuyen chuong trinh" in q
        or "doi chuong trinh" in q
    ):
        return {
            "name": "strict_chuyen_nganh",
            "filters": [
                {"sub_category": "quy_trinh_hoc_vu"},
                {"category": "phu_luc"},
            ],
            "queries": [
                query,
                "Phụ lục 17",
                "Phụ lục số 17",
                "QUY TRÌNH CHUYỂN CHƯƠNG TRÌNH, CHUYỂN NGÀNH ĐÀO TẠO",
                "hồ sơ chuyển ngành",
                "hồ sơ chuyển chương trình",
                "đơn đăng ký chuyển chương trình ngành đào tạo bảng kết quả học tập giấy báo trúng tuyển",
            ],
            "preferred_file_terms": [
                "phụ lục 17",
                "quy trình chuyển chương trình",
                "chuyển chương trình",
            ],
            "required_any": [
                "phụ lục 17",
                "chuyển chương trình",
                "chuyển ngành",
                "hồ sơ gồm",
            ],
            "negative": [
                "phụ lục 19",
                "phụ lục 18",
                "phụ lục 16",
                "phụ lục 15",
                "phụ lục 14",
                "sổ tay sinh viên",
                "chương trình thứ hai",
                "chuyển cơ sở đào tạo",
                "chuyển trường",
                "xét tốt nghiệp",
                "nghỉ học tạm thời",
            ],
        }

    # 3. Học chương trình thứ hai
    if (
        "chuong trinh thu hai" in q
        or "hoc hai nganh" in q
        or "hoc nganh thu hai" in q
        or "hoc bang hai" in q
        or "song nganh" in q
    ):
        return {
            "name": "strict_chuong_trinh_thu_hai",
            "filters": [{"sub_category": "quy_trinh_hoc_vu"}],
            "queries": [
                query,
                "Phụ lục 19 thủ tục đăng ký học chương trình thứ hai hồ sơ điều kiện",
                "đăng ký học chương trình thứ hai ngành đào tạo thứ hai",
            ],
            "required_any": [
                "phụ lục 19",
                "chương trình thứ hai",
                "ngành đào tạo thứ hai",
            ],
            "negative": [
                "phụ lục 17",
                "phụ lục 1",
                "chuyển ngành",
                "chuyển chương trình",
                "đăng ký học phần",
            ],
        }

    # 4. Chuyển trường / chuyển cơ sở đào tạo / thôi học / rút hồ sơ
    if (
        "chuyen truong" in q
        or "chuyen co so dao tao" in q
        or "rut ho so" in q
        or "xin thoi hoc" in q
        or "nghi han" in q
    ):
        return {
            "name": "strict_chuyen_truong_thoi_hoc",
            "filters": [{"sub_category": "quy_trinh_hoc_vu"}],
            "queries": [
                query,
                "Phụ lục 18 thủ tục chuyển cơ sở đào tạo chuyển trường rút hồ sơ thôi học",
                "đơn xin thôi học chuyển trường đi chuyển đến hồ sơ",
            ],
            "required_any": [
                "phụ lục 18",
                "chuyển cơ sở đào tạo",
                "chuyển trường",
                "đơn xin thôi học",
                "rút hồ sơ",
            ],
            "negative": [
                "phụ lục 16",
                "phụ lục 17",
                "phụ lục 19",
                "nghỉ học tạm thời",
                "chuyển ngành",
                "chương trình thứ hai",
            ],
        }

    # 5. Tiết học / giờ học
    if (
        re.search(r"\btiet\s*\d{1,2}\b", q)
        or "gio hoc" in q
        or "may gio vao hoc" in q
        or "may gio tan hoc" in q
        or "thoi gian hoc hang ngay" in q
    ):
        return {
            "name": "strict_tiet_hoc",
            # Có thể nằm trong kế hoạch hoặc sổ tay, nên thử cả hai.
            "filters": [
                {"category": "ke_hoach"},
                {"category": "so_tay"},
            ],
            "queries": [
                query,
                "thời gian học hàng ngày tiết học bắt đầu kết thúc",
                "bảng thời gian học hàng ngày tiết 1 tiết 7 tiết 13",
            ],
            "required_any": [
                "thời gian học hàng ngày",
                "tiết",
                "bắt đầu",
                "kết thúc",
            ],
            "negative": [
                "phụ lục 12",
                "phụ lục 14",
                "phụ lục 15",
                "phụ lục 19",
                "sửa điểm",
                "xét tốt nghiệp",
                "cảnh báo học tập",
            ],
        }

    # 6. Mã học phần / CTĐT
    if (
        "ma hoc phan" in q
        or "ma mon" in q
        or "hoc phan nao" in q
        or "mon nao" in q
        or "tin chi" in q
        or "chuong trinh dao tao" in q
        or "ctdt" in q
    ):
        extra_queries = []

        # Cứu các câu kiểu: "mã học phần quản trị thương hiệu là gì"
        if "quan tri thuong hieu" in q:
            extra_queries.append("Quản trị thương hiệu mã học phần tín chỉ")

        if "marketing" in q:
            extra_queries.append("Marketing chương trình đào tạo mã học phần tín chỉ")

        if "cong nghe thong tin" in q or "cntt" in q:
            extra_queries.append("Công nghệ thông tin chương trình đào tạo mã học phần tín chỉ")

        return {
            "name": "strict_ctdt_hoc_phan",
            "filters": [{"category": "ctdt"}],
            "queries": [
                query,
                "chương trình đào tạo mã học phần số tín chỉ học phần",
                "mã học phần học phần tín chỉ chương trình đào tạo",
                *extra_queries,
            ],
            "required_any": [
                "chương trình đào tạo",
                "mã học phần",
                "học phần",
                "tín chỉ",
                "quản trị thương hiệu",
            ],
            "negative": [
                "phụ lục 12",
                "phụ lục 14",
                "phụ lục 15",
                "phụ lục 19",
                "sửa điểm",
                "cảnh báo học tập",
                "xét tốt nghiệp",
            ],
        }

    # 7. Thẻ sinh viên
    if (
        "the sinh vien" in q
        or "mat the" in q
        or "lam lai the" in q
        or "cap lai the" in q
    ):
        return {
            "name": "strict_the_sinh_vien",
            "filters": [
                {"category": "so_tay"},
                {"category": "quy_che"},
            ],
            "queries": [
                query,
                "thẻ sinh viên mất thẻ làm lại thẻ cấp lại thẻ sinh viên",
                "sổ tay sinh viên thẻ sinh viên làm lại thẻ",
            ],
            "required_any": [
                "thẻ sinh viên",
                "mất thẻ",
                "làm lại thẻ",
                "cấp lại thẻ",
            ],
            "negative": [
                "phụ lục 12",
                "phụ lục 14",
                "phụ lục 15",
                "sửa điểm",
                "cảnh báo học tập",
                "xét tốt nghiệp",
            ],
        }

    return None


def strict_doc_score(query: str, doc: Document, route: dict) -> int:
    text = doc_full_text(doc)
    score = 0

    for term in route.get("required_any", []):
        if fuzzy_contains(term, text):
            score += 500

    for term in route.get("negative", []):
        if fuzzy_contains(term, text):
            score -= 700

    # Overlap câu hỏi vẫn có điểm nhưng thấp hơn route.
    score += keyword_overlap_score(query, text)

    return score


def keyword_rescue_from_chroma(db, route: dict) -> List[Document]:
    """
    Quét trực tiếp trong Chroma theo metadata filter rồi lọc bằng keyword.
    Dùng để cứu các intent rất rõ nhưng similarity search kéo sai.
    """
    rescued_docs: List[Document] = []

    filters = route.get("filters") or [None]

    for meta_filter in filters:
        try:
            if meta_filter:
                raw = db.get(
                    where=meta_filter,
                    include=["documents", "metadatas"],
                )
            else:
                raw = db.get(
                    include=["documents", "metadatas"],
                )

            documents = raw.get("documents") or []
            metadatas = raw.get("metadatas") or []

            for content, metadata in zip(documents, metadatas):
                if not content:
                    continue

                doc = Document(
                    page_content=content,
                    metadata=metadata or {},
                )

                text = doc_full_text(doc)

                if any(fuzzy_contains(term, text) for term in route.get("required_any", [])):
                    rescued_docs.append(doc)

        except Exception:
            continue

    return rescued_docs


def keyword_rescue_from_chunks(route: dict) -> List[Document]:
    """
    Cứu tài liệu bằng cách quét trực tiếp data/chunks/chunks.jsonl.
    Cách này chắc hơn Chroma similarity_search khi intent đã rất rõ.
    """
    rescued_docs: List[Document] = []

    chunks_file = Path(settings.CHUNKS_DIR) / "chunks.jsonl"

    if not chunks_file.exists():
        return rescued_docs

    required_terms = route.get("required_any", [])
    negative_terms = route.get("negative", [])

    with chunks_file.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue

            try:
                item = json.loads(line)
            except Exception:
                continue

            text = item.get("text", "")
            metadata = item.get("metadata", {}) or {}

            # Bổ sung id nếu thiếu
            if item.get("id") and not metadata.get("id"):
                metadata["id"] = item.get("id")

            # Bổ sung filename nếu thiếu
            if not metadata.get("filename"):
                source_file = metadata.get("source_file", "")
                if source_file:
                    metadata["filename"] = Path(source_file).name

            doc = Document(
                page_content=text,
                metadata=metadata,
            )

            full_text = doc_full_text(doc)

            has_required = any(
                fuzzy_contains(term, full_text)
                for term in required_terms
            )

            if not has_required:
                continue

            # Với strict route, vẫn cho docs có negative đi qua,
            # nhưng điểm sẽ bị trừ ở strict_doc_score.
            # Không loại bỏ cứng ở đây để tránh mất context nếu OCR lỗi.
            rescued_docs.append(doc)

    return rescued_docs


def retrieve_strict_context(db, query: str, route: dict, k: int = 5) -> List[Document]:
    docs: List[Document] = []

    filters = route.get("filters") or [None]
    queries = route.get("queries") or [query]

    # 1. Similarity search có kiểm soát route
    for meta_filter in filters:
        for search_query in queries:
            try:
                if meta_filter:
                    docs.extend(
                        db.similarity_search(
                            search_query,
                            k=30,
                            filter=meta_filter,
                        )
                    )
                else:
                    docs.extend(
                        db.similarity_search(
                            search_query,
                            k=30,
                        )
                    )
            except Exception:
                try:
                    docs.extend(
                        db.similarity_search(
                            search_query,
                            k=30,
                        )
                    )
                except Exception:
                    pass

    # 2. Keyword rescue trực tiếp từ Chroma
    docs.extend(keyword_rescue_from_chroma(db, route))

    # 3. Keyword rescue trực tiếp từ chunks.jsonl
    # Cực quan trọng cho các route rõ như Phụ lục 16, 17, 19, CTĐT...
    docs.extend(keyword_rescue_from_chunks(route))

    docs = deduplicate_docs(docs)

    # Ưu tiên đúng file phụ lục nếu route yêu cầu.
    preferred_file_terms = route.get("preferred_file_terms", [])

    if preferred_file_terms:
        preferred_docs = []

        for doc in docs:
            file_text = normalize(
                f"{doc.metadata.get('filename', '')} "
                f"{doc.metadata.get('source_file', '')}"
            )

            if any(
                    fuzzy_contains(term, file_text)
                    for term in preferred_file_terms
            ):
                preferred_docs.append(doc)

        if preferred_docs:
            docs = preferred_docs

    # 3. Chỉ giữ docs có required_any nếu có
    strict_docs = [
        doc for doc in docs
        if any(
            fuzzy_contains(term, doc_full_text(doc))
            for term in route.get("required_any", [])
        )
    ]

    if strict_docs:
        docs = strict_docs

    docs = sorted(
        docs,
        key=lambda d: strict_doc_score(query, d, route),
        reverse=True,
    )

    return docs[:k]


def retrieve_context(query: str, k: int = 5):
    db = load_vector_store()

    # =====================================================
    # 1. Strict route trước
    # Các intent rõ ràng phải được ép về đúng nguồn.
    # =====================================================
    strict_route = get_strict_route(query)

    print("STRICT_ROUTE =", strict_route["name"] if strict_route else None)

    if strict_route:
        strict_docs = retrieve_strict_context(db, query, strict_route, k=k)

        print("STRICT_DOCS =", [
            doc.metadata.get("filename") for doc in strict_docs[:5]
        ])

        # Nếu strict route đã tìm được tài liệu, trả luôn.
        # Không kiểm tra top_score nữa vì strict route đã là intent chắc chắn.
        if strict_docs:
            return strict_docs[:k]

    # =====================================================
    # 2. Fallback: retriever rộng cũ
    # =====================================================
    intents = infer_intents(query, max_intents=8)
    search_queries = build_search_queries(query)

    docs: List[Document] = []

    # Search có filter theo nhiều intent
    for rule, _hit in intents:
        if not rule.meta_filter:
            continue

        for search_query in search_queries[:8]:
            try:
                docs.extend(
                    db.similarity_search(
                        search_query,
                        k=30,
                        filter=rule.meta_filter,
                    )
                )
            except Exception:
                docs.extend(
                    db.similarity_search(
                        search_query,
                        k=30,
                    )
                )

    # Search không filter để cứu metadata sai hoặc câu hỏi lạ
    for search_query in search_queries[:6]:
        docs.extend(
            db.similarity_search(
                search_query,
                k=18,
            )
        )

    # Search rộng category fallback
    category_fallbacks = [
        {"category": "quy_che"},
        {"category": "so_tay"},
        {"category": "ctdt"},
        {"category": "ke_hoach"},
        {"category": "phu_luc"},
    ]

    for meta_filter in category_fallbacks:
        try:
            docs.extend(
                db.similarity_search(
                    query,
                    k=8,
                    filter=meta_filter,
                )
            )
        except Exception:
            pass

    if not docs:
        docs = db.similarity_search(query, k=50)

    docs = deduplicate_docs(docs)
    docs = rerank_docs(query, docs)
    docs = soft_filter_docs(query, docs, min_keep=2)
    docs = rerank_docs(query, docs)
    docs = diversify_docs(query, docs, k=k)

    return docs[:k]