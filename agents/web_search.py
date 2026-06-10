from __future__ import annotations

import html
import json
import os
import re
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from langchain_core.tools import tool


@dataclass(frozen=True)
class WebSearchResult:
    query: str
    context: str
    enabled: bool
    source: str = ""


class WebSearchClient(Protocol):
    def search(self, query: str) -> WebSearchResult:
        ...


class DisabledWebSearch:
    def search(self, query: str) -> WebSearchResult:
        return WebSearchResult(query=query, context="", enabled=False, source="disabled")


class StaticWebSearch:
    def __init__(self, results: dict[str, str]):
        self.results = results

    def search(self, query: str) -> WebSearchResult:
        return WebSearchResult(
            query=query,
            context=self.results.get(query, ""),
            enabled=True,
            source="static",
        )


class HttpJsonWebSearch:
    def __init__(self, endpoint: str, timeout: float = 8.0):
        self.endpoint = endpoint
        self.timeout = timeout

    def search(self, query: str) -> WebSearchResult:
        url = f"{self.endpoint}?{urlencode({'q': query})}"
        with urlopen(url, timeout=self.timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
        context = payload.get("context") or payload.get("text") or payload.get("snippet") or ""
        return WebSearchResult(query=query, context=context, enabled=True, source=self.endpoint)


class DuckDuckGoHtmlSearch:
    def __init__(self, timeout: float = 8.0, max_results: int = 3):
        self.timeout = timeout
        self.max_results = max_results

    def search(self, query: str) -> WebSearchResult:
        url = f"https://lite.duckduckgo.com/lite/?{urlencode({'q': query})}"
        request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        try:
            with urlopen(request, timeout=self.timeout) as response:
                page = response.read().decode("utf-8", errors="ignore")
        except Exception:
            return WebSearchResult(query=query, context="", enabled=True, source="duckduckgo")

        snippets = []
        patterns = (
            r"class=['\"]result-link['\"].*?>(.*?)</a>",
            r"class=['\"]result-snippet['\"].*?>(.*?)</td>",
            r'<a rel="nofollow" class="result__a".*?>(.*?)</a>',
            r'<a class="result__snippet".*?>(.*?)</a>',
        )
        for pattern in patterns:
            for raw in re.findall(pattern, page, re.DOTALL):
                text = re.sub(r"<.*?>", "", raw)
                text = html.unescape(text).strip()
                text = re.sub(r"\s+", " ", text)
                if text:
                    snippets.append(text)
                if len(snippets) >= self.max_results:
                    break
            if len(snippets) >= self.max_results:
                break

        return WebSearchResult(
            query=query,
            context="\n".join(f"- {snippet}" for snippet in snippets),
            enabled=True,
            source="duckduckgo",
        )


def default_web_search() -> WebSearchClient:
    if os.getenv("WEB_SEARCH_ENABLED", "false").lower() not in {"1", "true", "yes"}:
        return DisabledWebSearch()
    endpoint = os.getenv("WEB_SEARCH_ENDPOINT")
    if endpoint:
        return HttpJsonWebSearch(endpoint=endpoint)
    provider = os.getenv("WEB_SEARCH_PROVIDER", "duckduckgo").lower()
    if provider == "duckduckgo":
        return DuckDuckGoHtmlSearch()
    return DisabledWebSearch()


def build_search_tool(search_client: WebSearchClient):
    @tool("web_search")
    def web_search_tool(query: str) -> str:
        """Search the web for current or uncertain multiple-choice questions."""
        return search_client.search(query).context

    return web_search_tool
