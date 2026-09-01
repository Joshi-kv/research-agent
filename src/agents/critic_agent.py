from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from integrations.llm import get_llm

CRITIC_AGENT_SYSTEM_PROMPT = """
    You are a world-class research critic. You are given a topic and a draft
    article. Critique the draft on accuracy, clarity, organization and
    completeness.

    RULES:
    - If the article contains falsehoods, invented facts, or claims that cannot
      be backed by the draft's own sources, set score <= 4 and list every such
      claim in accuracy_points.
    - If sources are missing for major claims, note that in accuracy_points.
    - score is 1-10, where 10 means publishable as-is.
    - Be specific and actionable. No vague complaints, no essays.
    - suggestions must be concrete edits the writer can apply directly.
    - Keep it tight: at most 3 items per list, one sentence each, and at most
      two sentences of overall criticism. Report only the problems that would
      actually change the article - every extra word is latency.
    """


class Critique(BaseModel):
    """Structured critique of a draft article."""

    score: int = Field(description="Quality score from 1 (unusable) to 10 (publishable).")
    criticism: str = Field(description="Overall assessment, at most two sentences.")
    accuracy_points: list[str] = Field(
        default_factory=list,
        description="Factual problems and unsupported claims. At most 3.",
    )
    clarity_issues: list[str] = Field(
        default_factory=list,
        description="Passages that are confusing or poorly ordered. At most 3.",
    )
    suggestions: list[str] = Field(
        default_factory=list,
        description="Concrete edits the writer should apply. At most 3.",
    )


class CriticAgent:
    def __init__(self, provider: str = "google", temperature: float = 0.0):
        # Structured output enforces the schema at the API level, so the caller
        # gets a Critique object instead of a string that may or may not be
        # valid JSON wrapped in a markdown fence.
        self.model = get_llm(provider, temperature).with_structured_output(Critique)
        self.prompt = ChatPromptTemplate.from_messages(
            [
                ("system", CRITIC_AGENT_SYSTEM_PROMPT),
                ("human", "Topic: {topic}\n\nDraft article:\n{article}"),
            ]
        )

    def run(self, topic: str, article: str, config: dict | None = None) -> Critique:
        chain = self.prompt | self.model
        return chain.invoke({"topic": topic, "article": article}, config=config)


if __name__ == "__main__":
    from rich import print

    agent = CriticAgent()
    print(
        agent.run(
            topic="What is LangGraph?",
            article="LangGraph is a framework for building distributed applications.",
        )
    )
