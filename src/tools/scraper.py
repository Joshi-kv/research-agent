import httpx

from langchain.tools import tool
from rich import print
from bs4 import BeautifulSoup

@tool
async def scrape_webpage(url: str, max_chars: int = 10_000) -> dict:
    """
    Fetch and parse a webpage, extracting text content.

    Args:
        url: The URL of the page to scrape.
        max_chars: Maximum number of characters to extract (from the start).

    Returns:
        A dict with 'url' and 'content' keys.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                     "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=headers, follow_redirects=True)
            resp.raise_for_status()
        
        soup = BeautifulSoup(resp.text, "html.parser")
    except Exception as e:
        raise Exception(f"Failed to scrape {url}: {e}")

    # Remove script and style elements
    for script_or_style in soup(["script", "style"]):
        script_or_style.decompose()
    
    # Get text and limit by max_chars
    text = soup.get_text()
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    text = "\n".join(chunk for chunk in chunks if chunk)

    if len(text) > max_chars:
        text = text[:max_chars] + "... [truncated]"

    return {
        "url": url,
        "content": text
    }

    
if __name__ == "__main__":
    import asyncio

    async def main():
        print("Calling scrape_webpage ........ ")
        result = await scrape_webpage("https://www.geeksforgeeks.org/machine-learning/what-is-langgraph/")
        print(result)

    asyncio.run(main())