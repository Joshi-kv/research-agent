from ddgs import DDGS
from langchain.tools import tool

from tools.store import current_store


def run_search(query: str, max_results: int = 5) -> list[dict]:
    """Plain DuckDuckGo search. No store, no agent - usable anywhere."""
    with DDGS() as ddgs:
        results = ddgs.text(query, max_results=max_results)

    # ddgs returns title/href/body; normalise to the title/url/content contract
    # the rest of the pipeline expects.
    return [
        {
            "title": r.get("title", ""),
            "url": r.get("href", ""),
            "content": r.get("body", ""),
        }
        for r in results
    ]


@tool
def web_search(query: str, max_results: int = 8) -> list[dict]:
    """
    Search the web using DuckDuckGo (no API key required).

    Call this more than once with different phrasings if the first results are
    thin, off-topic, or cover only one angle of the question.

    Args:
        query: The search query.
        max_results: Maximum number of results to return. Defaults to 8.

    Returns:
        List of dicts with keys: title, url, content (a short snippet).
        Results are also recorded for the run, so you never need to repeat them
        back in your answer - just say which URLs are worth scraping and why.
    """
    results = run_search(query, max_results)
    current_store().add_results(results)
    return results


if __name__ == "__main__":
    from rich import print

    print("Calling run_search ........")
    print(run_search("What is LangGraph?"))
