import csv
import json
import argparse
import sys
import re
import os

def compute_metrics(csv_path, gold_path, report_path):
    print("="*60)
    print(" BÁO CÁO KẾT QUẢ ĐÁNH GIÁ (RAG EVALUATION METRICS) ")
    print("="*60)

    # 1. Load Ground Truth
    try:
        with open(gold_path, 'r', encoding='utf-8') as f:
            ground_truth = json.load(f)
    except Exception as e:
        print(f"Lỗi đọc file Ground Truth: {e}")
        return

    # 2. Read Test Results
    total_queries = 0
    evaluated_rag = 0
    accuracy_hits = 0
    
    # metrics storage
    precision_1, precision_3, precision_5 = 0, 0, 0
    recall_1, recall_3, recall_5 = 0, 0, 0
    mrr_sum = 0
    
    # Error tracking
    hallucination_count = 0
    faithfulness_count = 0
    
    error_retrieval_fail = []
    error_hallucination = []
    error_missing_context = []
    error_ambiguous_query = []
    
    # Vietnamese Scenarios Analysis
    vn_khong_dau = []
    vn_viet_tat = []
    vn_slang = []
    vn_typo = []

    # Dictionary cho viết tắt và slang sinh viên
    VIET_TAT_LIST = ['sv', 'gv', 'kltn', 'tttn', 'cpa', 'gpa', 'hp', 'đh', 'tc', 'nckh', 'cntt', 'dtvt', 'khmt']
    SLANG_LIST = ['tạch', 'rớt', 'toang', 'nợ môn', 'đúp', 'cút', 'khớp', 'tịt', 'cày', 'cày điểm', 'kéo cpa']

    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                q = row.get('question', '').strip()
                sources_str = row.get('sources', '')
                notes = row.get('notes', '').lower()
                correct_score = float(row.get('correct', '0.0'))
                answer = row.get('answer', '').strip()
                
                if not q: continue
                total_queries += 1
                
                # --- PHÂN TÍCH TIẾNG VIỆT THỰC TẾ ---
                q_lower = q.lower()
                
                # 1. Không dấu: Chỉ chứa các ký tự ascii cơ bản (mà không phải câu tiếng anh 100%)
                if re.match(r'^[a-z0-9\s\?]+$', q_lower) and len(q.split()) > 2:
                    vn_khong_dau.append(q)
                    
                # 2. Viết tắt sinh viên
                words = [w.strip("?,.!") for w in q_lower.split()]
                if any(w in VIET_TAT_LIST for w in words):
                    vn_viet_tat.append(q)
                    
                # 3. Slang học vụ
                if any(slang in q_lower for slang in SLANG_LIST):
                    vn_slang.append(q)
                    
                # 4. Typo (Ghi chú trong test case "lỗi chính tả" hoặc "typo")
                if "typo" in notes or "chính tả" in notes or "gõ sai" in notes:
                    vn_typo.append(q)
                
                # Trích xuất danh sách file từ sources
                raw_sources = sources_str.split('|')
                retrieved_docs = []
                for src in raw_sources:
                    src = src.strip()
                    match = re.search(r'^(.*?\.pdf)', src, re.IGNORECASE)
                    if match:
                        doc_name = match.group(1).split('\\')[-1].split('/')[-1]
                        if doc_name not in retrieved_docs:
                            retrieved_docs.append(doc_name)
                    else:
                        if src and "(trang " not in src:
                             retrieved_docs.append(src)
                             
                # Phân tích Missing Context (Không tìm thấy tài liệu nào)
                if not retrieved_docs or sources_str.strip() == "":
                    error_missing_context.append({"query": q, "answer": answer})
                    
                # Phân tích Ambiguous Query (Câu hỏi quá ngắn, dưới 5 từ)
                if len(q.split()) < 5:
                    error_ambiguous_query.append({"query": q})
                
                # Xử lý Faithfulness & Hallucination từ Label thủ công
                if correct_score > 0.5:
                    faithfulness_count += 1
                
                if "bịa" in notes or "hallucination" in notes or "ảo giác" in notes:
                    hallucination_count += 1
                    error_hallucination.append({"query": q, "answer": answer, "notes": notes})

                # Đánh giá RAG nếu câu hỏi có trong Ground Truth
                gold_docs = []
                for gq, docs in ground_truth.items():
                    if gq.lower() in q.lower() or q.lower() in gq.lower():
                        gold_docs = docs
                        break
                
                if gold_docs:
                    evaluated_rag += 1
                    
                    is_hit = any(g in retrieved_docs for g in gold_docs)
                    if is_hit:
                        accuracy_hits += 1
                    else:
                        # Phân tích Retrieval Fail (Tìm sai tài liệu so với đáp án)
                        error_retrieval_fail.append({
                            "query": q, 
                            "expected": gold_docs, 
                            "got": retrieved_docs
                        })

                    # K-Metrics
                    hits_at_1 = sum(1 for g in gold_docs if g in retrieved_docs[:1])
                    hits_at_3 = sum(1 for g in gold_docs if g in retrieved_docs[:3])
                    hits_at_5 = sum(1 for g in gold_docs if g in retrieved_docs[:5])

                    precision_1 += hits_at_1 / 1.0
                    precision_3 += hits_at_3 / 3.0 if len(retrieved_docs) >= 3 else (hits_at_3 / len(retrieved_docs) if retrieved_docs else 0)
                    precision_5 += hits_at_5 / 5.0 if len(retrieved_docs) >= 5 else (hits_at_5 / len(retrieved_docs) if retrieved_docs else 0)

                    recall_1 += hits_at_1 / len(gold_docs)
                    recall_3 += hits_at_3 / len(gold_docs)
                    recall_5 += hits_at_5 / len(gold_docs)

                    # MRR
                    rr = 0
                    for i, doc in enumerate(retrieved_docs):
                        if doc in gold_docs:
                            rr = 1.0 / (i + 1)
                            break
                    mrr_sum += rr

    except Exception as e:
        print(f"Lỗi khi đọc CSV: {e}")
        return

    # 3. Print Results
    if evaluated_rag == 0:
        print("Không tìm thấy câu hỏi nào trong Ground Truth khớp với Test CSV.")
        evaluated_rag = 1
    
    print(f"Tổng số query đã test: {total_queries}")
    print(f"Số query có đối chiếu (Ground Truth): {evaluated_rag}")
    print("-"*60)
    print(" [1] HIỆU SUẤT TRÍCH XUẤT (RETRIEVAL METRICS) ")
    print(f"  - Retrieval Accuracy  : { (accuracy_hits/evaluated_rag)*100 :.2f}%")
    print(f"  - P@1 (Precision@1)   : { (precision_1/evaluated_rag)*100 :.2f}%")
    print(f"  - P@3 (Precision@3)   : { (precision_3/evaluated_rag)*100 :.2f}%")
    print(f"  - R@1 (Recall@1)      : { (recall_1/evaluated_rag)*100 :.2f}%")
    print(f"  - R@3 (Recall@3)      : { (recall_3/evaluated_rag)*100 :.2f}%")
    print(f"  - MRR (Mean Reci Rank): { (mrr_sum/evaluated_rag) :.4f}")
    
    print()
    print(" [2] HIỆU SUẤT SINH VĂN BẢN (GENERATION METRICS) ")
    if total_queries > 0:
        print(f"  - Faithfulness Rate   : { (faithfulness_count/total_queries)*100 :.2f}%")
        print(f"  - Hallucination Rate  : { (hallucination_count/total_queries)*100 :.2f}%")
        print(f"  - Grounded Eval Score : Hệ thống kết hợp {faithfulness_count} câu trả lời đúng gốc.")
    print("="*60)
    
    # 4. Xuất Báo cáo Phân tích Lỗi (Error Analysis)
    try:
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("# BÁO CÁO PHÂN TÍCH LỖI (ERROR ANALYSIS REPORT)\n\n")
            
            f.write("## 1. Retrieval Fail (Lấy sai tài liệu)\n")
            f.write("*Các câu hỏi lấy được tài liệu nhưng không khớp với Ground Truth.*\n\n")
            if not error_retrieval_fail:
                f.write("Không phát hiện lỗi.\n\n")
            for item in error_retrieval_fail:
                f.write(f"- **Câu hỏi:** {item['query']}\n")
                f.write(f"  - **Kỳ vọng (Gold):** {', '.join(item['expected'])}\n")
                f.write(f"  - **Thực tế lấy (Got):** {', '.join(item['got']) if item['got'] else 'Không có'}\n\n")

            f.write("## 2. Hallucination (Ảo giác / Bịa thông tin)\n")
            f.write("*Các câu hỏi bị con người đánh dấu là AI bịa/ảo giác.*\n\n")
            if not error_hallucination:
                f.write("Không phát hiện lỗi.\n\n")
            for item in error_hallucination:
                f.write(f"- **Câu hỏi:** {item['query']}\n")
                f.write(f"  - **Câu trả lời AI:** {item['answer']}\n")
                f.write(f"  - **Ghi chú lỗi:** {item['notes']}\n\n")

            f.write("## 3. Missing Context (Thiếu Context / Không tra được)\n")
            f.write("*Các câu hỏi RAG không tìm được tài liệu nào (Sources trống hoặc rỗng).*\n\n")
            if not error_missing_context:
                f.write("Không phát hiện lỗi.\n\n")
            for item in error_missing_context:
                f.write(f"- **Câu hỏi:** {item['query']}\n\n")

            f.write("## 4. Ambiguous Query (Câu hỏi mơ hồ)\n")
            f.write("*Các câu hỏi quá ngắn (dưới 5 từ), thiếu thành phần hoặc ngữ cảnh.*\n\n")
            if not error_ambiguous_query:
                f.write("Không phát hiện lỗi.\n\n")
            for item in error_ambiguous_query:
                f.write(f"- **Câu hỏi:** {item['query']}\n")
                
            f.write("\n## 5. Phân tích Tình huống Tiếng Việt Thực tế (Vietnamese Real-World Endge Cases)\n")
            f.write("*Hệ thống tự động phát hiện các câu hỏi mang đậm văn hóa giao tiếp của sinh viên.* \n\n")
            
            f.write("### 5.1 Câu hỏi không dấu (Unaccented Queries)\n")
            f.write(f"Số lượng: {len(vn_khong_dau)} câu\n")
            for item in vn_khong_dau: f.write(f"- {item}\n")
            
            f.write("\n### 5.2 Chứa từ viết tắt (Abbreviations)\n")
            f.write(f"Số lượng: {len(vn_viet_tat)} câu\n")
            for item in vn_viet_tat: f.write(f"- {item}\n")
            
            f.write("\n### 5.3 Ngôn ngữ lóng / Từ lóng (Slang)\n")
            f.write(f"Số lượng: {len(vn_slang)} câu\n")
            for item in vn_slang: f.write(f"- {item}\n")
            
            f.write("\n### 5.4 Sai lỗi chính tả (Typo)\n")
            f.write(f"Số lượng: {len(vn_typo)} câu (Dựa theo nhãn thủ công)\n")
            for item in vn_typo: f.write(f"- {item}\n")
            
        print(f"Đã xuất báo cáo phân tích lỗi chi tiết tại: {report_path}")
    except Exception as e:
        print(f"Lỗi ghi file báo cáo lỗi: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--pred', default='tests/test_results_graded.csv', help='File CSV chấm điểm')
    parser.add_argument('--gold', default='tests/ground_truth.json', help='File Ground truth')
    parser.add_argument('--report', default='tests/error_analysis_report.md', help='File xuất báo cáo lỗi')
    args, unknown = parser.parse_known_args()
    
    compute_metrics(args.pred, args.gold, args.report)
