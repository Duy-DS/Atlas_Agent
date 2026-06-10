import unittest
from unittest.mock import patch

from agents.search_router import should_search
from agents.web_search import DisabledWebSearch, DuckDuckGoHtmlSearch, StaticWebSearch, default_web_search
import main


class WebSearchRoutingTest(unittest.TestCase):
    def test_should_not_search_stable_question_with_valid_answer(self):
        row = {"qid": "1", "question": "1+1 bằng bao nhiêu?"}

        self.assertFalse(should_search(row, "A"))

    def test_should_search_when_answer_is_na(self):
        row = {"qid": "1", "question": "Câu hỏi mơ hồ?"}

        self.assertTrue(should_search(row, "N/A"))

    def test_should_search_current_or_latest_questions_even_with_answer(self):
        row = {"qid": "1", "question": "CEO hiện nay của công ty X là ai?"}

        self.assertTrue(should_search(row, "A"))

    def test_disabled_search_returns_empty_context(self):
        result = DisabledWebSearch().search("anything")

        self.assertEqual(result.context, "")
        self.assertFalse(result.enabled)

    def test_duckduckgo_search_parses_html_results(self):
        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return b'<a rel="nofollow" class="result__a" href="/">Result One</a>'

        with patch("agents.web_search.urlopen", return_value=FakeResponse()):
            result = DuckDuckGoHtmlSearch().search("query")

        self.assertTrue(result.enabled)
        self.assertEqual(result.source, "duckduckgo")
        self.assertIn("Result One", result.context)

    def test_default_search_uses_duckduckgo_when_enabled_without_endpoint(self):
        with patch.dict("os.environ", {"WEB_SEARCH_ENABLED": "true"}, clear=True):
            self.assertIsInstance(default_web_search(), DuckDuckGoHtmlSearch)

    def test_static_search_can_reanswer_single_row(self):
        row = {"qid": "7", "question": "CEO hiện nay là ai?", "A": "a", "B": "b", "C": "c", "D": "d"}
        search = StaticWebSearch({"CEO hiện nay là ai?": "Nguồn web: đáp án là C."})
        calls = []

        def fake_agent(prompt):
            calls.append(prompt)
            return "qid,answer\n7,C\n"

        with patch.object(main, "agent", fake_agent):
            self.assertEqual(main.predict_with_search(row, search), "C")

        self.assertEqual(len(calls), 1)
        self.assertIn("Nguồn web", calls[0])
        self.assertIn("qid,question,A,B,C,D", calls[0])


if __name__ == "__main__":
    unittest.main()
