from langchain_core.messages import BaseMessage
from pydantic import BaseModel, Field
from rich.console import Console
from rich.rule import Rule

from agents.critic_agent import CriticAgent, Critique
from agents.scrape_agent import scrape_agent
from agents.search_agent import search_agent
from agents.writer_agent import WriterAgent

console = Console()


class ResearchState(BaseModel):
    """Everything one research run accumulates.

    Each step reads what it needs off the state and writes its result back, so
    the run is inspectable at any point instead of living in local variables.
    """

    topic: str
    sources: str = ""
    research: str = ""
    draft: str = ""
    critique: Critique | None = None
    final: str = ""
    revisions: int = 0
    errors: list[str] = Field(default_factory=list)

    @property
    def article(self) -> str:
        """The best article produced so far - the revision if there was one."""
        return self.final or self.draft


def _final_text(agent_output: dict) -> str:
    """Pull the last message's text out of an agent result.

    Passing str(result) instead dumps the whole message list - tool call ids,
    metadata and all - into the next prompt as if it were research.
    """
    messages: list[BaseMessage] = agent_output.get("messages", [])
    return messages[-1].text() if messages else ""


def _format_critique(critique: Critique) -> str:
    sections = [f"Score: {critique.score}/10", f"Overall: {critique.criticism}"]
    for title, items in (
        ("Accuracy problems", critique.accuracy_points),
        ("Clarity issues", critique.clarity_issues),
        ("Suggested edits", critique.suggestions),
    ):
        if items:
            sections.append(title + ":\n" + "\n".join(f"- {i}" for i in items))
    return "\n\n".join(sections)


class ResearchPipeline:
    def __init__(
        self,
        provider: str = "google",
        temperature: float = 0.0,
        verbose: bool = True,
        accept_score: int = 8,
    ):
        self.verbose = verbose
        self.accept_score = accept_score
        self.search_agent = search_agent(provider, temperature)
        self.scrape_agent = scrape_agent(provider, temperature)
        self.critic_agent = CriticAgent(provider, temperature)
        self.writer_agent = WriterAgent(provider, temperature)

    # ── logging ────────────────────────────────────────────────────────────

    def _log(self, title: str, content: str = ""):
        if not self.verbose:
            return
        console.print(Rule(f"[bold cyan]{title}[/bold cyan]"))
        if content:
            preview = content[:500] + "..." if len(content) > 500 else content
            console.print(preview)

    # ── steps: state in, state out ─────────────────────────────────────────

    def search(self, state: ResearchState) -> ResearchState:
        self._log(f"🔍 Search — {state.topic}")
        state.sources = _final_text(
            self.search_agent.invoke(
                {"messages": [{"role": "user", "content": state.topic}]}
            )
        )
        self._log("Sources", state.sources)
        return state

    def scrape(self, state: ResearchState) -> ResearchState:
        self._log("🌐 Scrape")
        state.research = _final_text(
            self.scrape_agent.invoke(
                {
                    "messages": [
                        {
                            "role": "user",
                            "content": (
                                "Scrape every URL listed below and return the "
                                f"extracted content for each.\n\n{state.sources}"
                            ),
                        }
                    ]
                }
            )
        )
        self._log("Research", state.research)
        return state

    def write(self, state: ResearchState) -> ResearchState:
        # Write first, then critique the draft. Critiquing raw scrape output and
        # feeding the critique to the writer meant the article was written from
        # a review document and never saw the research itself.
        self._log("✍️  Write draft")
        state.draft = self.writer_agent.run(
            topic=state.topic, research_content=state.research
        )
        self._log("Draft", state.draft)
        return state

    def critique(self, state: ResearchState) -> ResearchState:
        self._log("🧐 Critique")
        state.critique = self.critic_agent.run(
            topic=state.topic, article=state.draft
        )
        self._log("Feedback", _format_critique(state.critique))
        return state

    def revise(self, state: ResearchState) -> ResearchState:
        if state.critique is None or state.critique.score >= self.accept_score:
            score = state.critique.score if state.critique else "n/a"
            self._log(f"✅ Draft accepted (score {score})")
            return state

        self._log(f"✍️  Revise (score {state.critique.score})")
        state.final = self.writer_agent.run(
            topic=state.topic,
            research_content=state.research,
            critique=_format_critique(state.critique),
        )
        state.revisions += 1
        self._log("Final Article", state.final)
        return state

    # ── entry points ───────────────────────────────────────────────────────

    def run_state(self, topic: str) -> ResearchState:
        """Run the full pipeline and return the whole state.

        Use this from the API layer when the response needs more than the prose
        - the sources, the critic's score, which steps failed.
        """
        state = ResearchState(topic=topic)
        for step in (self.search, self.scrape, self.write, self.critique, self.revise):
            try:
                state = step(state)
            except Exception as e:
                state.errors.append(f"{step.__name__}: {e}")
                self._log(f"❌ {step.__name__} failed", str(e))
                break
        return state

    def run(self, topic: str) -> str:
        """Run the pipeline and return just the article."""
        return self.run_state(topic).article


if __name__ == "__main__":
    pipeline = ResearchPipeline(verbose=True)
    state = pipeline.run_state("What is LangGraph?")
    console.print(Rule("[bold green]Run summary[/bold green]"))
    console.print(
        {
            "topic": state.topic,
            "score": state.critique.score if state.critique else None,
            "revisions": state.revisions,
            "article_chars": len(state.article),
            "errors": state.errors,
        }
    )
