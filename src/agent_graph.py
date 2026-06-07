import sys
import io

# Cấu hình encoding UTF-8 cho Windows console để tránh UnicodeEncodeError
if sys.platform.startswith("win"):
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')


import json
from typing import TypedDict
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_groq import ChatGroq
import os
from dotenv import load_dotenv
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage, AIMessage
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

# Ràng buộc công cụ RAG với LLM
llm_with_tools = llm.bind_tools([search_rag_database])

class AgentState(TypedDict):
    question: str
    messages: list
    reasoning: str
    answer: str

def agent_node(state: AgentState):
    print(">> [Agent] Dang xu ly cau hoi...")
    messages = state.get("messages", [])
    if not messages:
        system_instructions = (
            SYSTEM_COT_PROMPT + "\n\n"
            "ADDITIONAL RULES FOR RESPONDING:\n"
            "1. TOOLS: You have a tool called 'search_rag_database' to query search context from competition documents.\n"
            "2. GENERAL KNOWLEDGE: If the question is about general common knowledge (e.g. basic math 1+1, common science, general trivia...) and is not specific to the competition documents, "
            "you DO NOT need to call the RAG tool. Reason using your internal knowledge and respond directly.\n"
            "3. FALLBACK REASONING: If the question is general knowledge or if the RAG search returns no relevant results, "
            "you ARE ALLOWED to use your own internal knowledge to solve the question (you are not constrained by the 'only use information from the document' rule in this case)."
        )
        messages = [
            SystemMessage(content=system_instructions),
            HumanMessage(content=state["question"])
        ]
    
    response = llm_with_tools.invoke(messages)
    return {"messages": messages + [response]}

def tool_node(state: AgentState):
    print(">> [Tool] LLM yeu cau goi tool RAG Database...")
    last_message = state["messages"][-1]
    messages = state["messages"]
    new_messages = []
    
    for tool_call in last_message.tool_calls:
        if tool_call["name"] == "search_rag_database":
            query = tool_call["args"].get("query", "")
            print(f"   -> Dang truy van RAG voi tu khoa: '{query}'")
            try:
                result = search_rag_database.invoke({"query": query})
            except Exception as e:
                result = f"Loi khi truy van database: {e}"
            
            new_messages.append(
                ToolMessage(
                    content=result,
                    tool_call_id=tool_call["id"]
                )
            )
            
    return {"messages": messages + new_messages}

def should_continue(state: AgentState):
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        return "call_tool"
    return "parse_answer"

def parse_answer_node(state: AgentState):
    print(">> [Parse] Dang trich xuat dap an cuoi cung...")
    last_message = state["messages"][-1]
    response_content = last_message.content.strip()
    
    data = None
    try:
        data = json.loads(response_content)
    except json.JSONDecodeError:
        clean_content = response_content
        if clean_content.startswith("```json"):
            clean_content = clean_content[7:]
        if clean_content.endswith("```"):
            clean_content = clean_content[:-3]
        clean_content = clean_content.strip()
        
        # Thử sửa lỗi JSON bị cắt cụt (thiếu dấu ngoặc đóng)
        if not clean_content.endswith("}"):
            try:
                data = json.loads(clean_content + "}")
            except Exception:
                try:
                    data = json.loads(clean_content + '"}')
                except Exception:
                    data = None
                    
        if data is None:
            try:
                data = json.loads(clean_content)
            except Exception:
                # Trích xuất bằng regex nếu parse lỗi hoàn toàn
                import re
                answer_match = re.search(r'"answer"\s*:\s*"([A-D])"', clean_content, re.IGNORECASE)
                reasoning_match = re.search(r'"reasoning"\s*:\s*"([^"]+)"', clean_content)
                data = {
                    "reasoning": reasoning_match.group(1) if reasoning_match else f"Khong the parse JSON. Content thiet lap: {response_content}",
                    "answer": answer_match.group(1) if answer_match else "N/A"
                }
            
    raw_answer = data.get("answer", "A") if data else "A"
    clean_answer = str(raw_answer).strip().upper()
    
    # Tìm chữ cái A, B, C, hoặc D xuất hiện trong chuỗi đáp án của LLM
    import re
    match = re.search(r'([A-D])', clean_answer)
    if match:
        final_answer = match.group(1)
    else:
        # Mặc định fallback là A nếu hoàn toàn không có thông tin hợp lệ
        final_answer = "A"
            
    return {
        "reasoning": data.get("reasoning", "Không tìm thấy lý do suy luận.") if data else "Không thể phân tích lập luận.",
        "answer": final_answer
    }

workflow = StateGraph(AgentState)
workflow.add_node("Agent", agent_node)
workflow.add_node("Tool", tool_node)
workflow.add_node("Parse", parse_answer_node)

workflow.set_entry_point("Agent")
workflow.add_conditional_edges(
    "Agent",
    should_continue,
    {
        "call_tool": "Tool",
        "parse_answer": "Parse"
    }
)
workflow.add_edge("Tool", "Agent")
workflow.add_edge("Parse", END)

app_graph = workflow.compile()