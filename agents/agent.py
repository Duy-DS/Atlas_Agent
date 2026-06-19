import math
import os
import re
from pathlib import Path

from openai import OpenAI

BASE_DIR = Path(__file__).resolve().parents[1]
MODEL_NAME = os.getenv("MODEL_NAME", "qwen3.5:4b")
SYSTEM_PROMPT_PATH = Path(os.getenv("SYSTEM_PROMPT_PATH", BASE_DIR / "prompts" / "system_prompt.md"))
NUM_PREDICT = int(os.getenv("OLLAMA_NUM_PREDICT", "512"))
THINK_BLOCK_RE = re.compile(r"<think>.*?</think>", re.IGNORECASE | re.DOTALL)
_client = OpenAI(
    base_url=os.getenv("LLAMA_BASE_URL", "http://localhost:8080/v1"),
    api_key="unused",
)

with open(SYSTEM_PROMPT_PATH, "r", encoding="utf-8") as f:
    SYSTEM_PROMPT = f.read()


def final_answer(content: str) -> str:
    answer = THINK_BLOCK_RE.sub("", content or "").strip()
    if answer:
        return answer
    if "<think" in (content or "").lower():
        return ""
    return (content or "").strip()


def chat_once(user_message: str):
    return _client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        max_tokens=NUM_PREDICT,
        temperature=0,
        top_p=1,
        logprobs=True,
        top_logprobs=4,
    )


def answer_logprob(response, answer_token: str) -> float | None:
    """Lấy xác suất của token đáp án (A/B/C/D) từ logprobs của response."""
    content_logprobs = (response.choices[0].logprobs or {}).content or []
    for token_data in reversed(content_logprobs):
        for top in (token_data.top_logprobs or []):
            if top.token.strip().upper() == answer_token.upper():
                return math.exp(top.logprob)
    return None


def response_content(response) -> str:
    return response.choices[0].message.content


def agent(user_message: str) -> str:
    response = chat_once(user_message)
    return final_answer(response_content(response))


def agent_with_logprob(user_message: str, answer_token: str) -> tuple[str, float | None]:
    """Trả về (answer_text, xác suất của answer_token)."""
    response = chat_once(user_message)
    return final_answer(response_content(response)), answer_logprob(response, answer_token)
