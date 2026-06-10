import os
import re
from pathlib import Path

import ollama

BASE_DIR = Path(__file__).resolve().parents[1]
MODEL_NAME = os.getenv("MODEL_NAME", "qwen3.5:4b")
SYSTEM_PROMPT_PATH = Path(os.getenv("SYSTEM_PROMPT_PATH", BASE_DIR / "prompts" / "system_prompt.md"))
NUM_PREDICT = int(os.getenv("OLLAMA_NUM_PREDICT", "512"))
THINK_BLOCK_RE = re.compile(r"<think>.*?</think>", re.IGNORECASE | re.DOTALL)

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
    return ollama.chat(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        think=False,
        options={"num_predict": NUM_PREDICT,
                 "temperature" : 0
                 },
    )


def response_content(response) -> str:
    return response["message"]["content"]


def agent(user_message: str) -> str:
    response = chat_once(user_message)
    return final_answer(response_content(response))
