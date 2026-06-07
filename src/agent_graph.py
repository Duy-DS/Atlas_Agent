import json
from typing import TypedDict
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_groq import ChatGroq
import os
from dotenv import load_dotenv
from src.system_prompt import SYSTEM_COT_PROMPT
from src.rag_engine import search_rag_database

load_dotenv()

# Tự động chọn Groq nếu có API Key, ngược lại fallback về local LLM (vLLM/Ollama)
if os.getenv("GROQ_API_KEY"):
    print("[*] Đang cấu hình LLM sử dụng Groq API...")
    llm = ChatGroq(
        model="llama-3.1-8b-instant",  # Hoặc model khác tùy bạn chọn
        groq_api_key=os.getenv("GROQ_API_KEY"),
        temperature=0.1
    )
else:
    print("[*] Không tìm thấy GROQ_API_KEY trong file .env, dùng local LLM...")
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
    print(">> [Retrieve] Dang truy van RAG Database...")
    try:
        context = search_rag_database.invoke({"query": state["question"]})
    except Exception:
        context = search_rag_database(state["question"])
    return {"context": context}

def reasoning_node(state: AgentState):
    print(">> [Reason] Dang goi LLM de lap luan...")
    messages = [
        {"role": "system", "content": SYSTEM_COT_PROMPT},
        {"role": "user", "content": f"<Ngữ cảnh tài liệu>\n{state['context']}\n\nCâu hỏi: {state['question']}"}
    ]
    
    try:
        response = llm.invoke(messages)
        response_content = response.content.strip()
        
        # Thử parse JSON từ phản hồi của LLM
        try:
            data = json.loads(response_content)
        except json.JSONDecodeError:
            # Xử lý trường hợp LLM bọc JSON trong Markdown block (```json ... ```)
            clean_content = response_content
            if clean_content.startswith("```json"):
                clean_content = clean_content[7:]
            if clean_content.endswith("```"):
                clean_content = clean_content[:-3]
            data = json.loads(clean_content.strip())
            
        reasoning = data.get("reasoning", "Không tìm thấy lý do suy luận.")
        answer = data.get("answer", "N/A")
    except Exception as e:
        print(f"[!] Loi khi goi LLM hoac parse JSON: {e}")
        reasoning = f"Loi xay ra trong qua trinh goi mo hinh: {str(e)}"
        answer = "N/A"
        
    return {
        "reasoning": reasoning,
        "answer": answer
    }


workflow = StateGraph(AgentState)
workflow.add_node("Retrieve", retrieve_node)
workflow.add_node("Reason", reasoning_node)
workflow.set_entry_point("Retrieve")
workflow.add_edge("Retrieve", "Reason")
workflow.add_edge("Reason", END)

app_graph = workflow.compile()