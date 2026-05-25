from locust import HttpUser, task, between
import random

SAMPLE_QUESTIONS = [
    "Học phí một tín chỉ ngành CNTT là bao nhiêu?",
    "Học phí kỳ này tăng bao nhiêu so với kỳ trước?",
    "Quy định nộp học phí trễ hạn?",
    "Mức học bổng khuyến khích học tập?",
    "Điều kiện xét học bổng cho sinh viên giỏi?",
    "Học bổng dành cho sinh viên có hoàn cảnh khó khăn?",
    "Điều kiện xét tốt nghiệp đại học?",
    "Thời hạn nộp khóa luận tốt nghiệp?",
    "Quy định về điểm trung bình tích lũy để tốt nghiệp?",
    "Quy trình xin bảo lưu kết quả học tập?",
    "Thủ tục xin nghỉ học tạm thời?",
    "Hồ sơ chuyển ngành gồm những gì?",
    "Điều kiện được chuyển ngành học?",
    "Quy đổi điểm IELTS sang tiếng Anh khoa?",
    "Bảng quy đổi chứng chỉ TOEIC?",
]

class ChatbotUser(HttpUser):
    wait_time = between(1, 3)
    
    @task
    def ask_question(self):
        question = random.choice(SAMPLE_QUESTIONS)
        with self.client.post(
            "/ask",
            json={"question": question},
            headers={"Content-Type": "application/json"},
            catch_response=True,
            name="/ask"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status {response.status_code}: {response.text[:200]}")