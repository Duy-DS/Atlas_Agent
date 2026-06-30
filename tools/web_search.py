import urllib.request
import os
from duckduckgo_search import DDGS

def is_online() -> bool:
    """Fast check (under 1.0 second) to see if machine has internet access."""
    if os.getenv("OFFLINE_MODE", "false").lower() == "true":
        return False
    try:
        # Check connection to google.com with a short timeout
        urllib.request.urlopen('https://www.google.com', timeout=1.0)
        return True
    except Exception:
        return False

class WebSearchClient:
    def __init__(self):
        self.online = is_online()
        if not self.online:
            print("[WebSearchClient] Warning: Running in OFFLINE mode. Search queries will return empty context.", flush=True)

    def search(self, query: str, max_results: int = 3) -> str:
        """Runs search on DuckDuckGo and returns formatted markdown string of results."""
        if not self.online or not query.strip():
            return ""
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=max_results))
            if not results:
                return "No search results found."
            
            formatted_res = []
            for i, r in enumerate(results):
                formatted_res.append(f"Source [{i+1}]: {r.get('title')}\nURL: {r.get('href')}\nContent: {r.get('body')}\n")
            return "\n".join(formatted_res)
        except Exception as e:
            print(f"[WebSearchClient] Search failed due to: {e}", flush=True)
            return f"Search failed: {str(e)}"
