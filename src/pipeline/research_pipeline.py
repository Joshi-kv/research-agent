from langchain_core.messages import BaseMessage
from pydantic import BaseModel, Field
from rich.console import Console
from rich.rule import Rule

from agents.critic_agent import CriticAgent, Critique
from agents.scrape_agent import scrape_agent
from agents.search_agent import search_agent
from agents.writer_agent import WriterAgent
from integrations.langfuse_config import callbacks, trace_run, update_trace
from tools.store import ResearchStore, use_store

console = Console()


class ResearchState(BaseModel):
    """Everything one research run accumulates.

    Each step reads what it needs off the state and writes its result back, so
    the run is inspectable at any point instead of living in local variables.
    """

    topic: str
    sources: str = ""
    research: str = ""
    documents: int = 0
    failed_sources: dict[str, str] = Field(default_factory=dict)
    draft: str = ""
    critique: Critique | None = None
    final: str = ""
    revisions: int = 0
    trace_id: str | None = None
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
    return messages[-1].text if messages else ""


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

    @staticmethod
    def _config(step: str, **metadata) -> dict:
        """Runnable config that files this step under the run's Langfuse trace."""
        return {
            "run_name": step,
            "callbacks": callbacks(),
            "metadata": {"step": step, **metadata},
        }

    def _log(self, title: str, content: str = ""):
        if not self.verbose:
            return
        console.print(Rule(f"[bold cyan]{title}[/bold cyan]"))
        if content:
            preview = content[:500] + "..." if len(content) > 500 else content
            console.print(preview)

    # ── steps: state in, state out ─────────────────────────────────────────

    def search(self, state: ResearchState, store: ResearchStore) -> ResearchState:
        self._log(f"🔍 Search — {state.topic}")
        state.sources = _final_text(
            self.search_agent.invoke(
                {"messages": [{"role": "user", "content": state.topic}]},
                config=self._config("search", topic=state.topic),
            )
        )
        self._log("Sources", state.sources)
        return state

    def scrape(self, state: ResearchState, store: ResearchStore) -> ResearchState:
        self._log("🌐 Scrape")
        report = _final_text(
            self.scrape_agent.invoke(
                {
                    "messages": [
                        {
                            "role": "user",
                            "content": (
                                "Gather source material for this topic: "
                                f"{state.topic}\n\n"
                                "Candidate sources found so far:\n"
                                f"{state.sources}"
                            ),
                        }
                    ]
                },
                config=self._config("scrape"),
            )
        )
        # The agent decides what to fetch and what to retry; the text itself
        # comes from the store. Reading it out of the agent's message would make
        # the model re-emit every scraped page as output tokens.
        state.research = store.as_research_text()
        state.documents = len(store.documents)
        state.failed_sources = dict(store.failures)
        self._log(
            f"Research — {state.documents} sources, {store.total_chars} chars",
            report,
        )
        return state

    def write(self, state: ResearchState, store: ResearchStore) -> ResearchState:
        # Write first, then critique the draft. Critiquing raw scrape output and
        # feeding the critique to the writer meant the article was written from
        # a review document and never saw the research itself.
        self._log("✍️  Write draft")
        state.draft = self.writer_agent.run(
            topic=state.topic,
            research_content=state.research,
            config=self._config("write", sources=state.documents),
        )
        self._log("Draft", state.draft)
        return state

    def critique(self, state: ResearchState, store: ResearchStore) -> ResearchState:
        self._log("🧐 Critique")
        state.critique = self.critic_agent.run(
            topic=state.topic,
            article=state.draft,
            config=self._config("critique"),
        )
        self._log("Feedback", _format_critique(state.critique))
        return state

    def revise(self, state: ResearchState, store: ResearchStore) -> ResearchState:
        if state.critique is None or state.critique.score >= self.accept_score:
            score = state.critique.score if state.critique else "n/a"
            self._log(f"✅ Draft accepted (score {score})")
            return state

        self._log(f"✍️  Revise (score {state.critique.score})")
        state.final = self.writer_agent.run(
            topic=state.topic,
            research_content=state.research,
            critique=_format_critique(state.critique),
            config=self._config("revise", score=state.critique.score),
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
        steps = (self.search, self.scrape, self.write, self.critique, self.revise)
        # One store per run, bound to a ContextVar so the tools can reach it
        # without the agents having to be rebuilt for every request.
        # One trace per run, so search/scrape/write/critique/revise appear as
        # nested spans instead of five unrelated root runs.
        with trace_run("research", input={"topic": topic}, tags=["research"]) as tid:
            state.trace_id = tid
            with use_store(ResearchStore()) as store:
                for step in steps:
                    try:
                        state = step(state, store)
                    except Exception as e:
                        state.errors.append(f"{step.__name__}: {e}")
                        self._log(f"❌ {step.__name__} failed", str(e))
                        break
            update_trace(
                output={"article": state.article},
                metadata={
                    "sources_used": state.documents,
                    "sources_failed": list(state.failed_sources),
                    "score": state.critique.score if state.critique else None,
                    "revisions": state.revisions,
                    "errors": state.errors,
                },
            )
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
            "sources_used": state.documents,
            "sources_failed": list(state.failed_sources),
            "score": state.critique.score if state.critique else None,
            "revisions": state.revisions,
            "article_chars": len(state.article),
            "errors": state.errors,
        }
    )
