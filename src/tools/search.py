from rich import print
from ddgs import DDGS
from langchain.tools import tool

@tool
def web_search(query: str, max_results: int = 5) -> list[dict]:
    """
    Search the web using DuckDuckGo (no API key required).

    Args:
        query: The search query.
        max_results: Maximum number of results to return.

    Returns:
        List of dicts with keys: title, url, content.
    """
    with DDGS() as ddgs:
        results = ddgs.text(query, max_results=max_results)
    
    return results


if __name__ == "__main__":
    print("Calling web_search ........")
    results = web_search("What is LangGraph?")
    print(results)