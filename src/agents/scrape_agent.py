from langchain.agents import create_agent

from integrations.llm import get_llm
from tools.scraper import scrape_webpages
from tools.search import web_search

SCRAPE_AGENT_SYSTEM_PROMPT = """
You gather the source material a writer will work from.

How to work:
- Pass ALL the URLs you want to scrape_webpages in ONE call. They are fetched in
  parallel, so batching is much faster than one call per URL.
- You get back a receipt per URL, never the page text. The text is stored for the
  run and given to the writer automatically.
- Judge the receipts. "ok": false means the fetch failed. A very low "chars"
  count means the page was mostly boilerplate. Either way that source is
  unusable.
- If too few sources survived, or they all cover the same narrow angle, use
  web_search to find replacements and scrape those too. Aim for at least three
  usable sources before you stop.

Never repeat page content in your answer - you have not been given it, and
asking for it is not possible. Finish with one short paragraph: which sources
succeeded, which failed and why, and whether the material is enough to write
from.
"""


def scrape_agent(provider: str = "google", temperature: float = 0.0):
    return create_agent(
        model=get_llm(provider, temperature),
        tools=[scrape_webpages, web_search],
        system_prompt=SCRAPE_AGENT_SYSTEM_PROMPT,
    )


if __name__ == "__main__":
    from tools.store import ResearchStore, use_store

    agent = scrape_agent()
    with use_store(ResearchStore()) as store:
        for step in agent.stream(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": "Scrape https://www.ibm.com/think/topics/langgraph and https://www.langchain.com/langgraph",
                    }
                ]
            },
            stream_mode="updates",
        ):
            for node, update in step.items():
                for msg in update.get("messages", []):
                    msg.pretty_print()
        print(f"\nstored {store.total_chars} chars from {len(store.documents)} docs")
