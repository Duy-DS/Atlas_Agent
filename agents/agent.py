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
    base_url=os.getenv("LLAMA_BASE_URL", "http://localhost:11434/v1"),
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


ANSWER_TOKENS = {"A", "B", "C", "D"}


def _normalize_token(t: str) -> str:
    return t.strip().rstrip(".,:;)").lstrip(",").upper()


def answer_confidence(response, chosen: str) -> float | None:
    """
    Tìm vị trí token A/B/C/D cuối cùng trong output (đó là đáp án CSV thực sự),
    lấy logprob của 4 token A/B/C/D tại vị trí đó rồi normalize thành distribution.
    """
    content_logprobs = (response.choices[0].logprobs or {}).content or []
    last_answer_idx = None
    for i, token_data in enumerate(content_logprobs):
        if _normalize_token(token_data.token) in ANSWER_TOKENS:
            last_answer_idx = i
    if last_answer_idx is None:
        return None
    token_data = content_logprobs[last_answer_idx]
    probs: dict[str, float] = {}
    for top in (token_data.top_logprobs or []):
        norm = _normalize_token(top.token)
        if norm in ANSWER_TOKENS and norm not in probs:
            probs[norm] = math.exp(top.logprob)
    if not probs:
        return None
    total = sum(probs.values())
    return probs.get(chosen.upper(), 0.0) / total if total > 0 else None


def response_content(response) -> str:
    return response.choices[0].message.content


def agent(user_message: str) -> str:
    response = chat_once(user_message)
    return final_answer(response_content(response))


def agent_with_confidence(user_message: str, answer_token: str) -> tuple[str, float | None]:
    """Trả về (answer_text, normalized confidence của answer_token trong distribution A/B/C/D)."""
    response = chat_once(user_message)
    return final_answer(response_content(response)), answer_confidence(response, answer_token)
