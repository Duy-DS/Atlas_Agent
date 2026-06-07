import json
from typing import TypedDict
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from src.system_prompt import SYSTEM_COT_PROMPT
from src.rag_engine import search_rag_database

llm = ChatOpenAI(
    model="qwen-8b",
    api_key="sk-local-dev", 
    base_url="http://localhost:8000/v1",
    temperature=0.1
)

class AgentState(TypedDict):
    question: str
    context: str
    reasoning: str
    answer: str

def retrieve_node(state: AgentState):
    context = search_rag_database(state["question"])
    return {"context": context}

def reasoning_node(state: AgentState):
    print("DEBUG: Đang gọi LLM (Mock mode)...")
    # Thay vì gọi llm.invoke(), ta trả về kết quả giả
    return {
        "reasoning": "Đây là suy luận giả lập. Đồ thị của mày đã chạy thông luồng thành công!",
        "answer": "B"
    }   

workflow = StateGraph(AgentState)
workflow.add_node("Retrieve", retrieve_node)
workflow.add_node("Reason", reasoning_node)
workflow.set_entry_point("Retrieve")
workflow.add_edge("Retrieve", "Reason")
workflow.add_edge("Reason", END)

app_graph = workflow.compile()