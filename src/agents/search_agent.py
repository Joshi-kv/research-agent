from langchain.agents import create_agent

from integrations.llm import get_llm
from tools.search import web_search


def search_agent(provider: str = "google", temperature: float = 0.0):
    agent = create_agent(
        model=get_llm(provider, temperature),
        tools=[web_search],
        system_prompt=(
            "You are a web research assistant. Use web_search to find the most "
            "relevant sources for the user's topic, then report each result as "
            "title, url and a one-line summary. Do not invent URLs."
        ),
    )

    return agent


if __name__ == "__main__":
    print("Calling search_agent ........ ")
    agent = search_agent()
    for step in agent.stream(
        {"messages": [{"role": "user", "content": "What is LangGraph?"}]},
        stream_mode="updates",
    ):
        for node, update in step.items():
            print(f"\n{'=' * 40}")
            print(f"[{node.upper()}]")
            print(f"{'=' * 40}")
            for msg in update.get("messages", []):
                msg.pretty_print()
