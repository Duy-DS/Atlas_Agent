import os
import re
from pathlib import Path

import ollama

BASE_DIR = Path(__file__).resolve().parents[1]
MODEL_NAME = os.getenv("MODEL_NAME", "qwen3.5:4b")
SYSTEM_PROMPT_PATH = Path(os.getenv("SYSTEM_PROMPT_PATH", BASE_DIR / "prompts" / "system_prompt.md"))
NUM_PREDICT = int(os.getenv("OLLAMA_NUM_PREDICT", "512"))
NUM_CTX = int(os.getenv("OLLAMA_NUM_CTX", "8192"))
THINK_BLOCK_RE = re.compile(r"<think>.*?</think>", re.IGNORECASE | re.DOTALL)
_client = ollama.Client(host=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))

with open(SYSTEM_PROMPT_PATH, "r", encoding="utf-8") as f:
    SYSTEM_PROMPT = f.read()


def final_answer(content: str) -> str:
    answer = THINK_BLOCK_RE.sub("", content or "").strip()
    if answer:
        return answer
    if "<think" in (content or "").lower():
        return ""
    return (content or "").strip()


def chat_once(user_message: str, think: bool = False, temperature: float = 0.0, num_predict: int | None = None):
    opts = {
        "temperature": temperature,
        "num_ctx": NUM_CTX,
        "top_p": 1
    }
    if num_predict is not None:
        opts["num_predict"] = num_predict
    elif not think:
        opts["num_predict"] = 128
    else:
        opts["num_predict"] = NUM_PREDICT

    return _client.chat(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        think=think,
        options=opts,
    )


def response_content(response) -> str:
    return response["message"]["content"]


def agent(user_message: str, think: bool = False, temperature: float = 0.0, num_predict: int | None = None) -> str:
    response = chat_once(user_message, think=think, temperature=temperature, num_predict=num_predict)
    return final_answer(response_content(response))
