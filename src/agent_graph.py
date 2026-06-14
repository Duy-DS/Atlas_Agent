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

# Đọc cấu hình từ biến môi trường hoặc dùng fallback mặc định sang Groq API
llm_base_url = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")
llm_model_name = os.getenv("LLM_MODEL_NAME", "llama-3.1-8b-instant")
llm_api_key = os.getenv("LLM_API_KEY", groq_api_key)

print(f"[*] Cấu hình LLM: Base URL={llm_base_url} | Model={llm_model_name}")

# Khởi tạo LLM tương thích chuẩn OpenAI
llm = ChatOpenAI(
    model=llm_model_name,
    api_key=llm_api_key, 
    base_url=llm_base_url,
    temperature=0.1
)

# Semaphore giới hạn số luồng gọi LLM đồng thời để bảo vệ Ollama/LLM khỏi quá tải
is_gpu = False
try:
    import torch
    if torch.cuda.is_available():
        is_gpu = True
except Exception:
    pass

if "NVIDIA_VISIBLE_DEVICES" in os.environ or "CUDA_VISIBLE_DEVICES" in os.environ:
    is_gpu = True

is_local_ollama = any(host in llm_base_url for host in ["127.0.0.1", "localhost", "ollama"])

default_concurrency = "5"
if is_local_ollama and not is_gpu:
    # Nếu chạy local Ollama trên CPU, hạ concurrency xuống 1 tránh phân mảnh CPU làm nghẽn tiến trình
    default_concurrency = "1"
elif is_gpu:
    # Nếu có GPU, tăng concurrency mặc định lên 8 để xử lý batch nhanh hơn
    default_concurrency = "8"

max_concurrency = int(os.getenv("LLM_CONCURRENCY_LIMIT", default_concurrency))
print(f"[*] Chế độ phần cứng: {'GPU' if is_gpu else 'CPU'} | Giới hạn số luồng LLM đồng thời: {max_concurrency}")
concurrency_limit = asyncio.Semaphore(max_concurrency)

async def run_python_code_safe(code: str, timeout: float = 3.0) -> str:
    """Thực thi mã Python trong tiến trình con độc lập để tránh treo ứng dụng khi lặp vô hạn."""
    import tempfile
    import sys
    
    with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w", encoding="utf-8") as temp_file:
        temp_file.write(code)
        temp_path = temp_file.name
        
    try:
        proc = await asyncio.create_subprocess_exec(
            sys.executable, temp_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            if proc.returncode == 0:
                return stdout.decode("utf-8", errors="replace").strip()
            else:
                return f"Lỗi thực thi code: {stderr.decode('utf-8', errors='replace').strip()}"
        except asyncio.TimeoutError:
            try:
                proc.kill()
            except Exception:
                pass
            return f"Lỗi: Code chạy quá thời gian giới hạn ({timeout}s)."
    except Exception as e:
        return f"Lỗi chạy code: {e}"
    finally:
        try:
            os.remove(temp_path)
        except Exception:
            pass

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
    search_query: str

ROUTER_PROMPT = """Bạn là một chuyên gia phân loại câu hỏi trắc nghiệm và trích xuất từ khóa tìm kiếm.
Hãy phân tích câu hỏi của người dùng và trả về kết quả dưới dạng một JSON duy nhất có cấu trúc như sau:
{
    "route": "PYTHON" | "WIKI" | "WEB" | "NO",
    "search_query": "Từ khóa tìm kiếm ngắn gọn (VD: 'AI Agent', 'Nguyễn Du', 'Euro 2024'). BẮT BUỘC phải điền nếu chọn route WIKI hoặc WEB. Nếu chọn NO hoặc PYTHON thì để trống."
}

Quy tắc phân loại:
- PYTHON: Nếu câu hỏi yêu cầu giải toán, tính toán số học, logic, xác suất, quy luật dãy số.
- WIKI: CHỈ KHI câu hỏi chứa thông tin lịch sử, nhân vật lịch sử, địa lý, định nghĩa học thuật chuyên sâu và cụ thể mà bạn hoàn toàn không nhớ rõ số liệu/chi tiết.
- WEB: CHỈ KHI câu hỏi liên quan đến sự kiện mới nhất, thời sự, giá cả thị trường hiện tại, kết quả thể thao gần đây (từ năm 2025 trở đi).
- NO: Đối với tất cả câu hỏi kiến thức phổ thông, lịch sử/địa lý/văn học cơ bản (như đỉnh núi cao nhất, năm chiến thắng Điện Biên Phủ, tác giả Truyện Kiều...), hoặc các kiến thức bạn chắc chắn biết.

CHỈ TRẢ VỀ ĐÚNG MỘT OBJECT JSON, KHÔNG THÊM BẤT KỲ CHỮ NÀO KHÁC.
"""

async def router_node(state: AgentState):
    system_msg = SystemMessage(content=ROUTER_PROMPT)
    human_msg = HumanMessage(content=state["question"])
    decision = "NO"
    search_query = ""
    content = ""
    
    max_retries = 10
    for attempt in range(max_retries):
        try:
            async with concurrency_limit:
                response = await llm.ainvoke([system_msg, human_msg], max_tokens=120)
            content = response.content.strip()
            
            # Bóc tách JSON từ kết quả trả về của LLM
            match = re.search(r'\{.*\}', content, re.DOTALL)
            if match:
                parsed = json.loads(match.group(0))
            else:
                parsed = json.loads(content)
                
            decision = parsed.get("route", "NO").upper()
            search_query = parsed.get("search_query", "").strip()
            break
        except Exception as e:
            err_msg = str(e)
            if "429" in err_msg or "rate limit" in err_msg.lower():
                wait_time = 4 + attempt * 2
                print(f"Rate limit hit in Router! Đợi {wait_time}s rồi thử lại... (Lần {attempt+1}/{max_retries})")
                await asyncio.sleep(wait_time)
            else:
                # Fallback bằng regex nếu JSON lỗi cú pháp nhẹ từ LLM nhỏ
                route_match = re.search(r'"route"\s*:\s*"(.*?)"', content, re.IGNORECASE)
                query_match = re.search(r'"search_query"\s*:\s*"(.*?)"', content, re.IGNORECASE)
                if route_match:
                    decision = route_match.group(1).upper()
                    if query_match:
                        search_query = query_match.group(1)
                    break
                    
                print(f"Lỗi khi chạy router (Lần {attempt+1}/{max_retries}): {e}")
                if attempt == max_retries - 1:
                    decision = "NO"
                    search_query = ""
                else:
                    await asyncio.sleep(1)
            
    q_preview = state["question"].split('\n')[0][:50]
    
    if "PYTHON" in decision:
        print(f"[ROUTER] '{q_preview}...' -> GOI PYTHON REPL")
        return {"need_search": "PYTHON", "search_query": search_query}
    elif "WIKI" in decision:
        print(f"[ROUTER] '{q_preview}...' -> GOI WIKIPEDIA (Query: {search_query})")
        return {"need_search": "WIKI", "search_query": search_query}
    elif "WEB" in decision:
        print(f"[ROUTER] '{q_preview}...' -> GOI WEB SEARCH (Query: {search_query})")
        return {"need_search": "WEB", "search_query": search_query}
    else:
        print(f"[ROUTER] '{q_preview}...' -> ĐI THẲNG REASONING")
        return {"need_search": "NO", "search_query": ""}

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
    query = state.get("search_query", "").strip()
    if not query:
        query = question
    try:
        # Giới hạn thời gian chạy web search tối đa 5 giây tránh đơ luồng mạng
        search_results = await asyncio.wait_for(
            asyncio.to_thread(my_web_search, query),
            timeout=5.0
        )
        current_context = state.get("context", "")
        new_context = f"{current_context}\n\n--- THÔNG TIN TỪ WEB SEARCH ---\n{search_results}"
        return {"context": new_context}
    except Exception as e:
        print(f"Lỗi/Timeout Web Search ({query}): {e}")
        return {"context": state.get("context", "")}

def my_wiki_search(query: str) -> str:
    try:
        # Tìm kiếm trước để lấy bài viết sát nghĩa nhất, tránh DisambiguationError trực tiếp
        search_results = wikipedia.search(query, results=1)
        if search_results:
            return wikipedia.summary(search_results[0], sentences=2)
        return "Không tìm thấy trang Wikipedia phù hợp."
    except wikipedia.exceptions.DisambiguationError as e:
        if e.options:
            try:
                return wikipedia.summary(e.options[0], sentences=2)
            except Exception:
                pass
        return f"Wiki có nhiều kết quả, ví dụ: {e.options[:5]}"
    except Exception as e:
        return f"Lỗi Wiki: {e}"

async def wiki_search_node(state: AgentState):
    question = state.get("question", "")
    query = state.get("search_query", "").strip()
    if not query:
        query = question
    try:
        # Giới hạn thời gian chạy wiki search tối đa 5 giây tránh đơ luồng mạng
        search_results = await asyncio.wait_for(
            asyncio.to_thread(my_wiki_search, query),
            timeout=5.0
        )
        current_context = state.get("context", "")
        new_context = f"{current_context}\n\n--- KẾT QUẢ WIKIPEDIA ---\nTừ khóa: {query}\nThông tin:\n{search_results}"
        return {"context": new_context}
    except Exception as e:
        print(f"Lỗi/Timeout Wiki Search ({query}): {e}")
        return {"context": state.get("context", "")}

async def python_repl_node(state: AgentState):
    question = state.get("question", "")
    system_msg = SystemMessage(content="Bạn là lập trình viên Python. Viết MỘT ĐOẠN CODE PYTHON ngắn gọn để tính toán/giải bài toán của người dùng. CHỈ in ra (print) kết quả cuối cùng. KHÔNG DÙNG MARKDOWN (```python). CHỈ VIẾT CODE.")
    
    code = ""
    max_retries = 10
    for attempt in range(max_retries):
        try:
            async with concurrency_limit:
                response = await llm.ainvoke([system_msg, HumanMessage(content=question)], max_tokens=250)
            code = response.content.strip()
            code = re.sub(r"^```python\n|```$", "", code, flags=re.MULTILINE).strip()
            break
        except Exception as e:
            err_msg = str(e)
            if "429" in err_msg or "rate limit" in err_msg.lower():
                wait_time = 4 + attempt * 2
                print(f"Rate limit hit in Python Code Gen! Đợi {wait_time}s rồi thử lại... (Lần {attempt+1}/{max_retries})")
                await asyncio.sleep(wait_time)
            else:
                print(f"Lỗi gọi LLM tạo code (Lần {attempt+1}/{max_retries}): {e}")
                if attempt == max_retries - 1:
                    return {"context": state.get("context", "")}
                await asyncio.sleep(1)
                
    if not code:
        return {"context": state.get("context", "")}
        
    try:
        # Thực thi code Python trong subprocess an toàn với timeout 3 giây
        result = await run_python_code_safe(code, timeout=3.0)
        current_context = state.get("context", "")
        new_context = f"{current_context}\n\n--- KẾT QUẢ PYTHON REPL ---\nCode chạy:\n{code}\nOutput:\n{result}"
        return {"context": new_context}
    except Exception as e:
        print(f"Lỗi thực thi code Python: {e}")
        return {"context": state.get("context", "")}

# Semaphore giới hạn số luồng gọi LLM đồng thời. 
# Điều này cực kỳ quan trọng không chỉ cho Groq API mà còn để BẢO VỆ LLM tự host (vLLM) không bị sập (Out of Memory) khi nhận nhiều request cùng lúc.

async def reasoning_node(state: AgentState):
    # Thiết lập prompt với system message và câu hỏi của user
    system_msg = SystemMessage(content=SYSTEM_COT_PROMPT)
    user_prompt = f"Ngữ cảnh tài liệu:\n{state.get('context', '')}\n\nCâu hỏi:\n{state['question']}"
    human_msg = HumanMessage(content=user_prompt)
    
    # Khóa luồng, tối đa số lượng cấu hình được gọi LLM cùng lúc
    async with concurrency_limit:
        max_retries = 10
        for attempt in range(max_retries):
            content = ""
            try:
                # Gọi API bất đồng bộ tới Groq/vLLM, tối ưu tối đa 1000 tokens phản hồi
                response = await llm.ainvoke([system_msg, human_msg], max_tokens=1000)
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
                # Fallback parser bằng Regex nếu JSON bị lỗi cú pháp nhẹ (ví dụ lỗi ngoặc kép lồng nhau của mô hình nhỏ)
                if content:
                    try:
                        reasoning_match = re.search(r'"reasoning"\s*:\s*"(.*?)"', content, re.DOTALL)
                        answer_match = re.search(r'"answer"\s*:\s*"\s*([A-D])\s*"', content, re.IGNORECASE)
                        if reasoning_match or answer_match:
                            reasoning = reasoning_match.group(1) if reasoning_match else "Không trích xuất được lý do"
                            answer = answer_match.group(1).upper() if answer_match else "B"
                            return {
                                "reasoning": reasoning,
                                "answer": answer
                            }
                    except Exception:
                        pass
                
                err_msg = str(e)
                # Xử lý lỗi Rate Limit (429) của API hoặc Too Many Requests
                if "429" in err_msg or "rate limit" in err_msg.lower():
                    wait_time = 4 + attempt * 2 # Exponential backoff nhẹ
                    print(f"Rate limit hit in Reasoning! Đợi {wait_time}s rồi thử lại... (Lần {attempt+1}/{max_retries})")
                    await asyncio.sleep(wait_time)
                else:
                    print(f"Lỗi hệ thống khi gọi LLM (Reasoning): {e}")
                    if attempt == max_retries - 1:
                        return {
                            "reasoning": f"Lỗi parse/hệ thống: {e}",
                            "answer": "B"
                        }
                    await asyncio.sleep(1)
                    
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