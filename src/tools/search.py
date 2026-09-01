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

    # ddgs returns title/href/body; normalise to the title/url/content contract
    # promised above, so the agent can chain `url` straight into scrape_webpage.
    return [
        {
            "title": r.get("title", ""),
            "url": r.get("href", ""),
            "content": r.get("body", ""),
        }
        for r in results
    ]


if __name__ == "__main__":
    from rich import print

    print("Calling web_search ........")
    print(web_search.invoke({"query": "What is LangGraph?"}))
