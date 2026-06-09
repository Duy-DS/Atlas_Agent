import os
import json
import asyncio
import re
from typing import TypedDict
from dotenv import load_dotenv
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from src.system_prompt import SYSTEM_COT_PROMPT

# Load các biến môi trường (như GROQ_API_KEY) từ file .env
load_dotenv()
groq_api_key = os.getenv("GROQ_API_KEY", "")

# Khởi tạo LLM sử dụng Groq API thông qua ChatOpenAI format
llm = ChatOpenAI(
    model="llama-3.1-8b-instant", # Sử dụng model siêu nhanh của Groq
    api_key=groq_api_key, 
    base_url="https://api.groq.com/openai/v1",
    temperature=0.1
)

# Đọc sẵn dữ liệu từ file để làm ngữ cảnh thay vì dùng RAG
KNOWLEDGE_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "mock_knowledge.txt")
try:
    with open(KNOWLEDGE_PATH, "r", encoding="utf-8") as f:
        KNOWLEDGE_CONTEXT = f.read()
except FileNotFoundError:
    KNOWLEDGE_CONTEXT = "Không tìm thấy dữ liệu ngữ cảnh."

class AgentState(TypedDict):
    question: str
    context: str
    reasoning: str
    answer: str

async def retrieve_node(state: AgentState):
    # Trả về trực tiếp ngữ cảnh đã đọc từ file
    return {"context": KNOWLEDGE_CONTEXT}

# Semaphore giới hạn số luồng gọi LLM đồng thời. 
# Điều này cực kỳ quan trọng không chỉ cho Groq API mà còn để BẢO VỆ LLM tự host (vLLM) của team mày không bị sập (Out of Memory) khi nhận 80 request cùng lúc.
concurrency_limit = asyncio.Semaphore(5)

async def reasoning_node(state: AgentState):
    # Thiết lập prompt với system message và câu hỏi của user
    system_msg = SystemMessage(content=SYSTEM_COT_PROMPT)
    user_prompt = f"Ngữ cảnh tài liệu:\n{state.get('context', '')}\n\nCâu hỏi:\n{state['question']}"
    human_msg = HumanMessage(content=user_prompt)
    
    # Khóa luồng, tối đa 5 câu hỏi được gọi LLM cùng lúc
    async with concurrency_limit:
        max_retries = 10
        for attempt in range(max_retries):
            try:
                # Gọi API bất đồng bộ tới Groq/vLLM
                response = await llm.ainvoke([system_msg, human_msg])
                content = response.content
                
                # Bóc tách JSON từ kết quả trả về của LLM (phòng trường hợp có markdown ```json)
                match = re.search(r'\{.*\}', content, re.DOTALL)
                if match:
                    parsed = json.loads(match.group(0))
                else:
                    parsed = json.loads(content)
                    
                return {
                    "reasoning": parsed.get("reasoning", "Không trích xuất được lý do"),
                    "answer": parsed.get("answer", "B")
                }
            except Exception as e:
                err_msg = str(e)
                # Xử lý lỗi Rate Limit (429) của API hoặc Too Many Requests
                if "429" in err_msg or "rate limit" in err_msg.lower():
                    wait_time = 4 + attempt * 2 # Exponential backoff nhẹ
                    print(f"Rate limit hit! Đợi {wait_time}s rồi thử lại... (Lần {attempt+1}/{max_retries})")
                    await asyncio.sleep(wait_time)
                else:
                    print(f"Lỗi hệ thống khi gọi LLM: {e}")
                    return {
                        "reasoning": f"Lỗi parse/hệ thống: {e}",
                        "answer": "B"
                    }
                    
        return {
            "reasoning": "Thất bại do Rate Limit quá nhiều lần.",
            "answer": "B"
        }

workflow = StateGraph(AgentState)
workflow.add_node("Retrieve", retrieve_node)
workflow.add_node("Reason", reasoning_node)
workflow.set_entry_point("Retrieve")
workflow.add_edge("Retrieve", "Reason")
workflow.add_edge("Reason", END)

app_graph = workflow.compile()