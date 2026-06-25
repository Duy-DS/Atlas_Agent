import math
import os
import re
from pathlib import Path

import ollama

BASE_DIR = Path(__file__).resolve().parents[1]
MODEL_NAME = os.getenv("MODEL_NAME", "qwen3.5:4b")
SYSTEM_PROMPT_PATH = Path(os.getenv("SYSTEM_PROMPT_PATH", BASE_DIR / "prompts" / "system_prompt.md"))
NUM_PREDICT = int(os.getenv("OLLAMA_NUM_PREDICT", "512"))
THINK_BLOCK_RE = re.compile(r"<think>.*?</think>", re.IGNORECASE | re.DOTALL)
_client = ollama.Client(host=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))

with open(SYSTEM_PROMPT_PATH, "r", encoding="utf-8") as f:
    SYSTEM_PROMPT = f.read()

ANSWER_TOKENS = {"A", "B", "C", "D"}


def final_answer(content: str) -> str:
    answer = THINK_BLOCK_RE.sub("", content or "").strip()
    if answer:
        return answer
    if "<think" in (content or "").lower():
        return ""
    return (content or "").strip()


def _normalize_token(t: str) -> str:
    return t.strip().rstrip(".,:;)").lstrip(",").upper()


def chat_once(user_message: str) -> ollama.ChatResponse:
    return _client.chat(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        options={"num_predict": NUM_PREDICT, "temperature": 0, "top_p": 1},
        think=False,
        logprobs=True,
        top_logprobs=4,
    )


def _extract_logprobs(response: ollama.ChatResponse) -> list:
    """Trả về list token logprob objects từ Ollama response."""
    # Ollama trả logprobs tại response["logprobs"] hoặc response.logprobs
    try:
        return response.get("logprobs") or []
    except Exception:
        return getattr(response, "logprobs", None) or []


def batch_confidences(response: ollama.ChatResponse, answers: dict[str, str]) -> dict[str, float]:
    """
    Từ 1 response, extract confidence cho nhiều qid.
    Duyệt logprobs sau </think>, map token A/B/C/D theo thứ tự qid.
    """
    token_logprobs = _extract_logprobs(response)
    if not token_logprobs:
        return {}

    qids = list(answers.keys())
    result: dict[str, float] = {}

    # Bỏ qua thinking block
    start_idx = 0
    for i, entry in enumerate(token_logprobs):
        token = entry.get("token", "") if isinstance(entry, dict) else getattr(entry, "token", "")
        if "</think>" in token.lower():
            start_idx = i + 1
            break

    matched = 0
    for entry in token_logprobs[start_idx:]:
        if matched >= len(qids):
            break
        token = entry.get("token", "") if isinstance(entry, dict) else getattr(entry, "token", "")
        if _normalize_token(token) not in ANSWER_TOKENS:
            continue

        # top logprobs tại vị trí này
        top_list = entry.get("top_logprobs", []) if isinstance(entry, dict) else getattr(entry, "top_logprobs", [])
        probs: dict[str, float] = {}
        for top in (top_list or []):
            t = top.get("token", "") if isinstance(top, dict) else getattr(top, "token", "")
            lp = top.get("logprob", None) if isinstance(top, dict) else getattr(top, "logprob", None)
            norm = _normalize_token(t)
            if norm in ANSWER_TOKENS and norm not in probs and lp is not None:
                probs[norm] = math.exp(lp)

        total = sum(probs.values())
        if total > 0:
            qid = qids[matched]
            result[qid] = probs.get(answers[qid].upper(), 0.0) / total
        matched += 1

    return result


def agent_with_batch_confidences(user_message: str) -> tuple[str, ollama.ChatResponse]:
    """Gọi model 1 lần, trả về (output_text, response) để extract confidence sau."""
    response = chat_once(user_message)
    return final_answer(response["message"]["content"]), response


def extract_confidences(response: ollama.ChatResponse, answers: dict[str, str]) -> dict[str, float]:
    """Từ response đã có, extract confidence cho các qid/answer đã biết."""
    valid = {qid: ans for qid, ans in answers.items() if ans in ANSWER_TOKENS}
    return batch_confidences(response, valid)


def agent(user_message: str) -> str:
    response = chat_once(user_message)
    return final_answer(response["message"]["content"])


def raw_chat(user_message: str, temperature: float = 0.0) -> str:
    """Call the model without SYSTEM_PROMPT's CSV-only instructions.

    Used by callers (e.g. workflow_v2) whose own prompt already specifies the
    exact output format it needs — SYSTEM_PROMPT would otherwise override it
    and force a "qid,answer" CSV reply regardless of what was asked.
    """
    response = _client.chat(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": user_message}],
        options={"num_predict": NUM_PREDICT, "temperature": temperature, "top_p": 1},
        think=False,
    )
    return final_answer(response["message"]["content"])
