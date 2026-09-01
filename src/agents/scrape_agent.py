from langchain.agents import create_agent

from integrations.llm import get_llm
from tools.scraper import scrape_webpage


def scrape_agent(provider: str = "google", temperature: float = 0.0):
    agent = create_agent(
        model=get_llm(provider, temperature),
        tools=[scrape_webpage],
        system_prompt=(
            "You are a web scraping assistant. Call scrape_webpage on each URL "
            "you are given and return the extracted text, attributed to its URL. "
            'A result with "ok": false is a fetch failure, not page content - '
            "report it as a failed source and never summarise its error message "
            "as if it were the article."
        ),
    )

    return agent


if __name__ == "__main__":
    print("Calling scrape_agent ........ ")
    agent = scrape_agent()
    for step in agent.stream(
        {
            "messages": [
                {
                    "role": "user",
                    "content": "Scrape this url: https://www.geeksforgeeks.org/machine-learning/what-is-langgraph/",
                }
            ]
        },
        stream_mode="updates",
    ):
        for node, update in step.items():
            print(f"\n{'=' * 40}")
            print(f"[{node.upper()}]")
            print(f"{'=' * 40}")
            for msg in update.get("messages", []):
                msg.pretty_print()
