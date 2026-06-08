import json
from collections.abc import Iterable, Iterator

import requests


Message = dict[str, str]


def stream_chat(base_url: str, model: str, messages: Iterable[Message]) -> Iterator[str]:
    response = requests.post(
        f"{base_url.rstrip('/')}/api/chat",
        json={"model": model, "messages": list(messages), "stream": True},
        stream=True,
        timeout=180,
    )
    try:
        response.raise_for_status()
        for line in response.iter_lines():
            if not line:
                continue
            payload = json.loads(line.decode("utf-8"))
            content = payload.get("message", {}).get("content", "")
            if content:
                yield content
            if payload.get("done"):
                break
    finally:
        response.close()
