from core.llm_client import UnifiedLLMClient

class BaseAgent:
    def __init__(self, system_prompt: str = ""):
        self.llm = UnifiedLLMClient()
        self.system_prompt = system_prompt

    def run(self, user_message: str, max_tokens: int = 512, **kwargs) -> str:
        """Executes the agent logic by querying the LLM."""
        return self.llm.generate(
            system_prompt=self.system_prompt,
            user_message=user_message,
            max_tokens=max_tokens,
            **kwargs
        )
