import json
import unittest
from unittest.mock import patch

from ollama_chat_client import stream_chat


class FakeResponse:
    def __init__(self, lines):
        self._lines = lines

    def raise_for_status(self):
        return None

    def iter_lines(self):
        return iter(self._lines)

    def close(self):
        return None


class StreamChatTest(unittest.TestCase):
    def test_stream_chat_yields_message_content_tokens(self):
        messages = [{"role": "user", "content": "hello"}]
        response = FakeResponse(
            [
                json.dumps({"message": {"content": "Xin "}}).encode(),
                json.dumps({"message": {"content": "chao"}}).encode(),
                b"",
                json.dumps({"done": True}).encode(),
            ]
        )

        with patch("ollama_chat_client.requests.post", return_value=response) as post:
            tokens = list(stream_chat("http://ollama:11434", "qwen3.5:0.8b", messages))

        self.assertEqual(tokens, ["Xin ", "chao"])
        post.assert_called_once_with(
            "http://ollama:11434/api/chat",
            json={"model": "qwen3.5:0.8b", "messages": messages, "stream": True},
            stream=True,
            timeout=180,
        )


if __name__ == "__main__":
    unittest.main()
