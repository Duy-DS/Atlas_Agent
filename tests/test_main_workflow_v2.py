import csv
import sys
import types
import tempfile
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


def test_run_uses_workflow_v2_for_calculation_rows():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        input_path = tmp_path / "public_test.csv"
        output_path = tmp_path / "pred.csv"
        input_path.write_text(
            "qid,question,A,B,C,D\n"
            "1,Tính 2 + 2,3,4,5,6\n",
            encoding="utf-8",
        )

        with patch.object(main, "agent", return_value="qid,answer\n1,A\n"):
            main.run(input_path=input_path, output_path=output_path, search_client=StaticWebSearch({}))

        with output_path.open(newline="", encoding="utf-8") as f:
            assert list(csv.DictReader(f)) == [{"qid": "1", "answer": "B"}]

        with output_path.with_name("pred_audit.csv").open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        assert rows[0]["confidence"] == "0.95"
        assert rows[0]["answer_source"] == "workflow_v2:calculation"


def test_run_preserves_batch_for_non_workflow_fallback_when_pipeline_returns_none():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        input_path = tmp_path / "public_test.csv"
        output_path = tmp_path / "pred.csv"
        input_path.write_text(
            "qid,question,A,B,C,D\n"
            "1,one,a,b,c,d\n",
            encoding="utf-8",
        )

        with patch.object(main, "agent", return_value="qid,answer\n1,C\n"), patch.object(main, "raw_chat", return_value="qid,answer\n1,C\n"):
            main.run(input_path=input_path, output_path=output_path, search_client=StaticWebSearch({}))

        with output_path.open(newline="", encoding="utf-8") as f:
            assert list(csv.DictReader(f)) == [{"qid": "1", "answer": "C"}]
