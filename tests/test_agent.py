import importlib
import sys
import types
import unittest
from unittest.mock import patch


def load_agent_module():
    sys.modules.setdefault("ollama", types.SimpleNamespace(chat=lambda **kwargs: None))
    return importlib.import_module("agents.agent")


class AgentResponseTest(unittest.TestCase):
    def test_agent_strips_thinking_from_response(self):
        agent_module = load_agent_module()

        def fake_chat(**kwargs):
            return {"message": {"content": "<think>phan tich noi bo</think>qid,answer\n1,A"}}

        with patch.object(agent_module.ollama, "chat", fake_chat):
            self.assertEqual(agent_module.agent("1,1+1=?,2,4,5,7"), "qid,answer\n1,A")

    def test_agent_retries_without_thinking_when_response_has_no_answer(self):
        agent_module = load_agent_module()
        calls = []

        def fake_chat(**kwargs):
            calls.append(kwargs)
            if len(calls) == 1:
                return {"message": {"content": "<think>van dang suy nghi</think>"}}
            return {"message": {"content": "qid,answer\n1,A"}}

        with patch.object(agent_module.ollama, "chat", fake_chat):
            self.assertEqual(agent_module.agent("1,1+1=?,2,4,5,7"), "qid,answer\n1,A")

        self.assertEqual(len(calls), 2)
        self.assertIn("/no_think", calls[1]["messages"][-1]["content"])

    def test_chat_once_uses_fast_generation_settings(self):
        agent_module = load_agent_module()
        calls = []

        def fake_chat(**kwargs):
            calls.append(kwargs)
            return {"message": {"content": "qid,answer\n1,A"}}

        with patch.object(agent_module.ollama, "chat", fake_chat):
            agent_module.chat_once("1,1+1=?,2,4,5,7")

        self.assertIs(calls[0]["think"], False)
        self.assertLessEqual(calls[0]["options"]["num_predict"], 768)


if __name__ == "__main__":
    unittest.main()
