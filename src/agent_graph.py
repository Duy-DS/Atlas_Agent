import os
import json
import asyncio
import re
from typing import TypedDict
from dotenv import load_dotenv
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from duckduckgo_search import DDGS
import wikipedia
from langchain_experimental.utilities import PythonREPL
from src.system_prompt import SYSTEM_COT_PROMPT

wikipedia.set_lang("vi")
python_repl = PythonREPL()

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
    need_search: str

ROUTER_PROMPT = """Bạn là một chuyên gia phân loại câu hỏi.
Hãy phân loại câu hỏi của người dùng vào 1 trong 4 nhóm sau:
- PYTHON: Nếu là bài toán, phép tính, giải phương trình, logic tính toán, xác suất, quy luật dãy số.
- WIKI: Nếu là câu hỏi về lịch sử, địa lý, thông tin nhân vật, định nghĩa học thuật cố định.
- WEB: Nếu là câu hỏi về sự kiện mới nhất, tin tức, giá cả, thời tiết, kết quả thể thao gần đây (ví dụ Euro 2024).
- NO: Nếu là câu hỏi kiến thức phổ thông đơn giản, văn phạm cơ bản, hoặc bạn đã quá chắc chắn.

CHỈ TRẢ VỀ ĐÚNG 1 TỪ "PYTHON", "WIKI", "WEB", HOẶC "NO". KHÔNG ĐƯỢC CÓ CHỮ NÀO KHÁC.
"""

async def router_node(state: AgentState):
    system_msg = SystemMessage(content=ROUTER_PROMPT)
    human_msg = HumanMessage(content=state["question"])
    try:
        response = await llm.ainvoke([system_msg, human_msg])
        decision = response.content.strip().upper()
        
        q_preview = state["question"].split('\n')[0][:50]
        
        if "PYTHON" in decision:
            print(f"[ROUTER] '{q_preview}...' -> GOI PYTHON REPL")
            return {"need_search": "PYTHON"}
        elif "WIKI" in decision:
            print(f"[ROUTER] '{q_preview}...' -> GOI WIKIPEDIA")
            return {"need_search": "WIKI"}
        elif "WEB" in decision:
            print(f"[ROUTER] '{q_preview}...' -> GOI WEB SEARCH")
            return {"need_search": "WEB"}
        else:
            print(f"[ROUTER] '{q_preview}...' -> ĐI THẲNG REASONING")
            return {"need_search": "NO"}
    except Exception as e:
        print(f"Lỗi khi chạy router: {e}")
        return {"need_search": "NO"}

async def retrieve_node(state: AgentState):
    # Trả về trực tiếp ngữ cảnh đã đọc từ file
    return {"context": KNOWLEDGE_CONTEXT}

def my_web_search(query: str) -> str:
    try:
        with DDGS() as ddgs:
            results = ddgs.text(query, max_results=3)
            if results:
                return "\n".join([f"- {r.get('title', '')}: {r.get('body', '')}" for r in results])
            return "Không tìm thấy kết quả phù hợp."
    except Exception as e:
        return f"Lỗi API: {e}"

async def web_search_node(state: AgentState):
    question = state.get("question", "")
    try:
        search_results = my_web_search(question)
        current_context = state.get("context", "")
        new_context = f"{current_context}\n\n--- THÔNG TIN TỪ WEB SEARCH ---\n{search_results}"
        return {"context": new_context}
    except Exception as e:
        return {"context": state.get("context", "")}

def my_wiki_search(query: str) -> str:
    try:
        return wikipedia.summary(query, sentences=3)
    except wikipedia.exceptions.DisambiguationError as e:
        return f"Wiki có nhiều kết quả, ví dụ: {e.options[:5]}"
    except Exception as e:
        return f"Lỗi Wiki: {e}"

async def wiki_search_node(state: AgentState):
    question = state.get("question", "")
    system_msg = SystemMessage(content="Trích xuất DUY NHẤT 1 TỪ KHÓA ngắn gọn từ câu hỏi để tìm Wikipedia (VD: 'Chiến tranh thế giới thứ hai', 'Định lý Pythagoras'). Không viết gì thêm.")
    try:
        response = await llm.ainvoke([system_msg, HumanMessage(content=question)])
        query = response.content.strip()
        search_results = my_wiki_search(query)
        current_context = state.get("context", "")
        new_context = f"{current_context}\n\n--- KẾT QUẢ WIKIPEDIA ---\nTừ khóa: {query}\nThông tin:\n{search_results}"
        return {"context": new_context}
    except Exception as e:
        return {"context": state.get("context", "")}

async def python_repl_node(state: AgentState):
    question = state.get("question", "")
    system_msg = SystemMessage(content="Bạn là lập trình viên Python. Viết MỘT ĐOẠN CODE PYTHON ngắn gọn để tính toán/giải bài toán của người dùng. CHỈ in ra (print) kết quả cuối cùng. KHÔNG DÙNG MARKDOWN (```python). CHỈ VIẾT CODE.")
    try:
        response = await llm.ainvoke([system_msg, HumanMessage(content=question)])
        code = response.content.strip()
        code = re.sub(r"^```python\n|```$", "", code, flags=re.MULTILINE).strip()
        
        result = python_repl.run(code)
        current_context = state.get("context", "")
        new_context = f"{current_context}\n\n--- KẾT QUẢ PYTHON REPL ---\nCode chạy:\n{code}\nOutput:\n{result}"
        return {"context": new_context}
    except Exception as e:
        return {"context": state.get("context", "")}

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

def should_search(state: AgentState) -> str:
    ans = state.get("need_search", "NO")
    if ans == "PYTHON":
        return "PythonREPL"
    elif ans == "WIKI":
        return "WikiSearch"
    elif ans == "WEB":
        return "WebSearch"
    return "Reason"

workflow = StateGraph(AgentState)
workflow.add_node("Retrieve", retrieve_node)
workflow.add_node("Router", router_node)
workflow.add_node("WebSearch", web_search_node)
workflow.add_node("WikiSearch", wiki_search_node)
workflow.add_node("PythonREPL", python_repl_node)
workflow.add_node("Reason", reasoning_node)

workflow.set_entry_point("Retrieve")
workflow.add_edge("Retrieve", "Router")

workflow.add_conditional_edges(
    "Router",
    should_search,
    {
        "WebSearch": "WebSearch",
        "WikiSearch": "WikiSearch",
        "PythonREPL": "PythonREPL",
        "Reason": "Reason"
    }
)

workflow.add_edge("WebSearch", "Reason")
workflow.add_edge("WikiSearch", "Reason")
workflow.add_edge("PythonREPL", "Reason")
workflow.add_edge("Reason", END)

app_graph = workflow.compile()