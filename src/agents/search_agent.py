from langchain.agents import create_agent

from integrations.llm import get_llm
from tools.search import web_search

SEARCH_AGENT_SYSTEM_PROMPT = """
You are a web research scout. Find the best sources for the user's topic.

How to work:
- Start with one search. Read the snippets.
- If the results are thin, off-topic, or cover only one angle, search again with
  a different phrasing or a narrower sub-question. Two or three searches is
  normal for a broad topic.
- Prefer primary sources, official docs and substantial articles over listicles
  and SEO pages.

Every result you find is recorded automatically. Do NOT repeat the snippets back
in your answer - that wastes time and adds nothing.

Finish with a short list of the URLs worth scraping, one per line, each with a
few words on why. Nothing else.
"""


def search_agent(provider: str = "google", temperature: float = 0.0):
    return create_agent(
        model=get_llm(provider, temperature),
        tools=[web_search],
        system_prompt=SEARCH_AGENT_SYSTEM_PROMPT,
    )


if __name__ == "__main__":
    from tools.store import ResearchStore, use_store

    agent = search_agent()
    with use_store(ResearchStore()) as store:
        for step in agent.stream(
            {"messages": [{"role": "user", "content": "What is LangGraph?"}]},
            stream_mode="updates",
        ):
            for node, update in step.items():
                for msg in update.get("messages", []):
                    msg.pretty_print()
        print(f"\n{len(store.results)} results recorded")
