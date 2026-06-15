import asyncio
import json
import os
import re
import tempfile
from typing import TypedDict

import wikipedia
from dotenv import load_dotenv
from duckduckgo_search import DDGS
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_experimental.utilities import PythonREPL
from langgraph.graph import END, StateGraph
from pydantic import BaseModel, Field
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI

from src.system_prompt import SYSTEM_COT_PROMPT

class ReasoningOutput(BaseModel):
    reasoning: str = Field(description="Lý luận chi tiết từng bước vì sao chọn đáp án này.")
    answer: str = Field(description="Chỉ ghi duy nhất 1 chữ cái in hoa: A, B, C, hoặc D.")

wikipedia.set_lang("vi")
python_repl = PythonREPL()

load_dotenv()

# Default to the OpenAI-compatible vLLM endpoint.
llm_base_url = os.getenv("LLM_BASE_URL", "http://127.0.0.1:8000/v1")
llm_model_name = os.getenv("LLM_MODEL_NAME", "qwen-hackathon")
llm_api_key = os.getenv("LLM_API_KEY", os.getenv("OPENAI_API_KEY", "EMPTY"))

print(f"[*] LLM config: Base URL={llm_base_url} | Model={llm_model_name}")

llm = ChatOllama(
    model=os.getenv("MODEL_NAME", "qwen3.5:4b"),
    temperature=0.1,
    format="json"
)

# Ép khuôn cấu trúc
structured_llm = llm.with_structured_output(ReasoningOutput)

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
    default_concurrency = "1"
elif is_gpu:
    default_concurrency = "8"

max_concurrency = int(os.getenv("LLM_CONCURRENCY_LIMIT", default_concurrency))
print(f"[*] Hardware mode: {'GPU' if is_gpu else 'CPU'} | LLM concurrency hint: {max_concurrency}")


async def run_python_code_safe(code: str, timeout: float = 3.0) -> str:
    """Run Python code in a subprocess with a timeout."""
    import sys

    with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w", encoding="utf-8") as temp_file:
        temp_file.write(code)
        temp_path = temp_file.name

    try:
        proc = await asyncio.create_subprocess_exec(
            sys.executable,
            temp_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            if proc.returncode == 0:
                return stdout.decode("utf-8", errors="replace").strip()
            return f"Code execution error: {stderr.decode('utf-8', errors='replace').strip()}"
        except asyncio.TimeoutError:
            try:
                proc.kill()
            except Exception:
                pass
            return f"Error: code execution exceeded the timeout limit ({timeout}s)."
    except Exception as e:
        return f"Python execution error: {e}"
    finally:
        try:
            os.remove(temp_path)
        except Exception:
            pass


class AgentState(TypedDict):
    question: str
    context: str
    reasoning: str
    answer: str
    need_search: str
    search_query: str


ROUTER_PROMPT = """You are a multiple-choice question routing expert.
Analyze the user's question and return exactly one JSON object with this structure:
{
    "route": "PYTHON" | "WIKI" | "WEB" | "NO",
    "search_query": "Short search keyword. Required for WIKI or WEB. Leave empty for NO or PYTHON."
}

Rules:
- PYTHON: numerical math, logic, probability, sequences.
- WIKI: historical facts, geography, definitions, or specific knowledge you do not fully remember.
- WEB: current events, time-sensitive information, prices, recent sports, or anything from 2025 onward.
- NO: general knowledge, basic history, literature, and facts you are confident about.

Return only JSON. No extra text."""


async def router_node(state: AgentState):
    system_msg = SystemMessage(content=ROUTER_PROMPT)
    human_msg = HumanMessage(content=state["question"])
    decision = "NO"
    search_query = ""
    content = ""

    max_retries = 10
    for attempt in range(max_retries):
        try:
            response = await llm.ainvoke([system_msg, human_msg], max_tokens=120)
            content = response.content.strip()

            match = re.search(r"\{.*\}", content, re.DOTALL)
            parsed = json.loads(match.group(0) if match else content)

            decision = parsed.get("route", "NO").upper()
            search_query = parsed.get("search_query", "").strip()
            break
        except Exception as e:
            err_msg = str(e)
            if "429" in err_msg or "rate limit" in err_msg.lower():
                wait_time = 4 + attempt * 2
                print(f"Rate limit hit in Router. Waiting {wait_time}s before retry... ({attempt + 1}/{max_retries})")
                await asyncio.sleep(wait_time)
            else:
                route_match = re.search(r'"route"\s*:\s*"(.*?)"', content, re.IGNORECASE)
                query_match = re.search(r'"search_query"\s*:\s*"(.*?)"', content, re.IGNORECASE)
                if route_match:
                    decision = route_match.group(1).upper()
                    if query_match:
                        search_query = query_match.group(1)
                    break

                print(f"Router error ({attempt + 1}/{max_retries}): {e}")
                if attempt == max_retries - 1:
                    decision = "NO"
                    search_query = ""
                else:
                    wait_time = (attempt + 1) * 2
                    print(f"Connection/Other error. Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)

    q_preview = state["question"].split("\n")[0][:50]

    if "PYTHON" in decision:
        print(f"[ROUTER] '{q_preview}...' -> PYTHON REPL")
        return {"need_search": "PYTHON", "search_query": search_query}
    if "WIKI" in decision:
        print(f"[ROUTER] '{q_preview}...' -> WIKIPEDIA (Query: {search_query})")
        return {"need_search": "WIKI", "search_query": search_query}
    if "WEB" in decision:
        print(f"[ROUTER] '{q_preview}...' -> WEB SEARCH (Query: {search_query})")
        return {"need_search": "WEB", "search_query": search_query}

    print(f"[ROUTER] '{q_preview}...' -> DIRECT REASONING")
    return {"need_search": "NO", "search_query": ""}


def my_web_search(query: str) -> str:
    try:
        with DDGS() as ddgs:
            results = ddgs.text(query, max_results=3)
            if results:
                return "\n".join([f"- {r.get('title', '')}: {r.get('body', '')}" for r in results])
            return "No relevant results found."
    except Exception as e:
        return f"Search API error: {e}"


async def web_search_node(state: AgentState):
    question = state.get("question", "")
    query = state.get("search_query", "").strip() or question
    try:
        search_results = await asyncio.wait_for(
            asyncio.to_thread(my_web_search, query),
            timeout=5.0,
        )
        current_context = state.get("context", "")
        new_context = f"{current_context}\n\n--- WEB SEARCH RESULTS ---\n{search_results}"
        return {"context": new_context}
    except Exception as e:
        print(f"Web search timeout/error ({query}): {e}")
        return {"context": state.get("context", "")}


def my_wiki_search(query: str) -> str:
    try:
        search_results = wikipedia.search(query, results=1)
        if search_results:
            return wikipedia.summary(search_results[0], sentences=2)
        return "No matching Wikipedia page found."
    except wikipedia.exceptions.DisambiguationError as e:
        if e.options:
            try:
                return wikipedia.summary(e.options[0], sentences=2)
            except Exception:
                pass
        return f"Wiki has multiple results, examples: {e.options[:5]}"
    except Exception as e:
        return f"Wiki error: {e}"


async def wiki_search_node(state: AgentState):
    question = state.get("question", "")
    query = state.get("search_query", "").strip() or question
    try:
        search_results = await asyncio.wait_for(
            asyncio.to_thread(my_wiki_search, query),
            timeout=5.0,
        )
        current_context = state.get("context", "")
        new_context = (
            f"{current_context}\n\n--- WIKIPEDIA RESULTS ---\n"
            f"Keyword: {query}\nInformation:\n{search_results}"
        )
        return {"context": new_context}
    except Exception as e:
        print(f"Wiki search timeout/error ({query}): {e}")
        return {"context": state.get("context", "")}


async def python_repl_node(state: AgentState):
    question = state.get("question", "")
    system_msg = SystemMessage(
        content="You are a Python developer. Write one short Python snippet to solve the user's problem. Only print the final result. Do not use markdown."
    )

    code = ""
    max_retries = 10
    for attempt in range(max_retries):
        try:
            response = await llm.ainvoke([system_msg, HumanMessage(content=question)], max_tokens=250)
            code = response.content.strip()
            code = re.sub(r"^```python\n|```$", "", code, flags=re.MULTILINE).strip()
            break
        except Exception as e:
            err_msg = str(e)
            if "429" in err_msg or "rate limit" in err_msg.lower():
                wait_time = 4 + attempt * 2
                print(f"Rate limit hit in Python codegen. Waiting {wait_time}s before retry... ({attempt + 1}/{max_retries})")
                await asyncio.sleep(wait_time)
            else:
                print(f"LLM code generation error ({attempt + 1}/{max_retries}): {e}")
                if attempt == max_retries - 1:
                    return {"context": state.get("context", "")}
                wait_time = (attempt + 1) * 2
                print(f"Connection/Other error. Retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)

    if not code:
        return {"context": state.get("context", "")}

    try:
        result = await run_python_code_safe(code, timeout=3.0)
        current_context = state.get("context", "")
        new_context = f"{current_context}\n\n--- PYTHON REPL RESULTS ---\nCode:\n{code}\nOutput:\n{result}"
        return {"context": new_context}
    except Exception as e:
        print(f"Python execution error: {e}")
        return {"context": state.get("context", "")}


async def reasoning_node(state: AgentState):
    system_msg = SystemMessage(content=SYSTEM_COT_PROMPT)
    user_prompt = f"Context:\n{state.get('context', '')}\n\nQuestion:\n{state['question']}"
    human_msg = HumanMessage(content=user_prompt)

    max_retries = 10
    for attempt in range(max_retries):
        try:
            response = await structured_llm.ainvoke([system_msg, human_msg])
            return {
                "reasoning": response.reasoning,
                "answer": response.answer,
            }
        except Exception as e:
            err_msg = str(e)
            if "429" in err_msg or "rate limit" in err_msg.lower():
                wait_time = 4 + attempt * 2
                print(f"Rate limit hit in Reasoning. Waiting {wait_time}s before retry... ({attempt + 1}/{max_retries})")
                await asyncio.sleep(wait_time)
            else:
                print(f"LLM reasoning error: {e}")
                if attempt == max_retries - 1:
                    return {
                        "reasoning": f"Parse/system error: {e}",
                        "answer": "B",
                    }
                wait_time = (attempt + 1) * 2
                print(f"Connection/Other error. Retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)

    return {
        "reasoning": "Failed after repeated retries.",
        "answer": "B",
    }


def should_search(state: AgentState) -> str:
    ans = state.get("need_search", "NO")
    if ans == "PYTHON":
        return "PythonREPL"
    if ans == "WIKI":
        return "WikiSearch"
    if ans == "WEB":
        return "WebSearch"
    return "Reason"


workflow = StateGraph(AgentState)
workflow.add_node("Router", router_node)
workflow.add_node("WebSearch", web_search_node)
workflow.add_node("WikiSearch", wiki_search_node)
workflow.add_node("PythonREPL", python_repl_node)
workflow.add_node("Reason", reasoning_node)

workflow.set_entry_point("Router")

workflow.add_conditional_edges(
    "Router",
    should_search,
    {
        "WebSearch": "WebSearch",
        "WikiSearch": "WikiSearch",
        "PythonREPL": "PythonREPL",
        "Reason": "Reason",
    },
)

workflow.add_edge("WebSearch", "Reason")
workflow.add_edge("WikiSearch", "Reason")
workflow.add_edge("PythonREPL", "Reason")
workflow.add_edge("Reason", END)

app_graph = workflow.compile()
