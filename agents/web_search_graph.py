from __future__ import annotations

from typing import TypedDict

from langgraph.graph import END, StateGraph

from agents.search_router import should_search
from agents.web_search import WebSearchClient, build_search_tool


class WebSearchState(TypedDict, total=False):
    row: dict[str, str]
    answer: str
    needs_search: bool
    search_context: str
    final_answer: str


def build_web_search_graph(search_client: WebSearchClient, answer_with_context):
    search_tool = build_search_tool(search_client)

    def route_node(state: WebSearchState) -> WebSearchState:
        state["needs_search"] = should_search(state["row"], state.get("answer", "N/A"))
        return state

    def search_node(state: WebSearchState) -> WebSearchState:
        question = state["row"].get("question", "")
        state["search_context"] = search_tool.invoke(question)
        return state

    def answer_node(state: WebSearchState) -> WebSearchState:
        if state.get("search_context"):
            state["final_answer"] = answer_with_context(state["row"], state["search_context"])
        else:
            state["final_answer"] = state.get("answer", "N/A")
        return state

    def route_after_decision(state: WebSearchState) -> str:
        return "search" if state.get("needs_search") else "finalize"

    graph = StateGraph(WebSearchState)
    graph.add_node("route", route_node)
    graph.add_node("search", search_node)
    graph.add_node("finalize", answer_node)
    graph.set_entry_point("route")
    graph.add_conditional_edges("route", route_after_decision, {"search": "search", "finalize": "finalize"})
    graph.add_edge("search", "finalize")
    graph.add_edge("finalize", END)
    return graph.compile()
