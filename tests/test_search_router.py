import importlib.util
import sys
import unittest
from pathlib import Path


def load_search_router_module():
    module_path = Path(__file__).resolve().parents[1] / "agents" / "search_router.py"
    spec = importlib.util.spec_from_file_location("search_router_under_test", module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


search_router = load_search_router_module()


class SearchRouterKeywordTest(unittest.TestCase):
    def test_should_search_statistics_questions_even_with_answer(self):
        examples = [
            "Dân số Việt Nam là bao nhiêu?",
            "GDP của Nhật Bản đứng thứ mấy thế giới?",
            "Thống kê sản lượng lúa của Thái Lan?",
        ]

        for question in examples:
            with self.subTest(question=question):
                self.assertTrue(search_router.should_search({"qid": "1", "question": question}, "A"))

    def test_should_not_search_triangle_question_because_gia_is_inside_giac(self):
        question = "Một tam giác vuông có hai cạnh góc vuông dài 6 và 8. Cạnh huyền dài bao nhiêu?"

        decision = search_router.route_search({"qid": "1", "question": question}, "A")

        self.assertFalse(decision.needs_search)
        self.assertEqual(decision.reason, "stable_question")

    def test_should_search_price_questions_when_gia_is_a_word(self):
        question = "Giá vàng là bao nhiêu?"

        decision = search_router.route_search({"qid": "1", "question": question}, "A")

        self.assertTrue(decision.needs_search)
        self.assertEqual(decision.reason, "volatile_keyword:giá")

    def test_should_not_search_stable_academic_questions_only_because_of_domain(self):
        examples = [
            "Công thức toán học nào dùng để tính diện tích hình tròn?",
            "Nguyên tố hóa học nào có ký hiệu Fe?",
            "Định luật vật lý nào mô tả lực hấp dẫn?",
            "Dãy Hoàng Liên Sơn thuộc vùng địa lý nào?",
        ]

        for question in examples:
            with self.subTest(question=question):
                self.assertFalse(search_router.should_search({"qid": "1", "question": question}, "A"))


if __name__ == "__main__":
    unittest.main()
