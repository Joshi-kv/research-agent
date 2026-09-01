import re
from concurrent.futures import ThreadPoolExecutor

import requests
import trafilatura
from bs4 import BeautifulSoup
from langchain.tools import tool

from tools.store import Document as StoredDocument
from tools.store import current_store

# pyrefly: ignore [missing-import]
from readability import Document

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.google.com/",
}

BOILERPLATE_TAGS = ["script", "style", "nav", "footer", "header", "aside", "form"]

# Below this, an extraction is treated as having failed and the next strategy runs.
MIN_USEFUL_CHARS = 200


def _squash(text: str, max_chars: int) -> str:
    return re.sub(r"\s+", " ", text).strip()[:max_chars]


def _strip_tags(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(BOILERPLATE_TAGS):
        tag.decompose()
    return soup.get_text(separator=" ", strip=True)


def scrape_page(url: str, max_chars: int = 10_000) -> dict:
    """
    Scrape and extract the main readable text content from any public webpage URL.

    Use this tool when you need to:
    - Read the full content of a webpage, article, blog post, or documentation page.
    - Retrieve detailed information from a URL returned by a web search.
    - Extract the body text of a news article, tutorial, or reference page.

    Do NOT use this tool for:
    - Downloading files or binary content (PDFs, images, etc.).
    - Pages that require authentication or login.
    - Real-time data (stock prices, live feeds) - use a dedicated API instead.

    Extraction strategy (tried in order, best-first):
    1. **trafilatura** - optimised for articles and blog posts; strips boilerplate.
    2. **readability-lxml** - Mozilla Readability port; good for news and editorial.
    3. **BeautifulSoup fallback** - raw HTML tag-stripping for any remaining cases.

    Args:
        url (str): The full URL of the page (must start with http:// or https://).
        max_chars (int): Maximum characters of text to return. Defaults to 10,000.

    Returns:
        dict: On success, {"ok": True, "url": ..., "strategy": ..., "chars": int,
              "text": ...}. On failure, {"ok": False, "url": ..., "error": ...}
              with no "text" key. Always check "ok" before using the content -
              a failed fetch is not readable text and must not be summarised.
    """
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        html = response.text
    except requests.exceptions.Timeout:
        return {"ok": False, "url": url, "error": "Request timed out."}
    except requests.exceptions.HTTPError as e:
        return {"ok": False, "url": url, "error": f"HTTP error: {e}"}
    except Exception as e:
        return {"ok": False, "url": url, "error": f"Could not fetch URL: {e}"}

    try:
        # Strategy 1 - trafilatura (best for articles/blogs)
        extracted = trafilatura.extract(
            html, include_comments=False, include_tables=False
        )
        if extracted and len(extracted.strip()) > MIN_USEFUL_CHARS:
            text = _squash(extracted, max_chars)
            return {
                "ok": True,
                "url": url,
                "strategy": "trafilatura",
                "chars": len(text),
                "text": text,
            }

        # Strategy 2 - readability
        readable = _strip_tags(Document(html).summary())
        if readable and len(readable.strip()) > MIN_USEFUL_CHARS:
            text = _squash(readable, max_chars)
            return {
                "ok": True,
                "url": url,
                "strategy": "readability",
                "chars": len(text),
                "text": text,
            }

        # Strategy 3 - whole-page tag stripping
        text = _squash(_strip_tags(html), max_chars)
        if text:
            return {
                "ok": True,
                "url": url,
                "strategy": "beautifulsoup",
                "chars": len(text),
                "text": text,
            }

        return {
            "ok": False,
            "url": url,
            "error": "No meaningful content found on the page.",
        }
    except Exception as e:
        return {"ok": False, "url": url, "error": f"Could not parse page: {e}"}


@tool
def scrape_webpages(urls: list[str], max_chars: int = 10_000) -> list[dict]:
    """
    Scrape several webpages at once and record their content for this run.

    Pass every URL you want in ONE call - they are fetched in parallel, so ten
    URLs cost about as long as the slowest one.

    You get back a short receipt per URL, not the page text. The full text is
    stored for the run and handed to the writer automatically. Do NOT ask for
    the text and do NOT repeat page content back in your answer - judge the
    receipts and say what you gathered.

    Args:
        urls: Full URLs to scrape (each must start with http:// or https://).
        max_chars: Maximum characters to keep per page. Defaults to 10,000.

    Returns:
        One receipt per URL:
          {"ok": True, "url": ..., "chars": int, "strategy": ..., "preview": ...}
          {"ok": False, "url": ..., "error": ...}
        Use them to decide what to do next: an "ok": false result or a very low
        "chars" count means that source is unusable, so search again or scrape
        different URLs rather than proceeding with thin research.
    """
    store = current_store()
    titles = {r.get("url"): r.get("title", "") for r in store.results}

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda u: scrape_page(u, max_chars), urls))

    receipts = []
    for url, result in zip(urls, results):
        if not result.get("ok"):
            store.add_failure(url, result.get("error", "unknown error"))
            receipts.append(result)
            continue
        text = result["text"]
        store.add_document(
            StoredDocument(
                url=url,
                text=text,
                strategy=result["strategy"],
                title=titles.get(url, ""),
            )
        )
        receipts.append(
            {
                "ok": True,
                "url": url,
                "chars": len(text),
                "strategy": result["strategy"],
                "preview": text[:200],
            }
        )
    return receipts


if __name__ == "__main__":
    from rich import print

    print("Calling scrape_page ........ ")
    result = scrape_page(
        "https://www.geeksforgeeks.org/machine-learning/what-is-langgraph/"
    )
    print({k: v for k, v in result.items() if k != "text"})
