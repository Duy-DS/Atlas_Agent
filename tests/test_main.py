import csv
import contextlib
import io
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch


class _FakeOllamaClient:
    def __init__(self, *args, **kwargs):
        pass

    def chat(self, **kwargs):
        return {"message": {"content": ""}}


sys.modules.setdefault("ollama", types.SimpleNamespace(Client=_FakeOllamaClient, chat=lambda **kwargs: None, ChatResponse=dict))


class _FakeTool:
    def __init__(self, fn):
        self._fn = fn

    def invoke(self, arg):
        return self._fn(arg)


def _fake_tool(name):
    def decorator(fn):
        return _FakeTool(fn)

    return decorator


class _FakeCompiledGraph:
    def __init__(self, graph):
        self._graph = graph

    def invoke(self, state):
        current = self._graph.entry_point
        while current != "END":
            state = self._graph.nodes[current](state)
            if current in self._graph.conditional_edges:
                route_fn, mapping = self._graph.conditional_edges[current]
                current = mapping[route_fn(state)]
            else:
                current = self._graph.edges.get(current, "END")
        return state


class _FakeStateGraph:
    def __init__(self, state_type):
        self.nodes = {}
        self.edges = {}
        self.conditional_edges = {}
        self.entry_point = None

    def add_node(self, name, fn):
        self.nodes[name] = fn

    def set_entry_point(self, name):
        self.entry_point = name

    def add_conditional_edges(self, source, route_fn, mapping):
        self.conditional_edges[source] = (route_fn, mapping)

    def add_edge(self, source, target):
        self.edges[source] = target

    def compile(self):
        return _FakeCompiledGraph(self)


sys.modules.setdefault("langchain_core", types.SimpleNamespace())
sys.modules.setdefault("langchain_core.tools", types.SimpleNamespace(tool=_fake_tool))
sys.modules.setdefault("langgraph", types.SimpleNamespace())
sys.modules.setdefault("langgraph.graph", types.SimpleNamespace(END="END", StateGraph=_FakeStateGraph))

import main
from agents.web_search import StaticWebSearch


KNOWLEDGE_MARKER = "Các lựa chọn:"
SEARCH_CONTEXT_MARKER = "Ngu canh web"
SINGLE_RETRY_MARKER = "Chi tra ve dung 2 dong CSV"


def _refuse_agent(prompt):
    raise AssertionError(f"agent() should not be called for this row, got prompt: {prompt!r}")


def _refuse_raw_chat(prompt, **kwargs):
    raise AssertionError(f"raw_chat() should not be called for this row, got prompt: {prompt!r}")


class MainOutputTest(unittest.TestCase):
    def test_parse_model_answers_handles_preamble_and_colon_rows(self):
        output = "dau ra:\nqid,answer  \n5:A\n6, B\n"

        self.assertEqual(main.parse_model_answers(output), {"5": "A", "6": "B"})

    def test_predict_single_retry_uses_one_forced_call(self):
        row = {"qid": "4", "question": "one", "A": "a", "B": "b", "C": "c", "D": "d"}
        calls = []

        def fake_agent(prompt):
            calls.append(prompt)
            return "dau ra:\nqid,answer\n1,B"

        with patch.object(main, "agent", fake_agent):
            self.assertEqual(main.predict_single_retry(row), "B")

        self.assertEqual(len(calls), 1)
        self.assertIn("Chi tra ve dung 2 dong CSV", calls[0])

    def test_run_uses_workflow_v2_calculation_without_any_llm_call(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            input_path = tmp_path / "public_test.csv"
            output_path = tmp_path / "pred.csv"
            input_path.write_text(
                "qid,question,A,B,C,D\n"
                "1,Tính 2 + 2 bằng bao nhiêu?,3,4,5,6\n",
                encoding="utf-8",
            )

            with patch.object(main, "agent", _refuse_agent), patch.object(main, "raw_chat", _refuse_raw_chat):
                main.run(input_path=input_path, output_path=output_path, search_client=StaticWebSearch({}))

            with output_path.open(newline="", encoding="utf-8") as f:
                self.assertEqual(list(csv.DictReader(f)), [{"qid": "1", "answer": "B"}])
            with output_path.with_name("pred_audit.csv").open(newline="", encoding="utf-8") as f:
                self.assertEqual(
                    list(csv.DictReader(f)),
                    [{"qid": "1", "answer": "B", "confidence": "0.95", "needs_search": "false", "search_used": "false", "answer_source": "workflow_v2:calculation"}],
                )

    def test_run_uses_workflow_v2_retrieval(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            input_path = tmp_path / "public_test.csv"
            output_path = tmp_path / "pred.csv"
            input_path.write_text(
                "qid,question,A,B,C,D\n"
                '1,"Đoạn thông tin: Hà Nội là thủ đô Việt Nam.\n\nCâu hỏi: Thủ đô là gì?",Huế,Hà Nội,Đà Nẵng,Huế\n',
                encoding="utf-8",
            )

            def fake_raw_chat(prompt, **kwargs):
                self.assertIn("Chỉ sử dụng thông tin", prompt)
                return "B"

            with patch.object(main, "agent", _refuse_agent), patch.object(main, "raw_chat", fake_raw_chat):
                main.run(input_path=input_path, output_path=output_path, search_client=StaticWebSearch({}))

            with output_path.open(newline="", encoding="utf-8") as f:
                self.assertEqual(list(csv.DictReader(f)), [{"qid": "1", "answer": "B"}])
            with output_path.with_name("pred_audit.csv").open(newline="", encoding="utf-8") as f:
                self.assertEqual(
                    list(csv.DictReader(f)),
                    [{"qid": "1", "answer": "B", "confidence": "0.80", "needs_search": "false", "search_used": "false", "answer_source": "workflow_v2:retrieval"}],
                )

    def test_run_uses_workflow_v2_knowledge_majority_vote(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            input_path = tmp_path / "public_test.csv"
            output_path = tmp_path / "pred.csv"
            input_path.write_text(
                "qid,question,A,B,C,D\n"
                "1,Thủ đô của Việt Nam là gì?,Hà Nội,Huế,Đà Nẵng,Cần Thơ\n",
                encoding="utf-8",
            )

            def fake_raw_chat(prompt, **kwargs):
                self.assertIn(KNOWLEDGE_MARKER, prompt)
                return "ANSWER: A\nCONFIDENCE: 0.9"

            with patch.object(main, "agent", _refuse_agent), patch.object(main, "raw_chat", fake_raw_chat):
                main.run(input_path=input_path, output_path=output_path, search_client=StaticWebSearch({}))

            with output_path.open(newline="", encoding="utf-8") as f:
                self.assertEqual(list(csv.DictReader(f)), [{"qid": "1", "answer": "A"}])
            with output_path.with_name("pred_audit.csv").open(newline="", encoding="utf-8") as f:
                self.assertEqual(
                    list(csv.DictReader(f)),
                    [{"qid": "1", "answer": "A", "confidence": "0.97", "needs_search": "false", "search_used": "false", "answer_source": "workflow_v2:knowledge"}],
                )

    def test_run_falls_back_to_single_retry_when_workflow_v2_cannot_parse_an_answer(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            input_path = tmp_path / "public_test.csv"
            output_path = tmp_path / "pred.csv"
            input_path.write_text(
                "qid,question,A,B,C,D\n"
                "1,Thủ đô của Việt Nam là gì?,Hà Nội,Huế,Đà Nẵng,Cần Thơ\n",
                encoding="utf-8",
            )

            def fake_raw_chat(prompt, **kwargs):
                self.assertIn(KNOWLEDGE_MARKER, prompt)
                return "Tôi không biết."

            def fake_agent(prompt):
                self.assertIn(SINGLE_RETRY_MARKER, prompt)
                return "qid,answer\n1,C\n"

            with patch.object(main, "agent", fake_agent), patch.object(main, "raw_chat", fake_raw_chat):
                main.run(input_path=input_path, output_path=output_path, search_client=StaticWebSearch({}))

            with output_path.open(newline="", encoding="utf-8") as f:
                self.assertEqual(list(csv.DictReader(f)), [{"qid": "1", "answer": "C"}])
            with output_path.with_name("pred_audit.csv").open(newline="", encoding="utf-8") as f:
                self.assertEqual(
                    list(csv.DictReader(f)),
                    [{"qid": "1", "answer": "C", "confidence": "0.55", "needs_search": "false", "search_used": "false", "answer_source": "single_retry"}],
                )

    def test_run_marks_missing_when_workflow_v2_and_single_retry_both_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            input_path = tmp_path / "public_test.csv"
            output_path = tmp_path / "pred.csv"
            input_path.write_text(
                "qid,question,A,B,C,D\n"
                "1,Thủ đô của Việt Nam là gì?,Hà Nội,Huế,Đà Nẵng,Cần Thơ\n",
                encoding="utf-8",
            )

            with patch.object(main, "agent", return_value="Tôi không biết."), patch.object(main, "raw_chat", return_value="Tôi không biết."):
                main.run(input_path=input_path, output_path=output_path, search_client=StaticWebSearch({}))

            with output_path.open(newline="", encoding="utf-8") as f:
                self.assertEqual(list(csv.DictReader(f)), [{"qid": "1", "answer": "N/A"}])
            with output_path.with_name("pred_audit.csv").open(newline="", encoding="utf-8") as f:
                self.assertEqual(
                    list(csv.DictReader(f)),
                    [{"qid": "1", "answer": "N/A", "confidence": "0.00", "needs_search": "true", "search_used": "false", "answer_source": "missing"}],
                )

    def test_run_searches_volatile_question_after_workflow_v2_answer(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            input_path = tmp_path / "public_test.csv"
            output_path = tmp_path / "pred.csv"
            input_path.write_text(
                "qid,question,A,B,C,D\n"
                "1,CEO hiện nay là ai?,a,b,c,d\n",
                encoding="utf-8",
            )
            search = StaticWebSearch({"CEO hiện nay là ai?": "Nguồn web: đáp án là C."})

            def fake_raw_chat(prompt, **kwargs):
                self.assertIn(KNOWLEDGE_MARKER, prompt)
                return "ANSWER: A\nCONFIDENCE: 0.9"

            def fake_agent(prompt):
                self.assertIn(SEARCH_CONTEXT_MARKER, prompt)
                return "qid,answer\n1,C\n"

            with patch.object(main, "agent", fake_agent), patch.object(main, "raw_chat", fake_raw_chat):
                main.run(input_path=input_path, output_path=output_path, search_client=search)

            with output_path.open(newline="", encoding="utf-8") as f:
                self.assertEqual(list(csv.DictReader(f)), [{"qid": "1", "answer": "C"}])
            with output_path.with_name("pred_audit.csv").open(newline="", encoding="utf-8") as f:
                self.assertEqual(
                    list(csv.DictReader(f)),
                    [{"qid": "1", "answer": "C", "confidence": "0.40", "needs_search": "true", "search_used": "true", "answer_source": "search"}],
                )

    def test_run_keeps_existing_answer_when_search_reanswer_is_na(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            input_path = tmp_path / "public_test.csv"
            output_path = tmp_path / "pred.csv"
            input_path.write_text(
                "qid,question,A,B,C,D\n"
                "2,CEO hiện nay là ai?,a,b,c,d\n",
                encoding="utf-8",
            )
            search = StaticWebSearch({"CEO hiện nay là ai?": "Nguồn web không đủ để chọn đáp án."})

            def fake_raw_chat(prompt, **kwargs):
                self.assertIn(KNOWLEDGE_MARKER, prompt)
                return "ANSWER: A\nCONFIDENCE: 0.9"

            def fake_agent(prompt):
                self.assertIn(SEARCH_CONTEXT_MARKER, prompt)
                return "qid,answer\n2,N/A\n"

            with patch.object(main, "agent", fake_agent), patch.object(main, "raw_chat", fake_raw_chat):
                main.run(input_path=input_path, output_path=output_path, search_client=search)

            with output_path.open(newline="", encoding="utf-8") as f:
                self.assertEqual(list(csv.DictReader(f)), [{"qid": "2", "answer": "A"}])
            with output_path.with_name("pred_audit.csv").open(newline="", encoding="utf-8") as f:
                self.assertEqual(
                    list(csv.DictReader(f)),
                    [{"qid": "2", "answer": "A", "confidence": "0.97", "needs_search": "true", "search_used": "true", "answer_source": "workflow_v2:knowledge"}],
                )

    def test_run_can_print_progress_to_stderr(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            input_path = tmp_path / "public_test.csv"
            output_path = tmp_path / "pred.csv"
            input_path.write_text(
                "qid,question,A,B,C,D\n"
                "1,Tính 1 + 1,1,2,3,4\n"
                "2,Tính 2 + 2,3,4,5,6\n"
                "3,Tính 3 + 3,5,6,7,8\n",
                encoding="utf-8",
            )

            stderr = io.StringIO()
            with patch.object(main, "agent", _refuse_agent), patch.object(main, "raw_chat", _refuse_raw_chat), contextlib.redirect_stderr(stderr):
                main.run(
                    input_path=input_path,
                    output_path=output_path,
                    search_client=StaticWebSearch({}),
                    show_progress=True,
                )

            progress_output = stderr.getvalue()
            self.assertIn("Progress:", progress_output)
            self.assertIn("3/3 (100%)", progress_output)

    def test_run_reads_utf8_sig_csv_with_bom_header(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            input_path = tmp_path / "public_test.csv"
            output_path = tmp_path / "pred.csv"
            input_path.write_text(
                "﻿qid,question,A,B,C,D\n"
                "1,Tính 1 + 1,1,2,3,4\n",
                encoding="utf-8",
            )

            with patch.object(main, "agent", _refuse_agent), patch.object(main, "raw_chat", _refuse_raw_chat):
                main.run(input_path=input_path, output_path=output_path, search_client=StaticWebSearch({}))

            with output_path.open(newline="", encoding="utf-8") as f:
                self.assertEqual(list(csv.DictReader(f)), [{"qid": "1", "answer": "B"}])

    def test_run_reads_json_input_file_with_choices_array(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            input_path = tmp_path / "public_test.json"
            output_path = tmp_path / "pred.csv"
            input_path.write_text(
                json.dumps(
                    [{"qid": "test_0001", "question": "Tính 1 + 1", "choices": ["1", "2", "3", "4"]}],
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            with patch.object(main, "agent", _refuse_agent), patch.object(main, "raw_chat", _refuse_raw_chat):
                main.run(input_path=input_path, output_path=output_path, search_client=StaticWebSearch({}))

            with output_path.open(newline="", encoding="utf-8") as f:
                self.assertEqual(list(csv.DictReader(f)), [{"qid": "test_0001", "answer": "B"}])

    def test_rows_to_prompt_renders_json_array_with_choices(self):
        row = {"qid": "1", "question": "Câu hỏi có, dấu phẩy?", "A": "X", "B": "Y"}

        prompt = main.rows_to_prompt([row])

        self.assertEqual(
            json.loads(prompt),
            [{"qid": "1", "question": "Câu hỏi có, dấu phẩy?", "choices": ["X", "Y"]}],
        )


if __name__ == "__main__":
    unittest.main()
