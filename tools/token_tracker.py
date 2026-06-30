import json
from pathlib import Path
from typing import Dict, Any

# Standard Pricing per 1M tokens (in USD)
# [Prompt price, Completion price]
MODEL_PRICING = {
    "claude-3-5-sonnet-20241022": [3.00, 15.00],
    "claude-3-5-sonnet-20240620": [3.00, 15.00],
    "claude-3-haiku-20240307": [0.25, 1.25],
    "gpt-4o": [2.50, 10.00],
    "gpt-4o-mini": [0.15, 0.60],
    "gemini-1.5-pro": [1.25, 5.00],
    "gemini-1.5-flash": [0.075, 0.30]
}

class TokenTracker:
    def __init__(self, stats_file: Path = Path("output/token_usage_stats.json")):
        self.stats_file = stats_file
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.total_cost = 0.0
        self.details = {}

    def track(self, model_name: str, prompt_tokens: int, completion_tokens: int):
        """Records token consumption for a specific model call and calculates cost."""
        self.total_prompt_tokens += prompt_tokens
        self.total_completion_tokens += completion_tokens
        
        # Calculate cost
        price_rates = MODEL_PRICING.get(model_name.lower(), [0.0, 0.0]) # Default $0.0 for local Ollama
        prompt_cost = (prompt_tokens / 1_000_000) * price_rates[0]
        completion_cost = (completion_tokens / 1_000_000) * price_rates[1]
        call_cost = prompt_cost + completion_cost
        
        self.total_cost += call_cost
        
        # Log to details
        if model_name not in self.details:
            self.details[model_name] = {
                "calls_count": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "cost": 0.0
            }
            
        self.details[model_name]["calls_count"] += 1
        self.details[model_name]["prompt_tokens"] += prompt_tokens
        self.details[model_name]["completion_tokens"] += completion_tokens
        self.details[model_name]["cost"] += call_cost

    def get_summary(self) -> Dict[str, Any]:
        """Returns in-memory token summary dictionary."""
        return {
            "total_prompt_tokens": self.total_prompt_tokens,
            "total_completion_tokens": self.total_completion_tokens,
            "total_tokens": self.total_prompt_tokens + self.total_completion_tokens,
            "total_cost_usd": round(self.total_cost, 6),
            "details": self.details
        }

    def save(self):
        """Saves current statistics to JSON file."""
        self.stats_file.parent.mkdir(parents=True, exist_ok=True)
        with self.stats_file.open("w", encoding="utf-8") as f:
            json.dump(self.get_summary(), f, indent=2, ensure_ascii=False)
        print(f"[TokenTracker] Saved usage statistics to: {self.stats_file}")
