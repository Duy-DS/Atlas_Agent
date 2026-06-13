import importlib.util
import sys
import unittest
from pathlib import Path


def load_subject_router_module():
    module_path = Path(__file__).resolve().parents[1] / "agents" / "subject_router.py"
    spec = importlib.util.spec_from_file_location("subject_router_under_test", module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class SubjectRouterTest(unittest.TestCase):
    def setUp(self):
        self.router = load_subject_router_module()

    def classify(self, question):
        return self.router.classify_subject({"qid": "1", "question": question})

    def test_classifies_requested_domains(self):
        examples = [
            ("Thuật toán quicksort có độ phức tạp trung bình là gì?", "it"),
            ("Giải phương trình 2x + 3 = 7", "math"),
            ("Định luật II Newton phát biểu như thế nào?", "physics"),
            ("Dãy Hoàng Liên Sơn thuộc vùng địa lý nào?", "geography"),
            ("Chiến dịch Điện Biên Phủ diễn ra năm nào?", "history"),
            ("Choose the correct tense for this sentence", "english"),
            ("Nếu A kéo theo B và A đúng thì kết luận nào hợp logic?", "logic"),
            ("Loài hoa nào thường nở vào mùa xuân?", "other"),
        ]

        for question, subject in examples:
            with self.subTest(question=question):
                self.assertEqual(self.classify(question).subject, subject)

    def test_retries_only_high_risk_domains_initially(self):
        self.assertTrue(self.classify("Tính giá trị của 2x khi x = 3").needs_domain_retry)
        self.assertTrue(self.classify("Một vật rơi tự do có gia tốc bao nhiêu?").needs_domain_retry)
        self.assertTrue(self.classify("Nếu mọi A là B và C là A thì kết luận nào đúng?").needs_domain_retry)
        self.assertFalse(self.classify("Chiến dịch Điện Biên Phủ diễn ra năm nào?").needs_domain_retry)

    def test_simple_domain_questions_do_not_need_domain_retry_by_default(self):
        self.assertFalse(self.classify("Toán học là môn học về điều gì?").needs_domain_retry)
        self.assertFalse(self.classify("Vật lý nghiên cứu lĩnh vực nào?").needs_domain_retry)
        self.assertFalse(self.classify("Logic là gì?").needs_domain_retry)

    def test_high_risk_domain_signals_still_need_domain_retry(self):
        self.assertTrue(self.classify("Đáp án nào không đúng về phương trình x = 2?").needs_domain_retry)
        self.assertTrue(self.classify("Một điện trở có hiệu điện thế 12V thì dòng điện là bao nhiêu?").needs_domain_retry)
        self.assertTrue(self.classify("Nếu A kéo theo B thì mệnh đề nào mâu thuẫn?").needs_domain_retry)


if __name__ == "__main__":
    unittest.main()
