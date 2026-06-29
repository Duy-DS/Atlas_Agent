import importlib
import sys
import types
import unittest
from unittest.mock import patch


class FakeClient:
    def __init__(self, *args, **kwargs):
        pass
    def chat(self, *args, **kwargs):
        return {"message": {"content": ""}}

def load_agent_module():
    sys.modules.setdefault("ollama", types.SimpleNamespace(Client=FakeClient, chat=lambda **kwargs: None))
    # If already loaded, reload it to apply new mock
    if "agents.agent" in sys.modules:
        return importlib.reload(sys.modules["agents.agent"])
    return importlib.import_module("agents.agent")




class AgentResponseTest(unittest.TestCase):
    def test_system_prompt_instructs_how_to_handle_web_search_results(self):
        agent_module = load_agent_module()

        self.assertIn("**Xử lý kết quả tìm kiếm (khi có)**", agent_module.SYSTEM_PROMPT)
        self.assertIn("Ưu tiên thông tin từ kết quả tìm kiếm hơn kiến thức nội tại", agent_module.SYSTEM_PROMPT)
        self.assertIn("Không bịa thêm thông tin ngoài những gì đã được cung cấp", agent_module.SYSTEM_PROMPT)
        self.assertIn("Nếu có kết quả tìm kiếm", agent_module.SYSTEM_PROMPT)
        self.assertIn("[Search Result]:", agent_module.SYSTEM_PROMPT)

    def test_agent_strips_thinking_from_response(self):
        agent_module = load_agent_module()

        def fake_chat(**kwargs):
            return {"message": {"content": "<think>phan tich noi bo</think>qid,answer\n1,A"}}

        with patch.object(agent_module._client, "chat", fake_chat):
            self.assertEqual(agent_module.agent("1,1+1=?,2,4,5,7"), "qid,answer\n1,A")

    def test_agent_does_not_retry_when_response_has_no_answer(self):
        agent_module = load_agent_module()
        calls = []

        def fake_chat(**kwargs):
            calls.append(kwargs)
            return {"message": {"content": "<think>van dang suy nghi</think>"}}

        with patch.object(agent_module._client, "chat", fake_chat):
            self.assertEqual(agent_module.agent("1,1+1=?,2,4,5,7"), "")

        self.assertEqual(len(calls), 1)

    def test_chat_once_uses_fast_generation_settings(self):
        agent_module = load_agent_module()
        calls = []

        def fake_chat(**kwargs):
            calls.append(kwargs)
            return {"message": {"content": "qid,answer\n1,A"}}

        with patch.object(agent_module._client, "chat", fake_chat):
            agent_module.chat_once("1,1+1=?,2,4,5,7")

        self.assertIs(calls[0]["think"], False)
        self.assertLessEqual(calls[0]["options"]["num_predict"], 768)


if __name__ == "__main__":
    unittest.main()
